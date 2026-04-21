"""Tests for guardrail integration into agent system prompts."""

import os

import pytest

from gateway.guardrails.models import GuardrailCategory
from gateway.guardrails.prompt import generate_prompt_block
from patterns.utils.prompt import BASE_PROMPT, GUARDRAIL_BLOCK, build_system_prompt

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBuildSystemPrompt:
    """Tests for the system prompt assembly function."""

    def test_includes_base_prompt(self):
        prompt = build_system_prompt()
        assert BASE_PROMPT in prompt

    def test_includes_guardrail_block(self):
        prompt = build_system_prompt()
        assert "## Guardrails" in prompt
        assert GUARDRAIL_BLOCK in prompt

    def test_guardrail_block_matches_generator(self):
        assert GUARDRAIL_BLOCK == generate_prompt_block()

    def test_guardrails_always_present_without_context(self):
        prompt = build_system_prompt()
        assert "## Guardrails" in prompt

    def test_guardrails_always_present_with_context(self):
        prompt = build_system_prompt(context_block="Some session context.")
        assert "## Guardrails" in prompt

    def test_context_block_appended_when_provided(self):
        context = "User session context: citizen is logged in."
        prompt = build_system_prompt(context_block=context)
        assert context in prompt

    def test_context_block_absent_when_not_provided(self):
        prompt = build_system_prompt()
        assert prompt.count("\n\n") == 1

    def test_guardrail_before_context_block(self):
        context = "Dynamic context goes here."
        prompt = build_system_prompt(context_block=context)
        guardrail_pos = prompt.index("## Guardrails")
        context_pos = prompt.index(context)
        assert guardrail_pos < context_pos

    def test_all_guardrail_categories_present(self):
        prompt = build_system_prompt()
        for category in GuardrailCategory:
            assert category.value in prompt, f"Missing guardrail category {category}"


class TestGuardrailContentInPrompt:
    """Verify the four explicit acceptance criteria guardrails appear in the prompt."""

    def test_no_legal_advice_instruction(self):
        prompt = build_system_prompt()
        assert "legal" in prompt.lower()
        assert "City Attorney" in prompt

    def test_no_timeline_promises_instruction(self):
        prompt = build_system_prompt()
        assert "timeline" in prompt.lower() or "guarantee" in prompt.lower()

    def test_escalation_for_sensitive_topics(self):
        prompt = build_system_prompt()
        assert "Code Enforcement" in prompt
        assert "ADA Coordinator" in prompt

    def test_refusal_explains_why_and_what(self):
        prompt = build_system_prompt()
        assert "not able to" in prompt.lower() or "cannot" in prompt.lower()
        assert "contact" in prompt.lower()


class TestAgentFilesUseSharedPrompt:
    """Verify both agent source files import the shared prompt builder."""

    @pytest.fixture()
    def strands_source(self):
        path = os.path.join(
            REPO_ROOT, "patterns", "strands-single-agent", "basic_agent.py"
        )
        with open(path) as f:
            return f.read()

    @pytest.fixture()
    def langgraph_source(self):
        path = os.path.join(
            REPO_ROOT, "patterns", "langgraph-single-agent", "langgraph_agent.py"
        )
        with open(path) as f:
            return f.read()

    def test_strands_imports_build_system_prompt(self, strands_source):
        assert "from utils.prompt import build_system_prompt" in strands_source

    def test_strands_uses_build_system_prompt(self, strands_source):
        assert "SYSTEM_PROMPT = build_system_prompt()" in strands_source

    def test_strands_no_hardcoded_prompt(self, strands_source):
        assert "You are a helpful assistant with access to tools" not in strands_source

    def test_langgraph_imports_build_system_prompt(self, langgraph_source):
        assert "from utils.prompt import build_system_prompt" in langgraph_source

    def test_langgraph_uses_build_system_prompt(self, langgraph_source):
        assert "SYSTEM_PROMPT = build_system_prompt()" in langgraph_source

    def test_langgraph_no_hardcoded_prompt(self, langgraph_source):
        assert "You are a helpful assistant with access to tools" not in langgraph_source
