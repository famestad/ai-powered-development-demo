"""Handoff orchestrator — routes escalation signals to the correct flow.

Routing logic:
1. Always-escalate topics bypass the confidence threshold.
2. During business hours with available agents → warm handoff.
3. Off-hours or agents unavailable → scheduled callback.
4. Non-urgent / low-confidence → ticket creation.
5. If warm handoff times out (SLA exceeded) → automatic fallback to callback.

Citizens are *never* left stranded — every path produces a HandoffResult.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from gateway.handoff.config import HandoffConfig
from gateway.handoff.flow import HandoffFlow
from gateway.handoff.models import (
    HandoffRequest,
    HandoffResult,
    HandoffState,
    HandoffType,
)
from gateway.handoff.state_machine import HandoffStateMachine


def _is_business_hours(config: HandoffConfig, now: datetime) -> bool:
    """Return True if *now* falls within configured business hours."""
    if now.weekday() not in config.business_hours.days:
        return False
    current_time = now.time()
    return config.business_hours.start <= current_time < config.business_hours.end


def _generate_reference() -> str:
    """Generate a unique reference number for a handoff."""
    return f"HO-{uuid.uuid4().hex[:8].upper()}"


class HandoffOrchestrator:
    """Routes escalation signals to the appropriate handoff flow.

    Args:
        config: Orchestrator configuration (business hours, SLAs, etc.).
        warm_flow: The warm-handoff flow implementation.
        callback_flow: The scheduled-callback flow implementation.
        ticket_flow: The ticket-creation flow implementation.
    """

    def __init__(
        self,
        config: HandoffConfig,
        warm_flow: HandoffFlow,
        callback_flow: HandoffFlow,
        ticket_flow: HandoffFlow,
    ) -> None:
        self._config = config
        self._flows: dict[HandoffType, HandoffFlow] = {
            HandoffType.WARM: warm_flow,
            HandoffType.CALLBACK: callback_flow,
            HandoffType.TICKET: ticket_flow,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_handoff(self, request: HandoffRequest) -> bool:
        """Decide whether the request warrants a human handoff.

        Returns ``True`` when:
        - The classifier recommended escalation **and** confidence meets the
          threshold, **or**
        - Any detected category is in the always-escalate list.
        """
        signal = request.escalation_signal

        # Always-escalate topics bypass confidence threshold
        for category in signal.categories:
            if category.lower() in (
                t.lower() for t in self._config.always_escalate_topics
            ):
                return True

        if signal.escalation_recommended:
            return signal.confidence >= self._config.confidence_threshold

        return False

    def determine_handoff_type(
        self,
        request: HandoffRequest,
        now: datetime | None = None,
    ) -> HandoffType:
        """Choose the best handoff pattern for the request.

        Decision matrix:
        - Business hours + warm flow available → WARM
        - Off-hours or warm flow unavailable → CALLBACK
        - Non-urgent (classifier did not explicitly recommend) → TICKET
        """
        now = now or datetime.utcnow()
        signal = request.escalation_signal

        # Non-urgent: classifier didn't explicitly recommend escalation
        # but an always-escalate topic triggered handoff
        if not signal.escalation_recommended:
            return HandoffType.TICKET

        # Urgent during business hours with available agents
        if _is_business_hours(self._config, now):
            warm = self._flows[HandoffType.WARM]
            if warm.is_available():
                return HandoffType.WARM

        # Urgent but off-hours or warm unavailable
        return HandoffType.CALLBACK

    async def execute(
        self,
        request: HandoffRequest,
        now: datetime | None = None,
    ) -> HandoffResult:
        """Run the full handoff flow for *request*.

        1. Determine the handoff type.
        2. Attempt the selected flow.
        3. If warm handoff times out, fall back to callback.
        4. Return a HandoffResult — never raises for flow failures.
        """
        handoff_type = self.determine_handoff_type(request, now=now)
        sm = HandoffStateMachine()

        # pending -> connecting
        sm.transition(HandoffState.CONNECTING)

        if handoff_type == HandoffType.WARM:
            result = await self._attempt_warm_with_fallback(request, sm)
        else:
            flow = self._flows[handoff_type]
            result = await flow.execute(request)
            self._advance_state(sm, handoff_type)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _attempt_warm_with_fallback(
        self,
        request: HandoffRequest,
        sm: HandoffStateMachine,
    ) -> HandoffResult:
        """Attempt warm handoff; fall back to callback on timeout."""
        warm = self._flows[HandoffType.WARM]
        timeout = self._config.sla.warm_handoff_timeout_seconds

        try:
            result = await asyncio.wait_for(
                warm.execute(request),
                timeout=timeout,
            )
            sm.transition(HandoffState.CONNECTED)
            return result
        except asyncio.TimeoutError:
            # Warm handoff timed out — fall back to callback
            callback = self._flows[HandoffType.CALLBACK]
            result = await callback.execute(request)
            sm.transition(HandoffState.CALLBACK_SCHEDULED)
            return result

    @staticmethod
    def _advance_state(
        sm: HandoffStateMachine, handoff_type: HandoffType
    ) -> None:
        """Move the state machine to the terminal state for *handoff_type*."""
        target_map: dict[HandoffType, HandoffState] = {
            HandoffType.WARM: HandoffState.CONNECTED,
            HandoffType.CALLBACK: HandoffState.CALLBACK_SCHEDULED,
            HandoffType.TICKET: HandoffState.TICKET_CREATED,
        }
        sm.transition(target_map[handoff_type])
