"""Unit tests for CitizenContext, generate_session_summary(), and MemoryLogger."""

import json
import logging
import sys
from pathlib import Path

import pytest

# Add the strands-single-agent pattern directory to the path so we can import
# citizen_context without installing it as a package.
_pattern_dir = str(
    Path(__file__).resolve().parent.parent.parent
    / "patterns"
    / "strands-single-agent"
)
if _pattern_dir not in sys.path:
    sys.path.insert(0, _pattern_dir)

from citizen_context import (  # noqa: E402
    CitizenContext,
    MemoryLogger,
    generate_session_summary,
)


# ---------------------------------------------------------------------------
# CitizenContext data model tests
# ---------------------------------------------------------------------------


class TestCitizenContext:
    """Tests for the CitizenContext dataclass."""

    def test_minimal_construction(self) -> None:
        """CitizenContext can be created with only required fields."""
        ctx = CitizenContext(session_id="sess-1", actor_id="user-1")
        assert ctx.session_id == "sess-1"
        assert ctx.actor_id == "user-1"
        assert ctx.citizen_name is None
        assert ctx.case_number is None
        assert ctx.conversation_topics == []

    def test_full_construction(self) -> None:
        """CitizenContext populates all optional fields when provided."""
        ctx = CitizenContext(
            session_id="sess-2",
            actor_id="user-2",
            citizen_name="John Doe",
            case_number="CR-2024-456",
            address="123 Oak St",
            issue_type="permit",
            issue_description="Needs a building permit renewal",
            conversation_topics=["permit renewal", "inspection scheduling"],
            additional_details={"priority": "high"},
        )
        assert ctx.citizen_name == "John Doe"
        assert ctx.case_number == "CR-2024-456"
        assert ctx.address == "123 Oak St"
        assert ctx.issue_type == "permit"
        assert ctx.issue_description == "Needs a building permit renewal"
        assert ctx.conversation_topics == [
            "permit renewal",
            "inspection scheduling",
        ]
        assert ctx.additional_details == {"priority": "high"}

    def test_to_dict_round_trip(self) -> None:
        """to_dict() produces a serializable dictionary with all fields."""
        ctx = CitizenContext(
            session_id="sess-3",
            actor_id="user-3",
            citizen_name="Jane Smith",
            case_number="CR-2024-789",
        )
        result = ctx.to_dict()
        assert isinstance(result, dict)
        assert result["session_id"] == "sess-3"
        assert result["citizen_name"] == "Jane Smith"
        assert result["case_number"] == "CR-2024-789"
        # Verify JSON-serializable
        serialized = json.dumps(result)
        assert isinstance(serialized, str)

    def test_timestamps_auto_populated(self) -> None:
        """created_at and updated_at are automatically set to ISO 8601."""
        ctx = CitizenContext(session_id="sess-4", actor_id="user-4")
        assert ctx.created_at is not None
        assert ctx.updated_at is not None
        # ISO 8601 timestamps contain 'T' as the date-time separator
        assert "T" in ctx.created_at
        assert "T" in ctx.updated_at


# ---------------------------------------------------------------------------
# generate_session_summary() tests
# ---------------------------------------------------------------------------


class TestGenerateSessionSummary:
    """Tests for the generate_session_summary() function."""

    def test_full_summary_matches_example_format(self) -> None:
        """Summary with all fields matches the expected handoff format."""
        ctx = CitizenContext(
            session_id="sess-100",
            actor_id="user-100",
            citizen_name="John Doe",
            case_number="CR-2024-456",
            address="123 Oak St",
            issue_type="permit",
            issue_description="Needs a building permit renewal",
            conversation_topics=["permit renewal", "inspection scheduling"],
        )
        summary = generate_session_summary(context=ctx)

        # Verify the header line matches the example format
        assert summary.startswith(
            "Citizen John Doe called about case #CR-2024-456 "
            "at 123 Oak St regarding a permit issue."
        )
        assert "Issue: Needs a building permit renewal" in summary
        assert "Topics discussed: permit renewal, inspection scheduling" in summary
        assert "Session ID: sess-100" in summary

    def test_minimal_summary(self) -> None:
        """Summary with only required fields still produces valid output."""
        ctx = CitizenContext(session_id="sess-101", actor_id="user-101")
        summary = generate_session_summary(context=ctx)

        assert summary.startswith("An unidentified citizen called.")
        assert "Session ID: sess-101" in summary

    def test_summary_with_name_only(self) -> None:
        """Summary includes citizen name when available, without case number."""
        ctx = CitizenContext(
            session_id="sess-102",
            actor_id="user-102",
            citizen_name="Alice Johnson",
        )
        summary = generate_session_summary(context=ctx)
        assert "Citizen Alice Johnson called." in summary

    def test_summary_with_case_number_only(self) -> None:
        """Summary includes case number when name is not available."""
        ctx = CitizenContext(
            session_id="sess-103",
            actor_id="user-103",
            case_number="CR-2024-001",
        )
        summary = generate_session_summary(context=ctx)
        assert "An unidentified citizen called about case #CR-2024-001." in summary

    def test_summary_with_additional_details(self) -> None:
        """Summary includes additional details section when provided."""
        ctx = CitizenContext(
            session_id="sess-104",
            actor_id="user-104",
            citizen_name="Bob Smith",
            additional_details={"priority": "urgent", "language": "Spanish"},
        )
        summary = generate_session_summary(context=ctx)
        assert "Additional details:" in summary
        assert "priority: urgent" in summary
        assert "language: Spanish" in summary

    def test_summary_with_address_and_issue_type(self) -> None:
        """Summary correctly combines address and issue type."""
        ctx = CitizenContext(
            session_id="sess-105",
            actor_id="user-105",
            citizen_name="Carol Davis",
            address="456 Elm Ave",
            issue_type="zoning",
        )
        summary = generate_session_summary(context=ctx)
        assert "at 456 Elm Ave" in summary
        assert "regarding a zoning issue" in summary

    def test_summary_includes_session_timestamp(self) -> None:
        """Summary always includes session start time."""
        ctx = CitizenContext(
            session_id="sess-106",
            actor_id="user-106",
            created_at="2024-12-01T10:30:00+00:00",
        )
        summary = generate_session_summary(context=ctx)
        assert "Session started: 2024-12-01T10:30:00+00:00" in summary


# ---------------------------------------------------------------------------
# MemoryLogger tests
# ---------------------------------------------------------------------------


class TestMemoryLogger:
    """Tests for the MemoryLogger structured logging class."""

    def test_log_context_created_emits_json(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_context_created() emits a valid JSON log entry."""
        ctx = CitizenContext(
            session_id="sess-200",
            actor_id="user-200",
            citizen_name="Test User",
            case_number="CR-TEST-001",
            issue_type="permit",
        )
        mem_logger = MemoryLogger(session_id="sess-200", actor_id="user-200")

        with caplog.at_level(logging.INFO):
            mem_logger.log_context_created(context=ctx)

        assert len(caplog.records) == 1
        log_data = json.loads(caplog.records[0].message)
        assert log_data["event"] == "memory_operation"
        assert log_data["operation"] == "context_created"
        assert log_data["session_id"] == "sess-200"
        assert log_data["actor_id"] == "user-200"
        assert log_data["data"]["citizen_name"] == "Test User"
        assert log_data["data"]["case_number"] == "CR-TEST-001"
        assert "timestamp" in log_data

    def test_log_context_updated_emits_json(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_context_updated() captures old and new values."""
        mem_logger = MemoryLogger(session_id="sess-201", actor_id="user-201")

        with caplog.at_level(logging.INFO):
            mem_logger.log_context_updated(
                field_name="citizen_name",
                old_value=None,
                new_value="Jane Doe",
            )

        log_data = json.loads(caplog.records[0].message)
        assert log_data["operation"] == "context_updated"
        assert log_data["data"]["field"] == "citizen_name"
        assert log_data["data"]["old_value"] is None
        assert log_data["data"]["new_value"] == "Jane Doe"

    def test_log_topic_added_emits_json(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_topic_added() captures the topic string."""
        mem_logger = MemoryLogger(session_id="sess-202", actor_id="user-202")

        with caplog.at_level(logging.INFO):
            mem_logger.log_topic_added(topic="permit inquiry")

        log_data = json.loads(caplog.records[0].message)
        assert log_data["operation"] == "topic_added"
        assert log_data["data"]["topic"] == "permit inquiry"

    def test_log_summary_generated_emits_json(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_summary_generated() captures summary length."""
        mem_logger = MemoryLogger(session_id="sess-203", actor_id="user-203")

        with caplog.at_level(logging.INFO):
            mem_logger.log_summary_generated(summary="A test summary string.")

        log_data = json.loads(caplog.records[0].message)
        assert log_data["operation"] == "summary_generated"
        assert log_data["data"]["summary_length"] == len("A test summary string.")

    def test_log_context_retrieved_emits_json(self, caplog: pytest.LogCaptureFixture) -> None:
        """log_context_retrieved() emits a diagnostics-purpose entry."""
        mem_logger = MemoryLogger(session_id="sess-204", actor_id="user-204")

        with caplog.at_level(logging.INFO):
            mem_logger.log_context_retrieved()

        log_data = json.loads(caplog.records[0].message)
        assert log_data["operation"] == "context_retrieved"
        assert log_data["data"]["purpose"] == "diagnostics"

    def test_all_log_entries_are_valid_json(self, caplog: pytest.LogCaptureFixture) -> None:
        """Every log method produces a parseable JSON string."""
        ctx = CitizenContext(session_id="sess-205", actor_id="user-205")
        mem_logger = MemoryLogger(session_id="sess-205", actor_id="user-205")

        with caplog.at_level(logging.INFO):
            mem_logger.log_context_created(context=ctx)
            mem_logger.log_context_updated(
                field_name="issue_type",
                old_value=None,
                new_value="zoning",
            )
            mem_logger.log_topic_added(topic="zoning variance")
            mem_logger.log_summary_generated(summary="test")
            mem_logger.log_context_retrieved()

        assert len(caplog.records) == 5
        for record in caplog.records:
            parsed = json.loads(record.message)
            assert "event" in parsed
            assert "operation" in parsed
            assert "session_id" in parsed
            assert "timestamp" in parsed
