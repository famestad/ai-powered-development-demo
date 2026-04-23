"""System prompt assembly for Maplewood Civic Services agents.

Combines the base agent prompt with the always-present guardrail block
and an optional dynamic context block (for future use by Issue #6).
"""

from gateway.guardrails.prompt import generate_prompt_block

BASE_PROMPT = (
    "You are a helpful assistant for the City of Maplewood. You help citizens "
    "with questions about permits, utilities, public records, city council, "
    "parks & recreation, 311 service requests, and zoning inquiries. "
    "You have access to tools via the Gateway and Code Interpreter. "
    "When asked about your tools, list them and explain what they do."
)

GUARDRAIL_BLOCK = generate_prompt_block()


def build_system_prompt(context_block: str | None = None) -> str:
    """Assemble the full system prompt for a Maplewood agent.

    Args:
        context_block: Optional dynamic context (e.g. session or user context).
            Appended after the guardrail block when provided.

    Returns:
        The complete system prompt string.
    """
    parts = [BASE_PROMPT, GUARDRAIL_BLOCK]
    if context_block:
        parts.append(context_block)
    return "\n\n".join(parts)
