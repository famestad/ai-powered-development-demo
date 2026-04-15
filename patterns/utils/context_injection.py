"""
Context injection for civic services agent system prompts.

Provides the middleware that augments a base system prompt with the
current CitizenContext before each agent turn. This module works for
both Strands and LangGraph agent patterns.

Depends on Issue #4 (memory wrapper) for the actual load_context()
implementation. Until that lands, load_citizen_context() returns an
empty CitizenContext so agents operate with a clean initial prompt.
"""

from __future__ import annotations

import logging
from typing import Optional

from utils.citizen_context import CitizenContext

logger = logging.getLogger(__name__)

# --- Context-aware prompt instructions -----------------------------------
# These are appended only when citizen context exists, instructing the agent
# on how to handle known vs. unknown information.

_CONTEXT_INSTRUCTIONS = (
    "\n\n--- Context Instructions ---\n"
    "You have prior context about this citizen from earlier in the conversation. "
    "Use it naturally — do NOT re-ask for information you already know.\n"
    "However, if any detail seems stale or uncertain (e.g., the citizen hints "
    "their address changed), confirm it before relying on it.\n"
    "If the citizen corrects any detail, treat the correction as authoritative."
)


def load_citizen_context(
    session_id: str, user_id: str
) -> CitizenContext:
    """Load the current CitizenContext for a session from the memory wrapper.

    This is a placeholder that returns an empty context until Issue #4
    (memory wrapper with load_context()) is merged. Once available, this
    function should delegate to the memory wrapper's load_context() method.

    Args:
        session_id: The current conversation session ID.
        user_id: The authenticated user/citizen ID.

    Returns:
        CitizenContext with any known citizen information, or an empty
        CitizenContext for new sessions.
    """
    # TODO: Replace with memory wrapper call once Issue #4 lands:
    #   from utils.memory_wrapper import MemoryWrapper
    #   wrapper = MemoryWrapper(session_id=session_id, user_id=user_id)
    #   return wrapper.load_context()
    logger.debug(
        "load_citizen_context called (stub) for session=%s user=%s",
        session_id,
        user_id,
    )
    return CitizenContext()


def build_system_prompt(
    base_prompt: str,
    citizen_context: Optional[CitizenContext] = None,
) -> str:
    """Build the full system prompt by appending citizen context if available.

    This is the core template approach: base system prompt + optional
    context block appended at runtime. If no context exists (new session
    or empty CitizenContext), the base prompt is returned unmodified.

    Args:
        base_prompt: The static base system prompt for the agent.
        citizen_context: The current CitizenContext, or None.

    Returns:
        The augmented system prompt string.
    """
    if citizen_context is None or citizen_context.is_empty():
        return base_prompt

    context_block = citizen_context.to_prompt_block()
    return f"{base_prompt}\n\n{context_block}{_CONTEXT_INSTRUCTIONS}"
