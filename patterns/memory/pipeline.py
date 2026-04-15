"""Memory pipeline orchestrator.

Coordinates the extract-merge-inject cycle for each conversation turn.
Provides an in-memory store keyed by (user_id, session_id) so context
persists across turns within the same session. This augments (does not
replace) the existing AgentCoreMemorySessionManager / AgentCoreMemorySaver
that handle raw conversation history.
"""

from __future__ import annotations

import logging
from typing import Dict, Tuple

from .extraction import extract_entities
from .injection import build_augmented_prompt
from .schema import CitizenContext

logger = logging.getLogger(__name__)

# In-memory store: (user_id, session_id) -> CitizenContext
_context_store: Dict[Tuple[str, str], CitizenContext] = {}


class MemoryPipeline:
    """Orchestrates entity extraction, context merging, and prompt injection.

    Usage (per conversation turn):
        pipeline = MemoryPipeline(user_id, session_id)
        pipeline.process_message(user_message)
        augmented_prompt = pipeline.inject_context(base_system_prompt)
        # ... generate agent response ...
    """

    def __init__(self, user_id: str, session_id: str) -> None:
        self.user_id = user_id
        self.session_id = session_id
        self._key = (user_id, session_id)

    @property
    def context(self) -> CitizenContext:
        """Get the current accumulated context for this session."""
        if self._key not in _context_store:
            _context_store[self._key] = CitizenContext()
        return _context_store[self._key]

    def process_message(self, message: str) -> CitizenContext:
        """Extract entities from a citizen message and merge into stored context.

        Returns the updated CitizenContext after merging.
        """
        extracted = extract_entities(message)
        self.context.merge(extracted)
        logger.info(
            "Memory pipeline processed message for (%s, %s): %d entities tracked",
            self.user_id,
            self.session_id,
            len(self.context.summary_lines()),
        )
        return self.context

    def inject_context(self, base_prompt: str) -> str:
        """Build an augmented system prompt with the current citizen context."""
        return build_augmented_prompt(base_prompt, self.context)

    def get_context(self) -> CitizenContext:
        """Return the current context (read-only access)."""
        return self.context

    @staticmethod
    def clear_session(user_id: str, session_id: str) -> None:
        """Remove stored context for a session (for testing / cleanup)."""
        key = (user_id, session_id)
        _context_store.pop(key, None)
