# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Thin wrapper around AgentCore Memory for structured citizen context."""

import logging
import os
from datetime import UTC, datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from gateway.memory.context import CitizenContext

logger = logging.getLogger(__name__)

# Role used in the conversational payload to distinguish context events
# from regular conversation history.
_CONTEXT_ROLE = "ASSISTANT"
_CONTEXT_PREFIX = "__citizen_context__:"


class MemoryAdapter:
    """Store and retrieve CitizenContext in AgentCore Memory.

    Context is persisted as a conversational event whose text payload is a
    JSON blob prefixed with a sentinel marker.  Each session gets its own
    namespace (session_id + actor_id), preventing cross-session leakage.

    Usage::

        adapter = MemoryAdapter(session_id="sess-1", actor_id="user-42")
        adapter.save_context(CitizenContext(citizen_name="Jane Doe"))
        ctx = adapter.load_context()
    """

    def __init__(
        self,
        session_id: str,
        actor_id: str,
        memory_id: Optional[str] = None,
        region_name: Optional[str] = None,
    ) -> None:
        self.session_id = session_id
        self.actor_id = actor_id
        self.memory_id = memory_id or os.environ.get("MEMORY_ID", "")
        if not self.memory_id:
            raise ValueError(
                "memory_id must be provided or set via the MEMORY_ID environment variable"
            )
        self._region = region_name or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        self._client = boto3.client(
            "bedrock-agentcore", region_name=self._region
        )

    def save_context(self, context: CitizenContext) -> str:
        """Persist *context* as a memory event and return the event ID."""
        payload_text = _CONTEXT_PREFIX + context.model_dump_json()
        response = self._client.create_event(
            memoryId=self.memory_id,
            actorId=self.actor_id,
            sessionId=self.session_id,
            eventTimestamp=datetime.now(UTC),
            payload=[
                {
                    "conversational": {
                        "content": {"text": payload_text},
                        "role": _CONTEXT_ROLE,
                    }
                }
            ],
        )
        event_id: str = response["event"]["eventId"]
        logger.info("Saved citizen context as event %s", event_id)
        return event_id

    def load_context(self) -> Optional[CitizenContext]:
        """Load the most recent CitizenContext for this session.

        Returns ``None`` if no context has been saved yet.
        """
        try:
            response = self._client.list_events(
                memoryId=self.memory_id,
                actorId=self.actor_id,
                sessionId=self.session_id,
                maxResults=20,
            )
        except ClientError:
            logger.exception("Failed to list memory events")
            return None

        # Walk events newest-first looking for our sentinel prefix.
        for event in response.get("events", []):
            for item in event.get("payload", []):
                text = (
                    item.get("conversational", {})
                    .get("content", {})
                    .get("text", "")
                )
                if text.startswith(_CONTEXT_PREFIX):
                    json_str = text[len(_CONTEXT_PREFIX) :]
                    try:
                        return CitizenContext.model_validate_json(json_str)
                    except Exception:
                        logger.exception("Corrupt citizen context in event")
                        continue
        return None
