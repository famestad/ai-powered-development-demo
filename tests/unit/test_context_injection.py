"""Tests for context injection middleware (build_system_prompt, load_citizen_context)."""

import sys
from pathlib import Path

# Add patterns directory to the path so we can import utils modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "patterns"))

from utils.citizen_context import CitizenContext
from utils.context_injection import build_system_prompt, load_citizen_context

BASE_PROMPT = "You are a helpful civic services assistant."


class TestBuildSystemPrompt:
    def test_no_context_returns_base_prompt(self):
        result = build_system_prompt(BASE_PROMPT, None)
        assert result == BASE_PROMPT

    def test_empty_context_returns_base_prompt(self):
        result = build_system_prompt(BASE_PROMPT, CitizenContext())
        assert result == BASE_PROMPT

    def test_with_context_appends_block(self):
        ctx = CitizenContext(name="Jane Doe", case_number="CASE-001")
        result = build_system_prompt(BASE_PROMPT, ctx)

        # Base prompt is preserved at the start
        assert result.startswith(BASE_PROMPT)

        # Context block is appended
        assert "Known citizen context:" in result
        assert "Name: Jane Doe" in result
        assert "Case #: CASE-001" in result

    def test_with_context_includes_instructions(self):
        ctx = CitizenContext(name="Jane Doe")
        result = build_system_prompt(BASE_PROMPT, ctx)

        # Context instructions are included
        assert "do NOT re-ask for information you already know" in result
        assert "confirm it before relying on it" in result
        assert "correction as authoritative" in result

    def test_instructions_not_added_for_empty_context(self):
        result = build_system_prompt(BASE_PROMPT, CitizenContext())
        assert "do NOT re-ask" not in result
        assert "Context Instructions" not in result

    def test_full_augmented_prompt_structure(self):
        ctx = CitizenContext(
            name="Jane Doe",
            address="123 Main St",
            notes=["Needs permit renewal"],
        )
        result = build_system_prompt(BASE_PROMPT, ctx)

        # Verify structural order: base prompt -> context block -> instructions
        base_idx = result.index(BASE_PROMPT)
        context_idx = result.index("Known citizen context:")
        instructions_idx = result.index("Context Instructions")

        assert base_idx < context_idx < instructions_idx


class TestLoadCitizenContext:
    def test_stub_returns_empty_context(self):
        """Until Issue #4 lands, load_citizen_context returns empty context."""
        ctx = load_citizen_context(session_id="sess-123", user_id="user-456")
        assert isinstance(ctx, CitizenContext)
        assert ctx.is_empty() is True
