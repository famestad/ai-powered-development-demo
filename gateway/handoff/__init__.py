"""Handoff orchestrator module for Maplewood Civic Services Agent.

Provides the orchestrator that routes escalation signals to the appropriate
handoff pattern (warm handoff, scheduled callback, or ticket creation),
a state machine for tracking handoff lifecycle, and the HandoffFlow protocol
that Issue #19's concrete implementations must satisfy.
"""

from gateway.handoff.config import (
    BusinessHoursConfig,
    HandoffConfig,
    SLAConfig,
    load_config,
)
from gateway.handoff.flow import HandoffFlow
from gateway.handoff.models import (
    CitizenContext,
    EscalationSignal,
    HandoffRequest,
    HandoffResult,
    HandoffState,
    HandoffType,
    SessionSummary,
)
from gateway.handoff.orchestrator import HandoffOrchestrator
from gateway.handoff.state_machine import (
    HandoffStateMachine,
    InvalidTransitionError,
)

__all__ = [
    # Models
    "CitizenContext",
    "EscalationSignal",
    "HandoffRequest",
    "HandoffResult",
    "HandoffState",
    "HandoffType",
    "SessionSummary",
    # Config
    "BusinessHoursConfig",
    "HandoffConfig",
    "SLAConfig",
    "load_config",
    # Flow protocol
    "HandoffFlow",
    # Orchestrator
    "HandoffOrchestrator",
    # State machine
    "HandoffStateMachine",
    "InvalidTransitionError",
]
