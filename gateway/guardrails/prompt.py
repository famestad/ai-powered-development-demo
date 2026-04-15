"""Prompt block generator for injecting guardrail rules into agent system prompts."""

from gateway.guardrails.models import GuardrailCategory, GuardrailRule
from gateway.guardrails.rules import GUARDRAIL_RULES

_PROMPT_HEADER = (
    "## Guardrails\n\n"
    "You MUST follow these guardrail rules. When a citizen's message matches "
    "any of the categories below, you MUST refuse to handle the request directly "
    "and instead provide the specified response.\n"
)


def _format_rule_block(rule: GuardrailRule) -> str:
    """Format a single guardrail rule into a prompt-ready text block."""
    hints = ", ".join(f'"{h}"' for h in rule.detection_hints)
    return (
        f"### {rule.category.value}\n"
        f"**Description:** {rule.description}\n"
        f"**Detection hints:** {hints}\n"
        f"**Required response:** {rule.response_template}\n"
    )


def generate_prompt_block(
    categories: list[GuardrailCategory] | None = None,
) -> str:
    """Generate a system prompt section containing active guardrail rules.

    The output is a formatted text block suitable for injection into an agent's
    system prompt. It lists each active guardrail rule with its description,
    detection hints, and required refusal response.

    Args:
        categories: Optional list of categories to include. If None, all
            categories are included.

    Returns:
        A formatted string containing the guardrail prompt block.
    """
    if categories is None:
        rules = list(GUARDRAIL_RULES.values())
    else:
        rules = [GUARDRAIL_RULES[cat] for cat in categories]

    rule_blocks = "\n".join(_format_rule_block(rule) for rule in rules)
    return f"{_PROMPT_HEADER}\n{rule_blocks}"
