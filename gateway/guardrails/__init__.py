"""Guardrails module for Maplewood Civic Services Agent.

Provides structured guardrail rules, refusal response building, and prompt block
generation for safe, responsible AI interactions with citizens.
"""

from gateway.guardrails.models import GuardrailCategory, GuardrailRule, RefusalResponse
from gateway.guardrails.rules import GUARDRAIL_RULES, get_rule
from gateway.guardrails.refusal import build_refusal_response
from gateway.guardrails.prompt import generate_prompt_block

__all__ = [
    "GuardrailCategory",
    "GuardrailRule",
    "RefusalResponse",
    "GUARDRAIL_RULES",
    "get_rule",
    "build_refusal_response",
    "generate_prompt_block",
]
