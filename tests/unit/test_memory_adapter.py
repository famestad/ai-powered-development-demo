# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for MemoryAdapter (save_context / load_context)."""

from unittest.mock import MagicMock, patch

import pytest

from gateway.memory.adapter import _CONTEXT_PREFIX, MemoryAdapter
from gateway.memory.context import CitizenContext


@pytest.fixture()
def mock_boto_client():
    """Patch boto3.client so no AWS calls are made."""
    with patch("gateway.memory.adapter.boto3.client") as mock_client_ctor:
        client = MagicMock()
        mock_client_ctor.return_value = client
        yield client


@pytest.fixture()
def adapter(mock_boto_client):
    return MemoryAdapter(
        session_id="sess-1",
        actor_id="user-42",
        memory_id="mem-abc",
        region_name="us-east-1",
    )


class TestMemoryAdapterInit:
    def test_requires_memory_id(self):
        with patch("gateway.memory.adapter.boto3.client"):
            with patch.dict("os.environ", {}, clear=True):
                with pytest.raises(ValueError, match="memory_id"):
                    MemoryAdapter(session_id="s", actor_id="a")

    def test_reads_memory_id_from_env(self):
        with patch("gateway.memory.adapter.boto3.client"):
            with patch.dict("os.environ", {"MEMORY_ID": "env-mem-123"}):
                adapter = MemoryAdapter(session_id="s", actor_id="a")
                assert adapter.memory_id == "env-mem-123"

    def test_explicit_memory_id_overrides_env(self):
        with patch("gateway.memory.adapter.boto3.client"):
            with patch.dict("os.environ", {"MEMORY_ID": "env-mem"}):
                adapter = MemoryAdapter(
                    session_id="s", actor_id="a", memory_id="explicit-mem"
                )
                assert adapter.memory_id == "explicit-mem"


class TestSaveContext:
    def test_save_creates_event(self, adapter, mock_boto_client):
        mock_boto_client.create_event.return_value = {
            "event": {"eventId": "evt-123"}
        }
        ctx = CitizenContext(citizen_name="Jane", department="DMV")
        event_id = adapter.save_context(ctx)

        assert event_id == "evt-123"
        mock_boto_client.create_event.assert_called_once()

        call_kwargs = mock_boto_client.create_event.call_args.kwargs
        assert call_kwargs["memoryId"] == "mem-abc"
        assert call_kwargs["actorId"] == "user-42"
        assert call_kwargs["sessionId"] == "sess-1"

        payload_text = call_kwargs["payload"][0]["conversational"]["content"]["text"]
        assert payload_text.startswith(_CONTEXT_PREFIX)
        json_part = payload_text[len(_CONTEXT_PREFIX):]
        restored = CitizenContext.model_validate_json(json_part)
        assert restored.citizen_name == "Jane"
        assert restored.department == "DMV"

    def test_save_preserves_all_fields(self, adapter, mock_boto_client):
        mock_boto_client.create_event.return_value = {
            "event": {"eventId": "evt-456"}
        }
        ctx = CitizenContext(
            citizen_name="John",
            address="789 Elm St",
            case_number="C-100",
            account_number="A-200",
            service_type="permits",
            department="Planning",
            prior_requests=["first", "second"],
        )
        adapter.save_context(ctx)

        payload_text = (
            mock_boto_client.create_event.call_args.kwargs["payload"][0]
            ["conversational"]["content"]["text"]
        )
        restored = CitizenContext.model_validate_json(
            payload_text[len(_CONTEXT_PREFIX):]
        )
        assert restored == ctx


class TestLoadContext:
    def _make_event(self, text: str) -> dict:
        return {
            "eventId": "e1",
            "payload": [
                {"conversational": {"content": {"text": text}, "role": "ASSISTANT"}}
            ],
        }

    def test_load_returns_context(self, adapter, mock_boto_client):
        ctx = CitizenContext(citizen_name="Jane", case_number="C-1")
        payload_text = _CONTEXT_PREFIX + ctx.model_dump_json()
        mock_boto_client.list_events.return_value = {
            "events": [self._make_event(payload_text)]
        }
        loaded = adapter.load_context()
        assert loaded is not None
        assert loaded.citizen_name == "Jane"
        assert loaded.case_number == "C-1"

    def test_load_returns_none_when_empty(self, adapter, mock_boto_client):
        mock_boto_client.list_events.return_value = {"events": []}
        assert adapter.load_context() is None

    def test_load_skips_non_context_events(self, adapter, mock_boto_client):
        ctx = CitizenContext(citizen_name="Bob")
        mock_boto_client.list_events.return_value = {
            "events": [
                self._make_event("Just a normal conversation message"),
                self._make_event(_CONTEXT_PREFIX + ctx.model_dump_json()),
            ]
        }
        loaded = adapter.load_context()
        assert loaded is not None
        assert loaded.citizen_name == "Bob"

    def test_load_returns_first_matching_event(self, adapter, mock_boto_client):
        """Events are newest-first; the first match should win."""
        newer = CitizenContext(citizen_name="Newer")
        older = CitizenContext(citizen_name="Older")
        mock_boto_client.list_events.return_value = {
            "events": [
                self._make_event(_CONTEXT_PREFIX + newer.model_dump_json()),
                self._make_event(_CONTEXT_PREFIX + older.model_dump_json()),
            ]
        }
        loaded = adapter.load_context()
        assert loaded is not None
        assert loaded.citizen_name == "Newer"

    def test_load_skips_corrupt_json(self, adapter, mock_boto_client):
        valid = CitizenContext(citizen_name="Valid")
        mock_boto_client.list_events.return_value = {
            "events": [
                self._make_event(_CONTEXT_PREFIX + "{invalid json!!!}"),
                self._make_event(_CONTEXT_PREFIX + valid.model_dump_json()),
            ]
        }
        loaded = adapter.load_context()
        assert loaded is not None
        assert loaded.citizen_name == "Valid"

    def test_load_returns_none_on_client_error(self, adapter, mock_boto_client):
        from botocore.exceptions import ClientError

        mock_boto_client.list_events.side_effect = ClientError(
            {"Error": {"Code": "InternalError", "Message": "boom"}},
            "ListEvents",
        )
        assert adapter.load_context() is None

    def test_load_uses_correct_session_params(self, adapter, mock_boto_client):
        mock_boto_client.list_events.return_value = {"events": []}
        adapter.load_context()
        call_kwargs = mock_boto_client.list_events.call_args.kwargs
        assert call_kwargs["memoryId"] == "mem-abc"
        assert call_kwargs["actorId"] == "user-42"
        assert call_kwargs["sessionId"] == "sess-1"


class TestSessionIsolation:
    """Verify that different sessions do not share context."""

    def test_different_sessions_get_own_namespace(self, mock_boto_client):
        adapter_a = MemoryAdapter(
            session_id="sess-A", actor_id="user-1", memory_id="mem-1"
        )
        adapter_b = MemoryAdapter(
            session_id="sess-B", actor_id="user-1", memory_id="mem-1"
        )

        mock_boto_client.list_events.return_value = {"events": []}
        adapter_a.load_context()
        adapter_b.load_context()

        calls = mock_boto_client.list_events.call_args_list
        assert calls[0].kwargs["sessionId"] == "sess-A"
        assert calls[1].kwargs["sessionId"] == "sess-B"
