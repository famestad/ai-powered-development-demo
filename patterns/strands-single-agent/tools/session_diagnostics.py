"""Strands diagnostic tool for inspecting CitizenContext at runtime.

This tool is for internal/developer use only — it must NOT be exposed to citizens.
It allows the agent to inspect the current session context for debugging and
to generate handoff summaries.
"""

import json
import logging
from typing import Optional

from strands import tool

from citizen_context import (
    CitizenContext,
    MemoryLogger,
    generate_session_summary,
)

logger = logging.getLogger(__name__)

# Module-level context store, keyed by session_id.
# In production, this would be backed by AgentCore Memory;
# this in-memory dict supports local development and testing.
_session_contexts: dict[str, CitizenContext] = {}


def get_context(session_id: str) -> Optional[CitizenContext]:
    """Retrieve the CitizenContext for a given session.

    Args:
        session_id: The session identifier to look up.

    Returns:
        Optional[CitizenContext]: The context if found, otherwise None.
    """
    return _session_contexts.get(session_id)


def store_context(context: CitizenContext) -> None:
    """Store or update a CitizenContext in the session store.

    Also logs the creation via MemoryLogger for observability.

    Args:
        context: The CitizenContext instance to store.
    """
    memory_logger = MemoryLogger(
        session_id=context.session_id,
        actor_id=context.actor_id,
    )
    _session_contexts[context.session_id] = context
    memory_logger.log_context_created(context=context)


def clear_context(session_id: str) -> bool:
    """Remove a CitizenContext from the session store.

    Args:
        session_id: The session identifier to remove.

    Returns:
        bool: True if the context was found and removed, False otherwise.
    """
    if session_id in _session_contexts:
        del _session_contexts[session_id]
        return True
    return False


@tool
def inspect_session_context(session_id: str) -> str:
    """Inspect the current CitizenContext for a session (dev/debug only).

    Returns the full contents of the CitizenContext as a JSON string.
    This tool is for internal agent diagnostics only and must NOT be
    exposed to citizens.

    Args:
        session_id: The session identifier to inspect.

    Returns:
        str: JSON representation of the CitizenContext, or an error message
            if no context exists for the given session.
    """
    context = get_context(session_id=session_id)
    if context is None:
        return json.dumps(
            {"error": f"No context found for session_id: {session_id}"}
        )

    memory_logger = MemoryLogger(
        session_id=context.session_id,
        actor_id=context.actor_id,
    )
    memory_logger.log_context_retrieved()

    return json.dumps(context.to_dict(), indent=2)


@tool
def get_session_summary(session_id: str) -> str:
    """Generate a human-readable session summary for handoff to a human agent.

    Produces a structured summary of the citizen's context and conversation
    trajectory, designed for the handoff-to-human flow. This tool is for
    internal agent use only and must NOT be exposed to citizens.

    Args:
        session_id: The session identifier to summarize.

    Returns:
        str: A human-readable summary string, or an error message
            if no context exists for the given session.
    """
    context = get_context(session_id=session_id)
    if context is None:
        return json.dumps(
            {"error": f"No context found for session_id: {session_id}"}
        )

    summary = generate_session_summary(context=context)

    memory_logger = MemoryLogger(
        session_id=context.session_id,
        actor_id=context.actor_id,
    )
    memory_logger.log_summary_generated(summary=summary)

    return summary
