"""Integration tests for the conversation memory pipeline.

Verifies the full extract-merge-inject cycle across multiple conversation
turns, ensuring that entities provided in earlier turns are retained and
injected into later system prompts without re-asking.
"""

import sys
import os

# Add patterns/ to path so we can import the memory module
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "..", "..", "patterns")
)

from memory.schema import CitizenContext
from memory.extraction import extract_entities
from memory.injection import build_augmented_prompt
from memory.pipeline import MemoryPipeline


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestCitizenContext:
    def test_merge_preserves_existing_fields(self):
        ctx = CitizenContext(address="123 Main St")
        new = CitizenContext(case_number="CASE1234")
        ctx.merge(new)
        assert ctx.address == "123 Main St"
        assert ctx.case_number == "CASE1234"

    def test_merge_overwrites_with_new_value(self):
        ctx = CitizenContext(address="old address")
        new = CitizenContext(address="456 Oak Avenue")
        ctx.merge(new)
        assert ctx.address == "456 Oak Avenue"

    def test_merge_does_not_clear_with_none(self):
        ctx = CitizenContext(citizen_name="Jane Doe", address="123 Main St")
        new = CitizenContext()  # all None
        ctx.merge(new)
        assert ctx.citizen_name == "Jane Doe"
        assert ctx.address == "123 Main St"

    def test_round_trip_json(self):
        ctx = CitizenContext(
            citizen_name="John Smith",
            case_number="AB1234",
            additional_entities={"department": "Public Works"},
        )
        restored = CitizenContext.from_json(ctx.to_json())
        assert restored.citizen_name == "John Smith"
        assert restored.case_number == "AB1234"
        assert restored.additional_entities["department"] == "Public Works"

    def test_has_entities_empty(self):
        assert not CitizenContext().has_entities()

    def test_has_entities_with_data(self):
        assert CitizenContext(address="123 Main St").has_entities()

    def test_summary_lines(self):
        ctx = CitizenContext(citizen_name="Jane", case_number="XY9999")
        lines = ctx.summary_lines()
        assert len(lines) == 2
        assert "Name: Jane" in lines
        assert "Case number: XY9999" in lines


# ---------------------------------------------------------------------------
# Extraction tests
# ---------------------------------------------------------------------------

class TestExtraction:
    def test_extract_case_number(self):
        ctx = extract_entities("I'm calling about case #12345")
        assert ctx.case_number == "12345"

    def test_extract_case_number_with_prefix(self):
        ctx = extract_entities("My ticket number is REF5678")
        assert ctx.case_number == "REF5678"

    def test_extract_email_with_keyword(self):
        ctx = extract_entities("My email is jane@example.com")
        assert ctx.email == "jane@example.com"

    def test_extract_standalone_email(self):
        ctx = extract_entities("Please contact jane.doe@city.gov")
        assert ctx.email == "jane.doe@city.gov"

    def test_extract_phone(self):
        ctx = extract_entities("Call me at 555-123-4567")
        assert ctx.phone_number == "555-123-4567"

    def test_extract_name(self):
        ctx = extract_entities("My name is John Smith")
        assert ctx.citizen_name == "John Smith"

    def test_extract_address(self):
        ctx = extract_entities("I live at 742 Evergreen Street")
        assert ctx.address is not None
        assert "742 Evergreen Street" in ctx.address

    def test_no_entities(self):
        ctx = extract_entities("Hello, I need help with something")
        assert not ctx.has_entities()


# ---------------------------------------------------------------------------
# Injection tests
# ---------------------------------------------------------------------------

class TestInjection:
    def test_no_injection_when_empty(self):
        base = "You are a helpful assistant."
        result = build_augmented_prompt(base, CitizenContext())
        assert result == base

    def test_injection_adds_context_block(self):
        base = "You are a helpful assistant."
        ctx = CitizenContext(address="123 Main St", case_number="XY9999")
        result = build_augmented_prompt(base, ctx)
        assert "Citizen Context" in result
        assert "123 Main St" in result
        assert "XY9999" in result
        assert "Do NOT ask for any of this again" in result

    def test_base_prompt_preserved(self):
        base = "You are a helpful assistant."
        ctx = CitizenContext(citizen_name="Jane")
        result = build_augmented_prompt(base, ctx)
        assert result.startswith(base)


# ---------------------------------------------------------------------------
# Pipeline integration test — the acceptance scenario
# ---------------------------------------------------------------------------

class TestMemoryPipeline:
    """Multi-turn conversation test as specified in the acceptance criteria.

    Citizen provides address in turn 1, case number in turn 3,
    and agent correctly references both in turn 5 without re-asking.
    """

    def setup_method(self):
        self.user_id = "test-citizen-001"
        self.session_id = "test-session-001"
        MemoryPipeline.clear_session(self.user_id, self.session_id)
        self.pipeline = MemoryPipeline(self.user_id, self.session_id)
        self.base_prompt = (
            "You are a helpful assistant with access to tools via the Gateway "
            "and Code Interpreter."
        )

    def teardown_method(self):
        MemoryPipeline.clear_session(self.user_id, self.session_id)

    def test_turn_1_address_extracted(self):
        """Turn 1: citizen provides their address."""
        self.pipeline.process_message(
            "Hi, I live at 742 Evergreen Street and I need to report a pothole."
        )
        ctx = self.pipeline.get_context()
        assert ctx.address is not None
        assert "742 Evergreen Street" in ctx.address

    def test_turn_3_case_number_extracted(self):
        """Turn 3: citizen provides case number; address from turn 1 is retained."""
        # Turn 1
        self.pipeline.process_message(
            "Hi, I live at 742 Evergreen Street and I need to report a pothole."
        )
        # Turn 2 (agent response — no citizen message to process)
        # Turn 3
        self.pipeline.process_message(
            "My existing case number is #56789 for the same issue."
        )
        ctx = self.pipeline.get_context()
        assert ctx.address is not None
        assert "742 Evergreen Street" in ctx.address
        assert ctx.case_number == "56789"

    def test_turn_5_both_in_prompt(self):
        """Turn 5: both address and case number are injected into the prompt."""
        # Turn 1
        self.pipeline.process_message(
            "Hi, I live at 742 Evergreen Street and I need to report a pothole."
        )
        # Turn 3
        self.pipeline.process_message(
            "My existing case number is #56789 for the same issue."
        )
        # Turn 5
        self.pipeline.process_message(
            "Can you check the status of my report?"
        )

        augmented = self.pipeline.inject_context(self.base_prompt)

        # Both entities from earlier turns must be present in the prompt
        assert "742 Evergreen Street" in augmented
        assert "56789" in augmented
        assert "Do NOT ask for any of this again" in augmented
        # Base prompt still intact
        assert augmented.startswith(self.base_prompt)

    def test_full_multi_turn_with_name_and_email(self):
        """Extended scenario with name, address, case number, and email."""
        self.pipeline.process_message("My name is Maria Garcia")
        self.pipeline.process_message(
            "I live at 100 Oak Avenue and need help with a permit."
        )
        self.pipeline.process_message("Reference ticket REF0042")
        self.pipeline.process_message("email me at maria@example.com")

        ctx = self.pipeline.get_context()
        assert ctx.citizen_name == "Maria Garcia"
        assert ctx.address is not None
        assert "100 Oak Avenue" in ctx.address
        assert ctx.case_number == "REF0042"
        assert ctx.email == "maria@example.com"

        augmented = self.pipeline.inject_context(self.base_prompt)
        assert "Maria Garcia" in augmented
        assert "100 Oak Avenue" in augmented
        assert "REF0042" in augmented
        assert "maria@example.com" in augmented

    def test_separate_sessions_isolated(self):
        """Different sessions don't share context."""
        pipeline_a = MemoryPipeline("user-a", "session-a")
        pipeline_b = MemoryPipeline("user-b", "session-b")

        pipeline_a.process_message("My name is Alice")
        pipeline_b.process_message("My name is Bob")

        assert pipeline_a.get_context().citizen_name == "Alice"
        assert pipeline_b.get_context().citizen_name == "Bob"

        MemoryPipeline.clear_session("user-a", "session-a")
        MemoryPipeline.clear_session("user-b", "session-b")
