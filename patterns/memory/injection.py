"""Context injection into agent system prompts.

Builds an augmented system prompt that includes the accumulated citizen
context so the agent can reference previously provided information without
re-asking.
"""

from __future__ import annotations

import logging
from typing import List

from .schema import CitizenContext

logger = logging.getLogger(__name__)

_CONTEXT_HEADER = (
    "\n\n--- Citizen Context (from previous turns) ---\n"
    "The citizen has already provided the following information. "
    "Do NOT ask for any of this again. Reference it naturally in your responses.\n"
)

_CONTEXT_FOOTER = "\n--- End Citizen Context ---\n"


def build_augmented_prompt(base_prompt: str, context: CitizenContext) -> str:
    """Append citizen context to the base system prompt.

    If no entities have been captured yet, returns the base prompt unchanged.
    """
    if not context.has_entities():
        return base_prompt

    lines: List[str] = context.summary_lines()
    context_block = _CONTEXT_HEADER + "\n".join(f"- {line}" for line in lines) + _CONTEXT_FOOTER

    logger.debug("Injecting %d context lines into system prompt", len(lines))
    return base_prompt + context_block
