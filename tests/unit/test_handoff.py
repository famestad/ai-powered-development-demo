"""Unit tests for the gateway.handoff module."""

from __future__ import annotations

import asyncio
from datetime import datetime, time

import pytest

from gateway.handoff.config import (
    BusinessHoursConfig,
    HandoffConfig,
    SLAConfig,
    load_config,
)
from gateway.handoff.models import (
    CitizenContext,
    EscalationSignal,
    HandoffRequest,
    HandoffResult,
    HandoffState,
    HandoffType,
    SessionSummary,
)
from gateway.handoff.orchestrator import HandoffOrchestrator, _is_business_hours
from gateway.handoff.state_machine import (
    HandoffStateMachine,
    InvalidTransitionError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_signal(
    *,
    is_sensitive: bool = True,
    categories: list[str] | None = None,
    confidence: float = 0.9,
    escalation_recommended: bool = True,
) -> EscalationSignal:
    return EscalationSignal(
        is_sensitive=is_sensitive,
        categories=categories or ["general"],
        confidence=confidence,
        escalation_recommended=escalation_recommended,
    )


def _make_request(
    *,
    signal: EscalationSignal | None = None,
    categories: list[str] | None = None,
    confidence: float = 0.9,
    escalation_recommended: bool = True,
) -> HandoffRequest:
    return HandoffRequest(
        escalation_signal=signal
        or _make_signal(
            categories=categories or ["general"],
            confidence=confidence,
            escalation_recommended=escalation_recommended,
        ),
        session_summary=SessionSummary(
            session_id="sess-001",
            summary_text="Citizen asked about permit status.",
            topic="permits",
            message_count=5,
        ),
        citizen=CitizenContext(
            citizen_id="cit-001",
            name="Jane Doe",
            email="jane@example.com",
        ),
    )


class _StubFlow:
    """Minimal stub satisfying the HandoffFlow protocol for testing."""

    def __init__(
        self,
        handoff_type: HandoffType,
        available: bool = True,
        delay: float = 0.0,
    ) -> None:
        self._type = handoff_type
        self._available = available
        self._delay = delay
        self.execute_count = 0

    async def execute(self, request: HandoffRequest) -> HandoffResult:
        self.execute_count += 1
        if self._delay:
            await asyncio.sleep(self._delay)
        state_map = {
            HandoffType.WARM: HandoffState.CONNECTED,
            HandoffType.CALLBACK: HandoffState.CALLBACK_SCHEDULED,
            HandoffType.TICKET: HandoffState.TICKET_CREATED,
        }
        return HandoffResult(
            handoff_type=self._type,
            state=state_map[self._type],
            reference_number="HO-TEST0001",
            estimated_wait_minutes=5 if self._type == HandoffType.WARM else None,
            estimated_response_hours=(
                4 if self._type == HandoffType.CALLBACK else None
            ),
            citizen_message=f"Stub {self._type.value} result.",
        )

    async def cancel(self, reference_number: str) -> bool:
        return True

    def is_available(self) -> bool:
        return self._available


def _make_orchestrator(
    *,
    warm_available: bool = True,
    warm_delay: float = 0.0,
    config: HandoffConfig | None = None,
) -> tuple[HandoffOrchestrator, _StubFlow, _StubFlow, _StubFlow]:
    cfg = config or HandoffConfig()
    warm = _StubFlow(HandoffType.WARM, available=warm_available, delay=warm_delay)
    callback = _StubFlow(HandoffType.CALLBACK)
    ticket = _StubFlow(HandoffType.TICKET)
    orch = HandoffOrchestrator(
        config=cfg,
        warm_flow=warm,
        callback_flow=callback,
        ticket_flow=ticket,
    )
    return orch, warm, callback, ticket


# ===================================================================
# State machine tests
# ===================================================================


class TestHandoffStateMachine:
    """Tests for state machine transitions (valid and invalid)."""

    def test_initial_state_is_pending(self) -> None:
        sm = HandoffStateMachine()
        assert sm.state == HandoffState.PENDING

    def test_valid_warm_handoff_path(self) -> None:
        """pending -> connecting -> connected -> resolved"""
        sm = HandoffStateMachine()
        sm.transition(HandoffState.CONNECTING)
        sm.transition(HandoffState.CONNECTED)
        sm.transition(HandoffState.RESOLVED)
        assert sm.state == HandoffState.RESOLVED
        assert sm.is_terminal

    def test_valid_callback_path(self) -> None:
        """pending -> connecting -> callback_scheduled -> resolved"""
        sm = HandoffStateMachine()
        sm.transition(HandoffState.CONNECTING)
        sm.transition(HandoffState.CALLBACK_SCHEDULED)
        sm.transition(HandoffState.RESOLVED)
        assert sm.state == HandoffState.RESOLVED

    def test_valid_ticket_path(self) -> None:
        """pending -> connecting -> ticket_created -> resolved"""
        sm = HandoffStateMachine()
        sm.transition(HandoffState.CONNECTING)
        sm.transition(HandoffState.TICKET_CREATED)
        sm.transition(HandoffState.RESOLVED)
        assert sm.state == HandoffState.RESOLVED

    def test_invalid_pending_to_connected(self) -> None:
        """Cannot jump from pending directly to connected."""
        sm = HandoffStateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.transition(HandoffState.CONNECTED)

    def test_invalid_pending_to_resolved(self) -> None:
        """Cannot jump from pending directly to resolved."""
        sm = HandoffStateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.transition(HandoffState.RESOLVED)

    def test_invalid_connected_to_callback(self) -> None:
        """Cannot go from connected to callback_scheduled."""
        sm = HandoffStateMachine()
        sm.transition(HandoffState.CONNECTING)
        sm.transition(HandoffState.CONNECTED)
        with pytest.raises(InvalidTransitionError):
            sm.transition(HandoffState.CALLBACK_SCHEDULED)

    def test_invalid_resolved_to_anything(self) -> None:
        """Resolved is terminal — no further transitions allowed."""
        sm = HandoffStateMachine()
        sm.transition(HandoffState.CONNECTING)
        sm.transition(HandoffState.CONNECTED)
        sm.transition(HandoffState.RESOLVED)
        with pytest.raises(InvalidTransitionError):
            sm.transition(HandoffState.PENDING)

    def test_history_tracks_all_states(self) -> None:
        sm = HandoffStateMachine()
        sm.transition(HandoffState.CONNECTING)
        sm.transition(HandoffState.CONNECTED)
        assert sm.history == [
            HandoffState.PENDING,
            HandoffState.CONNECTING,
            HandoffState.CONNECTED,
        ]

    def test_can_transition_returns_true_for_valid(self) -> None:
        sm = HandoffStateMachine()
        assert sm.can_transition(HandoffState.CONNECTING) is True

    def test_can_transition_returns_false_for_invalid(self) -> None:
        sm = HandoffStateMachine()
        assert sm.can_transition(HandoffState.RESOLVED) is False

    def test_is_terminal_false_for_non_terminal(self) -> None:
        sm = HandoffStateMachine()
        assert sm.is_terminal is False

    @pytest.mark.parametrize(
        "invalid_target",
        [
            HandoffState.CONNECTED,
            HandoffState.CALLBACK_SCHEDULED,
            HandoffState.TICKET_CREATED,
            HandoffState.RESOLVED,
        ],
    )
    def test_pending_rejects_all_except_connecting(
        self, invalid_target: HandoffState
    ) -> None:
        sm = HandoffStateMachine()
        with pytest.raises(InvalidTransitionError):
            sm.transition(invalid_target)


# ===================================================================
# Routing logic tests
# ===================================================================


class TestRoutingLogic:
    """Tests for handoff type determination based on context."""

    def test_business_hours_warm_handoff(self) -> None:
        """During business hours with agents → WARM."""
        orch, *_ = _make_orchestrator()
        request = _make_request()
        # Wednesday 10 AM
        now = datetime(2026, 4, 15, 10, 0)
        assert orch.determine_handoff_type(request, now=now) == HandoffType.WARM

    def test_off_hours_callback(self) -> None:
        """Off-hours → CALLBACK."""
        orch, *_ = _make_orchestrator()
        request = _make_request()
        # Wednesday 10 PM (after business hours)
        now = datetime(2026, 4, 15, 22, 0)
        assert orch.determine_handoff_type(request, now=now) == HandoffType.CALLBACK

    def test_weekend_callback(self) -> None:
        """Weekend → CALLBACK."""
        orch, *_ = _make_orchestrator()
        request = _make_request()
        # Saturday 10 AM
        now = datetime(2026, 4, 18, 10, 0)
        assert orch.determine_handoff_type(request, now=now) == HandoffType.CALLBACK

    def test_warm_unavailable_falls_to_callback(self) -> None:
        """Business hours but warm flow unavailable → CALLBACK."""
        orch, *_ = _make_orchestrator(warm_available=False)
        request = _make_request()
        now = datetime(2026, 4, 15, 10, 0)
        assert orch.determine_handoff_type(request, now=now) == HandoffType.CALLBACK

    def test_non_urgent_routes_to_ticket(self) -> None:
        """Classifier did not recommend escalation → TICKET."""
        orch, *_ = _make_orchestrator()
        request = _make_request(
            categories=["discrimination"],
            escalation_recommended=False,
        )
        now = datetime(2026, 4, 15, 10, 0)
        assert orch.determine_handoff_type(request, now=now) == HandoffType.TICKET


# ===================================================================
# Always-escalate topic tests
# ===================================================================


class TestAlwaysEscalateTopics:
    """Tests for the always-escalate topic list override."""

    def test_always_escalate_bypasses_threshold(self) -> None:
        """An always-escalate topic triggers handoff even at low confidence."""
        orch, *_ = _make_orchestrator()
        request = _make_request(
            categories=["discrimination"],
            confidence=0.3,
            escalation_recommended=False,
        )
        assert orch.should_handoff(request) is True

    def test_non_escalate_topic_below_threshold_rejected(self) -> None:
        """A normal topic below threshold does not trigger handoff."""
        orch, *_ = _make_orchestrator()
        request = _make_request(
            categories=["general_inquiry"],
            confidence=0.5,
            escalation_recommended=True,
        )
        assert orch.should_handoff(request) is False

    def test_non_escalate_topic_above_threshold_accepted(self) -> None:
        """A normal topic above threshold triggers handoff."""
        orch, *_ = _make_orchestrator()
        request = _make_request(
            categories=["general_inquiry"],
            confidence=0.9,
            escalation_recommended=True,
        )
        assert orch.should_handoff(request) is True

    def test_always_escalate_is_case_insensitive(self) -> None:
        """Topic matching should be case-insensitive."""
        orch, *_ = _make_orchestrator()
        request = _make_request(
            categories=["DISCRIMINATION"],
            confidence=0.1,
            escalation_recommended=False,
        )
        assert orch.should_handoff(request) is True

    def test_custom_always_escalate_list(self) -> None:
        """Custom always-escalate list should be respected."""
        cfg = HandoffConfig(always_escalate_topics=["custom_topic"])
        orch, *_ = _make_orchestrator(config=cfg)
        request = _make_request(
            categories=["custom_topic"],
            confidence=0.1,
            escalation_recommended=False,
        )
        assert orch.should_handoff(request) is True

    def test_no_escalation_when_not_recommended_and_no_match(self) -> None:
        """No handoff when not recommended and no always-escalate match."""
        orch, *_ = _make_orchestrator()
        request = _make_request(
            categories=["parking_info"],
            confidence=0.2,
            escalation_recommended=False,
        )
        assert orch.should_handoff(request) is False


# ===================================================================
# Timeout fallback tests
# ===================================================================


class TestTimeoutFallback:
    """Tests for warm handoff timeout → callback fallback."""

    @pytest.mark.asyncio
    async def test_warm_handoff_success(self) -> None:
        """Warm handoff succeeds within timeout."""
        orch, warm, callback, _ = _make_orchestrator()
        request = _make_request()
        now = datetime(2026, 4, 15, 10, 0)  # business hours
        result = await orch.execute(request, now=now)
        assert result.handoff_type == HandoffType.WARM
        assert result.state == HandoffState.CONNECTED
        assert warm.execute_count == 1
        assert callback.execute_count == 0

    @pytest.mark.asyncio
    async def test_warm_timeout_falls_back_to_callback(self) -> None:
        """Warm handoff timeout triggers automatic callback fallback."""
        cfg = HandoffConfig(sla=SLAConfig(warm_handoff_timeout_seconds=1))
        orch, warm, callback, _ = _make_orchestrator(
            config=cfg, warm_delay=5.0
        )
        request = _make_request()
        now = datetime(2026, 4, 15, 10, 0)
        result = await orch.execute(request, now=now)
        assert result.handoff_type == HandoffType.CALLBACK
        assert result.state == HandoffState.CALLBACK_SCHEDULED
        assert callback.execute_count == 1

    @pytest.mark.asyncio
    async def test_off_hours_goes_directly_to_callback(self) -> None:
        """Off-hours skips warm entirely, goes to callback."""
        orch, warm, callback, _ = _make_orchestrator()
        request = _make_request()
        now = datetime(2026, 4, 15, 22, 0)
        result = await orch.execute(request, now=now)
        assert result.handoff_type == HandoffType.CALLBACK
        assert warm.execute_count == 0
        assert callback.execute_count == 1

    @pytest.mark.asyncio
    async def test_ticket_flow_executed(self) -> None:
        """Non-urgent request routes to ticket creation."""
        orch, warm, callback, ticket = _make_orchestrator()
        request = _make_request(
            categories=["discrimination"],
            escalation_recommended=False,
        )
        now = datetime(2026, 4, 15, 10, 0)
        result = await orch.execute(request, now=now)
        assert result.handoff_type == HandoffType.TICKET
        assert ticket.execute_count == 1
        assert warm.execute_count == 0


# ===================================================================
# Business hours helper tests
# ===================================================================


class TestBusinessHours:
    """Tests for the _is_business_hours helper."""

    def test_within_hours(self) -> None:
        cfg = HandoffConfig()
        now = datetime(2026, 4, 15, 12, 0)  # Wednesday noon
        assert _is_business_hours(cfg, now) is True

    def test_before_hours(self) -> None:
        cfg = HandoffConfig()
        now = datetime(2026, 4, 15, 7, 0)  # Wednesday 7 AM
        assert _is_business_hours(cfg, now) is False

    def test_after_hours(self) -> None:
        cfg = HandoffConfig()
        now = datetime(2026, 4, 15, 18, 0)  # Wednesday 6 PM
        assert _is_business_hours(cfg, now) is False

    def test_at_start_boundary(self) -> None:
        cfg = HandoffConfig()
        now = datetime(2026, 4, 15, 8, 0)  # Wednesday 8 AM exactly
        assert _is_business_hours(cfg, now) is True

    def test_at_end_boundary(self) -> None:
        cfg = HandoffConfig()
        now = datetime(2026, 4, 15, 17, 0)  # Wednesday 5 PM exactly
        assert _is_business_hours(cfg, now) is False

    def test_weekend(self) -> None:
        cfg = HandoffConfig()
        now = datetime(2026, 4, 18, 12, 0)  # Saturday noon
        assert _is_business_hours(cfg, now) is False

    def test_custom_hours(self) -> None:
        cfg = HandoffConfig(
            business_hours=BusinessHoursConfig(
                start=time(9, 0),
                end=time(21, 0),
                days=[0, 1, 2, 3, 4, 5],  # Mon-Sat
            )
        )
        now = datetime(2026, 4, 18, 12, 0)  # Saturday noon
        assert _is_business_hours(cfg, now) is True


# ===================================================================
# Configuration tests
# ===================================================================


class TestConfiguration:
    """Tests for configuration loading."""

    def test_default_config_values(self) -> None:
        cfg = HandoffConfig()
        assert cfg.confidence_threshold == 0.7
        assert "discrimination" in cfg.always_escalate_topics
        assert cfg.business_hours.start == time(8, 0)
        assert cfg.business_hours.end == time(17, 0)
        assert cfg.sla.warm_handoff_timeout_seconds == 120

    def test_load_config_returns_defaults_when_no_file(self) -> None:
        cfg = load_config()
        assert isinstance(cfg, HandoffConfig)
        assert cfg.confidence_threshold == 0.7

    def test_load_config_from_yaml(self, tmp_path: object) -> None:
        from pathlib import Path

        config_file = Path(str(tmp_path)) / "handoff.yaml"
        config_file.write_text(
            "confidence_threshold: 0.5\n"
            "always_escalate_topics:\n"
            "  - custom_topic\n"
            "sla:\n"
            "  warm_handoff_timeout_seconds: 60\n"
        )
        cfg = load_config(config_file)
        assert cfg.confidence_threshold == 0.5
        assert cfg.always_escalate_topics == ["custom_topic"]
        assert cfg.sla.warm_handoff_timeout_seconds == 60

    def test_load_config_missing_file_returns_defaults(self) -> None:
        cfg = load_config("/nonexistent/path.yaml")
        assert isinstance(cfg, HandoffConfig)


# ===================================================================
# Model validation tests
# ===================================================================


class TestModels:
    """Tests for Pydantic model validation."""

    def test_escalation_signal_confidence_bounds(self) -> None:
        with pytest.raises(Exception):
            EscalationSignal(
                is_sensitive=True,
                confidence=1.5,
                escalation_recommended=True,
            )

    def test_handoff_state_enum_values(self) -> None:
        assert HandoffState.PENDING.value == "pending"
        assert HandoffState.CONNECTING.value == "connecting"
        assert HandoffState.CONNECTED.value == "connected"
        assert HandoffState.CALLBACK_SCHEDULED.value == "callback_scheduled"
        assert HandoffState.TICKET_CREATED.value == "ticket_created"
        assert HandoffState.RESOLVED.value == "resolved"

    def test_handoff_type_enum_values(self) -> None:
        assert HandoffType.WARM.value == "warm"
        assert HandoffType.CALLBACK.value == "callback"
        assert HandoffType.TICKET.value == "ticket"

    def test_handoff_result_creation(self) -> None:
        result = HandoffResult(
            handoff_type=HandoffType.WARM,
            state=HandoffState.CONNECTED,
            reference_number="HO-ABC12345",
            estimated_wait_minutes=5,
            citizen_message="You are being connected.",
        )
        assert result.handoff_type == HandoffType.WARM
        assert result.reference_number == "HO-ABC12345"
