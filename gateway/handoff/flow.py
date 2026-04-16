"""HandoffFlow protocol that Issue #19's flow implementations must satisfy.

Each concrete flow (warm handoff, scheduled callback, ticket creation) must
implement this protocol so the orchestrator can route to it uniformly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from gateway.handoff.models import HandoffRequest, HandoffResult


@runtime_checkable
class HandoffFlow(Protocol):
    """Protocol that all handoff flow implementations must satisfy.

    Issue #19 will provide concrete implementations for:
    - ``WarmHandoffFlow``  — live transfer to a human agent
    - ``ScheduledCallbackFlow`` — schedule a callback for the citizen
    - ``TicketCreationFlow`` — create a support ticket for async resolution
    """

    async def execute(self, request: HandoffRequest) -> HandoffResult:
        """Execute the handoff flow and return the result.

        Args:
            request: The handoff request containing escalation signal,
                session summary, and citizen context.

        Returns:
            A HandoffResult describing the outcome and next steps.
        """
        ...

    async def cancel(self, reference_number: str) -> bool:
        """Cancel a previously initiated handoff.

        Args:
            reference_number: The reference number from the HandoffResult.

        Returns:
            True if the cancellation succeeded, False otherwise.
        """
        ...

    def is_available(self) -> bool:
        """Check whether this flow is currently available.

        For example, warm handoff may only be available during business
        hours when human agents are staffed.

        Returns:
            True if the flow can currently accept requests.
        """
        ...
