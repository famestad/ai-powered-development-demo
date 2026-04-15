"""Citizen session context model, summary generation, and structured memory logging.

Provides the CitizenContext data model for tracking citizen interactions,
a generate_session_summary() function for the handoff-to-human flow,
and a MemoryLogger for structured observability of memory operations.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CitizenContext:
    """Tracks the context of a citizen's session with the agent.

    This model captures all relevant information gathered during a citizen's
    interaction, including identity, case details, and conversation trajectory.
    Used for internal diagnostics and to generate handoff summaries.

    Attributes:
        session_id: Unique identifier for this conversation session.
        actor_id: User identifier from the JWT token (sub claim).
        citizen_name: Full name of the citizen, if provided.
        case_number: Case reference number (e.g., "CR-2024-456"), if applicable.
        address: Address related to the citizen's inquiry, if provided.
        issue_type: Category of the issue (e.g., "permit", "zoning", "complaint").
        issue_description: Free-text description of the citizen's issue.
        conversation_topics: Ordered list of topics discussed during the session.
        created_at: ISO 8601 timestamp when the session context was created.
        updated_at: ISO 8601 timestamp when the session context was last updated.
        additional_details: Arbitrary key-value pairs for extra context.
    """

    session_id: str
    actor_id: str
    citizen_name: Optional[str] = None
    case_number: Optional[str] = None
    address: Optional[str] = None
    issue_type: Optional[str] = None
    issue_description: Optional[str] = None
    conversation_topics: list[str] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    additional_details: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize the context to a dictionary.

        Returns:
            dict: All context fields as a dictionary, suitable for JSON serialization.
        """
        return {
            "session_id": self.session_id,
            "actor_id": self.actor_id,
            "citizen_name": self.citizen_name,
            "case_number": self.case_number,
            "address": self.address,
            "issue_type": self.issue_type,
            "issue_description": self.issue_description,
            "conversation_topics": self.conversation_topics,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "additional_details": self.additional_details,
        }


def generate_session_summary(context: CitizenContext) -> str:
    """Generate a human-readable summary of the citizen's session for handoff.

    Produces a structured summary designed for the handoff-to-human flow,
    including the citizen's identity, case details, issue description, and
    conversation trajectory. The output is formatted for easy reading by
    a human agent receiving the handoff.

    Args:
        context: The CitizenContext containing the citizen's session data.

    Returns:
        str: A formatted, human-readable summary string. Contains a header line
            with key details and a body with conversation topics and additional
            context.
    """
    # Build the header line with available identity and case information
    header_parts: list[str] = []

    if context.citizen_name:
        header_parts.append(f"Citizen {context.citizen_name}")
    else:
        header_parts.append("An unidentified citizen")

    if context.case_number:
        header_parts.append(f"called about case #{context.case_number}")
    else:
        header_parts.append("called")

    if context.address:
        header_parts.append(f"at {context.address}")

    if context.issue_type:
        header_parts.append(f"regarding a {context.issue_type} issue")

    header = " ".join(header_parts)

    # Build the body with issue description and conversation trajectory
    body_sections: list[str] = []

    if context.issue_description:
        body_sections.append(f"Issue: {context.issue_description}")

    if context.conversation_topics:
        topics_formatted = ", ".join(context.conversation_topics)
        body_sections.append(f"Topics discussed: {topics_formatted}")

    if context.additional_details:
        details_formatted = "; ".join(
            f"{key}: {value}"
            for key, value in context.additional_details.items()
        )
        body_sections.append(f"Additional details: {details_formatted}")

    body_sections.append(f"Session ID: {context.session_id}")
    body_sections.append(f"Session started: {context.created_at}")

    # Combine header and body into the final summary
    summary = header + "."
    if body_sections:
        summary += "\n" + "\n".join(body_sections)

    return summary


class MemoryLogger:
    """Structured JSON logger for memory operations.

    Logs memory operations (store, retrieve, update, delete) as JSON-formatted
    entries for observability and log aggregation. Each log entry includes
    the operation type, session ID, timestamp, and operation-specific data.

    Attributes:
        session_id: The session ID to include in all log entries.
        actor_id: The actor (user) ID to include in all log entries.
    """

    def __init__(self, session_id: str, actor_id: str) -> None:
        """Initialize the memory logger for a specific session.

        Args:
            session_id: The session ID to tag all log entries with.
            actor_id: The actor (user) ID to tag all log entries with.
        """
        self.session_id = session_id
        self.actor_id = actor_id
        self._logger = logging.getLogger(f"{__name__}.MemoryLogger")

    def _log_operation(
        self, operation: str, data: dict, level: int = logging.INFO
    ) -> None:
        """Write a structured JSON log entry for a memory operation.

        Args:
            operation: The type of memory operation (e.g., "store", "retrieve").
            data: Operation-specific data to include in the log entry.
            level: The logging level to use (default: logging.INFO).
        """
        log_entry = {
            "event": "memory_operation",
            "operation": operation,
            "session_id": self.session_id,
            "actor_id": self.actor_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        self._logger.log(level, json.dumps(log_entry))

    def log_context_created(self, context: CitizenContext) -> None:
        """Log the creation of a new CitizenContext.

        Args:
            context: The newly created CitizenContext instance.
        """
        self._log_operation(
            operation="context_created",
            data={
                "citizen_name": context.citizen_name,
                "case_number": context.case_number,
                "issue_type": context.issue_type,
            },
        )

    def log_context_updated(
        self, field_name: str, old_value: Optional[str], new_value: str
    ) -> None:
        """Log an update to a CitizenContext field.

        Args:
            field_name: The name of the field that was updated.
            old_value: The previous value of the field (None if not set).
            new_value: The new value of the field.
        """
        self._log_operation(
            operation="context_updated",
            data={
                "field": field_name,
                "old_value": old_value,
                "new_value": new_value,
            },
        )

    def log_topic_added(self, topic: str) -> None:
        """Log the addition of a new conversation topic.

        Args:
            topic: The topic string that was added to the conversation.
        """
        self._log_operation(
            operation="topic_added",
            data={"topic": topic},
        )

    def log_summary_generated(self, summary: str) -> None:
        """Log that a session summary was generated (e.g., for handoff).

        Args:
            summary: The generated summary text.
        """
        self._log_operation(
            operation="summary_generated",
            data={"summary_length": len(summary)},
        )

    def log_context_retrieved(self) -> None:
        """Log that the CitizenContext was retrieved for diagnostics."""
        self._log_operation(
            operation="context_retrieved",
            data={"purpose": "diagnostics"},
        )
