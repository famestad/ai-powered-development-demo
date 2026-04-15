"""Pydantic models for guardrail rules and refusal responses."""

from enum import Enum

from pydantic import BaseModel, Field


class GuardrailCategory(str, Enum):
    """Categories of topics the agent must not handle directly."""

    LEGAL_ADVICE = "LEGAL_ADVICE"
    TIMELINE_PROMISES = "TIMELINE_PROMISES"
    CODE_ENFORCEMENT_COMPLAINTS = "CODE_ENFORCEMENT_COMPLAINTS"
    ADA_REQUESTS = "ADA_REQUESTS"
    GENERAL_SENSITIVE = "GENERAL_SENSITIVE"


class GuardrailRule(BaseModel):
    """A single guardrail rule defining a restricted topic category."""

    category: GuardrailCategory
    description: str = Field(
        description="Human-readable explanation of what this rule covers."
    )
    detection_hints: list[str] = Field(
        description="Example phrases or patterns that indicate this category."
    )
    response_template: str = Field(
        description="The refusal message template for this category. "
        "May contain {redirect} placeholder for the redirect destination."
    )


class RefusalResponse(BaseModel):
    """A structured refusal response returned to the citizen."""

    citizen_message: str = Field(
        description="The polite, citizen-facing refusal message."
    )
    reason: str = Field(
        description="Internal reason for the refusal (for logging/audit)."
    )
    category: GuardrailCategory
