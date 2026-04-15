"""Tests for CitizenContext schema and prompt formatting."""

import sys
from pathlib import Path

# Add patterns directory to the path so we can import utils modules
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "patterns"))

from utils.citizen_context import CitizenContext


class TestCitizenContextIsEmpty:
    def test_default_is_empty(self):
        ctx = CitizenContext()
        assert ctx.is_empty() is True

    def test_not_empty_with_name(self):
        ctx = CitizenContext(name="Jane Doe")
        assert ctx.is_empty() is False

    def test_not_empty_with_notes(self):
        ctx = CitizenContext(notes=["Called about permit"])
        assert ctx.is_empty() is False

    def test_empty_with_empty_notes(self):
        ctx = CitizenContext(notes=[])
        assert ctx.is_empty() is True

    def test_not_empty_with_any_field(self):
        for field_name in [
            "name",
            "address",
            "case_number",
            "phone",
            "email",
            "date_of_birth",
            "service_type",
        ]:
            ctx = CitizenContext(**{field_name: "test_value"})
            assert ctx.is_empty() is False, f"Expected non-empty for field {field_name}"


class TestCitizenContextToPromptBlock:
    def test_empty_context_returns_empty_string(self):
        ctx = CitizenContext()
        assert ctx.to_prompt_block() == ""

    def test_single_field(self):
        ctx = CitizenContext(name="Jane Doe")
        block = ctx.to_prompt_block()
        assert "Known citizen context:" in block
        assert "Name: Jane Doe" in block

    def test_multiple_fields(self):
        ctx = CitizenContext(
            name="Jane Doe",
            address="123 Main St",
            case_number="CASE-2026-001",
        )
        block = ctx.to_prompt_block()
        assert "Name: Jane Doe" in block
        assert "Address: 123 Main St" in block
        assert "Case #: CASE-2026-001" in block

    def test_notes_included(self):
        ctx = CitizenContext(
            name="Jane Doe",
            notes=["Called about building permit", "Prefers email contact"],
        )
        block = ctx.to_prompt_block()
        assert "Notes:" in block
        assert "- Called about building permit" in block
        assert "- Prefers email contact" in block

    def test_all_fields(self):
        ctx = CitizenContext(
            name="Jane Doe",
            address="123 Main St",
            case_number="CASE-2026-001",
            phone="555-0123",
            email="jane@example.com",
            date_of_birth="1990-01-15",
            service_type="Building Permit",
            notes=["Urgent"],
        )
        block = ctx.to_prompt_block()
        assert "Name: Jane Doe" in block
        assert "Address: 123 Main St" in block
        assert "Case #: CASE-2026-001" in block
        assert "Phone: 555-0123" in block
        assert "Email: jane@example.com" in block
        assert "Date of Birth: 1990-01-15" in block
        assert "Service Type: Building Permit" in block
        assert "- Urgent" in block

    def test_omits_none_fields(self):
        ctx = CitizenContext(name="Jane Doe")
        block = ctx.to_prompt_block()
        assert "Address:" not in block
        assert "Phone:" not in block
        assert "Email:" not in block
