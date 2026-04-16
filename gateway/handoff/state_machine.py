"""State machine for tracking handoff lifecycle.

Enforces valid transitions between handoff states and prevents invalid
state jumps.  The allowed transitions are:

    pending  ->  connecting
    connecting  ->  connected | callback_scheduled | ticket_created
    connected  ->  resolved
    callback_scheduled  ->  resolved
    ticket_created  ->  resolved
"""

from __future__ import annotations

from gateway.handoff.models import HandoffState


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current: HandoffState, target: HandoffState) -> None:
        self.current = current
        self.target = target
        super().__init__(
            f"Invalid handoff state transition: {current.value} -> {target.value}"
        )


# Allowed transitions: current_state -> set of valid next states
_TRANSITIONS: dict[HandoffState, set[HandoffState]] = {
    HandoffState.PENDING: {HandoffState.CONNECTING},
    HandoffState.CONNECTING: {
        HandoffState.CONNECTED,
        HandoffState.CALLBACK_SCHEDULED,
        HandoffState.TICKET_CREATED,
    },
    HandoffState.CONNECTED: {HandoffState.RESOLVED},
    HandoffState.CALLBACK_SCHEDULED: {HandoffState.RESOLVED},
    HandoffState.TICKET_CREATED: {HandoffState.RESOLVED},
    HandoffState.RESOLVED: set(),
}


class HandoffStateMachine:
    """Tracks the lifecycle of a single handoff request.

    Usage::

        sm = HandoffStateMachine()          # starts in PENDING
        sm.transition(HandoffState.CONNECTING)
        sm.transition(HandoffState.CONNECTED)
        sm.transition(HandoffState.RESOLVED)
    """

    def __init__(self, initial: HandoffState = HandoffState.PENDING) -> None:
        self._state = initial
        self._history: list[HandoffState] = [initial]

    @property
    def state(self) -> HandoffState:
        """Return the current state."""
        return self._state

    @property
    def history(self) -> list[HandoffState]:
        """Return the full history of states this handoff has been in."""
        return list(self._history)

    def can_transition(self, target: HandoffState) -> bool:
        """Check whether a transition to *target* is valid."""
        return target in _TRANSITIONS.get(self._state, set())

    def transition(self, target: HandoffState) -> None:
        """Transition to *target*, raising on invalid transitions.

        Args:
            target: The desired next state.

        Raises:
            InvalidTransitionError: If the transition is not allowed.
        """
        if not self.can_transition(target):
            raise InvalidTransitionError(self._state, target)
        self._state = target
        self._history.append(target)

    @property
    def is_terminal(self) -> bool:
        """Return ``True`` if the current state has no outgoing transitions."""
        return len(_TRANSITIONS.get(self._state, set())) == 0
