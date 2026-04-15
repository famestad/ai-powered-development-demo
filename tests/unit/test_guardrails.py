"""Unit tests for the gateway.guardrails module."""

import pytest

from gateway.guardrails.models import GuardrailCategory, GuardrailRule, RefusalResponse
from gateway.guardrails.rules import GUARDRAIL_RULES, get_rule
from gateway.guardrails.refusal import build_refusal_response
from gateway.guardrails.prompt import generate_prompt_block


# ---------------------------------------------------------------------------
# Rule completeness
# ---------------------------------------------------------------------------

ALL_CATEGORIES = [
    GuardrailCategory.LEGAL_ADVICE,
    GuardrailCategory.TIMELINE_PROMISES,
    GuardrailCategory.CODE_ENFORCEMENT_COMPLAINTS,
    GuardrailCategory.ADA_REQUESTS,
    GuardrailCategory.GENERAL_SENSITIVE,
]


class TestGuardrailRules:
    """Tests for guardrail rule definitions."""

    def test_all_five_categories_defined(self):
        """All 5 required categories must be present in GUARDRAIL_RULES."""
        for category in ALL_CATEGORIES:
            assert category in GUARDRAIL_RULES, f"Missing rule for {category}"

    def test_no_extra_categories(self):
        """Only the 5 specified categories should exist."""
        assert set(GUARDRAIL_RULES.keys()) == set(ALL_CATEGORIES)

    @pytest.mark.parametrize("category", ALL_CATEGORIES)
    def test_rule_fields_are_complete(self, category):
        """Each rule must have non-empty description, detection_hints, and response_template."""
        rule = GUARDRAIL_RULES[category]
        assert isinstance(rule, GuardrailRule)
        assert rule.description, f"{category} has empty description"
        assert len(rule.detection_hints) > 0, f"{category} has no detection_hints"
        assert rule.response_template, f"{category} has empty response_template"

    @pytest.mark.parametrize("category", ALL_CATEGORIES)
    def test_rule_category_matches_key(self, category):
        """The rule's category field must match its dictionary key."""
        rule = GUARDRAIL_RULES[category]
        assert rule.category == category

    def test_get_rule_returns_correct_rule(self):
        """get_rule should return the matching rule for a valid category."""
        rule = get_rule(GuardrailCategory.LEGAL_ADVICE)
        assert rule.category == GuardrailCategory.LEGAL_ADVICE
        assert "legal" in rule.description.lower()

    def test_get_rule_raises_for_invalid_key(self):
        """get_rule should raise KeyError for an unknown category."""
        with pytest.raises(KeyError):
            get_rule("NOT_A_CATEGORY")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Refusal response builder
# ---------------------------------------------------------------------------


class TestRefusalResponseBuilder:
    """Tests for the refusal response builder."""

    @pytest.mark.parametrize("category", ALL_CATEGORIES)
    def test_builds_response_for_each_category(self, category):
        """build_refusal_response must return a valid RefusalResponse for every category."""
        response = build_refusal_response(category)
        assert isinstance(response, RefusalResponse)
        assert response.category == category
        assert response.citizen_message, f"Empty citizen_message for {category}"
        assert response.reason, f"Empty reason for {category}"

    def test_legal_advice_response_contains_redirect(self):
        """Legal advice refusal should mention the City Attorney's office."""
        response = build_refusal_response(GuardrailCategory.LEGAL_ADVICE)
        assert "City Attorney" in response.citizen_message

    def test_timeline_response_contains_redirect(self):
        """Timeline refusal should suggest contacting the relevant department."""
        response = build_refusal_response(GuardrailCategory.TIMELINE_PROMISES)
        assert "department" in response.citizen_message.lower()

    def test_code_enforcement_response_contains_redirect(self):
        """Code enforcement refusal should mention the Code Enforcement Division."""
        response = build_refusal_response(GuardrailCategory.CODE_ENFORCEMENT_COMPLAINTS)
        assert "Code Enforcement" in response.citizen_message

    def test_ada_response_contains_redirect(self):
        """ADA refusal should mention the ADA Coordinator."""
        response = build_refusal_response(GuardrailCategory.ADA_REQUESTS)
        assert "ADA Coordinator" in response.citizen_message

    def test_general_sensitive_response_contains_redirect(self):
        """General sensitive refusal should mention the City Manager's office."""
        response = build_refusal_response(GuardrailCategory.GENERAL_SENSITIVE)
        assert "City Manager" in response.citizen_message


# ---------------------------------------------------------------------------
# Prompt block generator
# ---------------------------------------------------------------------------


class TestPromptBlockGenerator:
    """Tests for the prompt block generator."""

    def test_generates_well_formed_output(self):
        """The full prompt block must contain the header and all categories."""
        block = generate_prompt_block()
        assert "## Guardrails" in block
        assert "MUST" in block
        for category in ALL_CATEGORIES:
            assert category.value in block

    def test_contains_all_detection_hints(self):
        """The prompt block must include detection hints for every category."""
        block = generate_prompt_block()
        for rule in GUARDRAIL_RULES.values():
            for hint in rule.detection_hints:
                assert hint in block, f"Missing hint '{hint}' for {rule.category}"

    def test_contains_all_response_templates(self):
        """The prompt block must include response templates for every category."""
        block = generate_prompt_block()
        for rule in GUARDRAIL_RULES.values():
            assert rule.response_template in block, (
                f"Missing response template for {rule.category}"
            )

    def test_filter_by_categories(self):
        """When categories are specified, only those should appear in output."""
        subset = [GuardrailCategory.LEGAL_ADVICE, GuardrailCategory.ADA_REQUESTS]
        block = generate_prompt_block(categories=subset)

        assert GuardrailCategory.LEGAL_ADVICE.value in block
        assert GuardrailCategory.ADA_REQUESTS.value in block
        assert GuardrailCategory.TIMELINE_PROMISES.value not in block
        assert GuardrailCategory.CODE_ENFORCEMENT_COMPLAINTS.value not in block
        assert GuardrailCategory.GENERAL_SENSITIVE.value not in block

    def test_empty_categories_list_returns_header_only(self):
        """An empty categories list should return just the header with no rules."""
        block = generate_prompt_block(categories=[])
        assert "## Guardrails" in block
        for category in ALL_CATEGORIES:
            assert category.value not in block

    def test_prompt_block_is_string(self):
        """The output must be a plain string."""
        block = generate_prompt_block()
        assert isinstance(block, str)
