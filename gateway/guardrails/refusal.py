"""Refusal response builder for guardrail violations."""

from gateway.guardrails.models import GuardrailCategory, RefusalResponse
from gateway.guardrails.rules import get_rule

_CATEGORY_REASONS: dict[GuardrailCategory, str] = {
    GuardrailCategory.LEGAL_ADVICE: (
        "Request involves legal advice or ordinance interpretation"
    ),
    GuardrailCategory.TIMELINE_PROMISES: (
        "Request asks for guaranteed timelines on city processes"
    ),
    GuardrailCategory.CODE_ENFORCEMENT_COMPLAINTS: (
        "Request involves a code enforcement complaint requiring human handling"
    ),
    GuardrailCategory.ADA_REQUESTS: (
        "Request involves ADA accommodations requiring ADA Coordinator"
    ),
    GuardrailCategory.GENERAL_SENSITIVE: (
        "Request involves a sensitive topic requiring human judgment"
    ),
}


def build_refusal_response(category: GuardrailCategory) -> RefusalResponse:
    """Build a polite refusal response for a given guardrail category.

    Returns a RefusalResponse containing a citizen-facing message with
    appropriate redirects and an internal reason for logging.

    Args:
        category: The guardrail category that was triggered.

    Returns:
        A RefusalResponse with citizen_message, reason, and category.
    """
    rule = get_rule(category)
    return RefusalResponse(
        citizen_message=rule.response_template,
        reason=_CATEGORY_REASONS[category],
        category=category,
    )
