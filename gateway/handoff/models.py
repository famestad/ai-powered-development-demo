"""Pydantic models for the handoff orchestrator.

Defines the data contracts for escalation signals, citizen context,
session summaries, handoff requests/results, and the handoff state enum.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Escalation signal (consumed from Issue #17 classifier)
# ---------------------------------------------------------------------------


class EscalationSignal(BaseModel):
    """Output from the sensitive-topic classifier (Issue #17)."""

    is_sensitive: bool = Field(
        description="Whether the topic was classified as sensitive."
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Detected sensitive-topic categories.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Classifier confidence score (0.0 - 1.0).",
    )
    escalation_recommended: bool = Field(
        description="Whether the classifier recommends escalation."
    )


# ---------------------------------------------------------------------------
# Citizen context (placeholder consumed from Issues #4/#5)
# ---------------------------------------------------------------------------


class CitizenContext(BaseModel):
    """Minimal citizen context consumed from Issues #4/#5.

    Once Issue #4/#5 ships a full CitizenContext model, this should be
    replaced with an import from that module.
    """

    citizen_id: str = Field(description="Unique citizen identifier.")
    name: str = Field(default="", description="Citizen display name.")
    email: str = Field(default="", description="Citizen email address.")
    phone: str = Field(default="", description="Citizen phone number.")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional citizen metadata.",
    )


# ---------------------------------------------------------------------------
# Session summary (placeholder consumed from Issue #7)
# ---------------------------------------------------------------------------


class SessionSummary(BaseModel):
    """Summary of the current agent session (Issue #7).

    Once Issue #7 ships ``generate_session_summary()``, this model should
    align with its return type.
    """

    session_id: str = Field(description="Unique session identifier.")
    summary_text: str = Field(
        description="Human-readable summary of the conversation so far."
    )
    topic: str = Field(default="", description="Primary topic discussed.")
    message_count: int = Field(
        default=0, description="Number of messages in the session."
    )


# ---------------------------------------------------------------------------
# Handoff state machine
# ---------------------------------------------------------------------------


class HandoffState(str, Enum):
    """Lifecycle states for a handoff request."""

    PENDING = "pending"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CALLBACK_SCHEDULED = "callback_scheduled"
    TICKET_CREATED = "ticket_created"
    RESOLVED = "resolved"


# ---------------------------------------------------------------------------
# Handoff type
# ---------------------------------------------------------------------------


class HandoffType(str, Enum):
    """The type of handoff to perform."""

    WARM = "warm"
    CALLBACK = "callback"
    TICKET = "ticket"


# ---------------------------------------------------------------------------
# Handoff request / result
# ---------------------------------------------------------------------------


class HandoffRequest(BaseModel):
    """A request to hand off the conversation to a human agent.

    Combines the escalation signal (Issue #17), session summary (Issue #7),
    and citizen context (Issues #4/#5) into a single handoff request.
    """

    escalation_signal: EscalationSignal = Field(
        description="The escalation signal from the classifier."
    )
    session_summary: SessionSummary = Field(
        description="Summary of the current session for context packaging."
    )
    citizen: CitizenContext = Field(
        description="Information about the citizen being helped."
    )
    requested_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the handoff was requested.",
    )


class HandoffResult(BaseModel):
    """The outcome of a handoff attempt."""

    handoff_type: HandoffType = Field(
        description="Which handoff pattern was used."
    )
    state: HandoffState = Field(
        description="Current lifecycle state of this handoff."
    )
    reference_number: str = Field(
        description="Tracking reference number for the citizen."
    )
    estimated_wait_minutes: int | None = Field(
        default=None,
        description="Estimated wait time in minutes (for warm handoff).",
    )
    estimated_response_hours: int | None = Field(
        default=None,
        description="Estimated response time in hours (for callback/ticket).",
    )
    citizen_message: str = Field(
        description="Message to display to the citizen about next steps."
    )
