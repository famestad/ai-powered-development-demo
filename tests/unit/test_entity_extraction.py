# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for citizen entity extraction.

Tests the regex-based extraction pipeline and the merge/correction logic
without requiring an LLM or AWS credentials. LLM-based extraction is
tested via mocked Bedrock Converse responses.

Covers at least 10 sample conversation turns:
- Single entity extraction (name, address, case number, etc.)
- Multiple entities in one turn
- Corrections / overwrites of previously provided values
- Ambiguous and empty input
- Regex pattern matching for structured identifiers
- Merge logic for partial context updates
"""

from typing import Any
from unittest.mock import MagicMock, patch

from citizen_memory.extraction import (
    ACCOUNT_NUMBER_PATTERN,
    CASE_NUMBER_PATTERN,
    ZIP_CODE_PATTERN,
    _parse_tool_use_response,
    extract_entities,
    extract_entities_with_regex,
    merge_context,
)
from citizen_memory.models import Address, CitizenContext


# -----------------------------------------------------------------------
# Test 1: Single entity — citizen provides their name
# -----------------------------------------------------------------------
class TestRegexExtraction:
    """Tests for the regex-based extraction pass."""

    def test_case_number_extraction(self) -> None:
        """A turn containing a case number like CR-2024-0456 is extracted."""
        text = "I'm calling about case CR-2024-0456, can you check the status?"
        result = extract_entities_with_regex(text=text)
        assert result.case_number == "CR-2024-0456"
        # Other fields should be None since regex doesn't extract them
        assert result.citizen_name is None
        assert result.service_type is None

    def test_case_number_various_formats(self) -> None:
        """Case numbers with different prefix lengths are captured."""
        text = "Reference number is REF-2025-12345 for the complaint."
        result = extract_entities_with_regex(text=text)
        assert result.case_number == "REF-2025-12345"

    def test_case_number_lowercase(self) -> None:
        """Case numbers in lowercase text are captured and uppercased."""
        text = "my case number is cr-2023-001"
        result = extract_entities_with_regex(text=text)
        assert result.case_number == "CR-2023-001"

    def test_account_number_extraction(self) -> None:
        """Account numbers following the 'account' keyword are extracted."""
        text = "My account number is 12345678, can you look it up?"
        result = extract_entities_with_regex(text=text)
        assert result.account_number == "12345678"

    def test_account_number_with_hash(self) -> None:
        """Account number with # symbol is extracted."""
        text = "Account #98-765-432 needs to be updated."
        result = extract_entities_with_regex(text=text)
        assert result.account_number == "98-765-432"

    def test_zip_code_extraction(self) -> None:
        """A standalone 5-digit ZIP code is extracted into address.zip_code."""
        text = "I live in the 62704 area and need trash pickup."
        result = extract_entities_with_regex(text=text)
        assert result.address is not None
        assert result.address.zip_code == "62704"

    def test_zip_code_plus_four(self) -> None:
        """A ZIP+4 code is extracted correctly."""
        text = "My mailing ZIP is 90210-1234."
        result = extract_entities_with_regex(text=text)
        assert result.address is not None
        assert result.address.zip_code == "90210-1234"

    def test_no_entities_found(self) -> None:
        """A turn with no structured identifiers returns empty context."""
        text = "Hello, I need some help with a city service please."
        result = extract_entities_with_regex(text=text)
        assert result.case_number is None
        assert result.account_number is None
        assert result.address is None
        assert result.citizen_name is None

    def test_multiple_regex_entities(self) -> None:
        """A turn containing both a case number and ZIP code extracts both."""
        text = "Case CR-2024-0789 is about my property at ZIP 60601."
        result = extract_entities_with_regex(text=text)
        assert result.case_number == "CR-2024-0789"
        assert result.address is not None
        assert result.address.zip_code == "60601"

    def test_empty_string(self) -> None:
        """An empty string returns a fully empty context."""
        result = extract_entities_with_regex(text="")
        assert result.case_number is None
        assert result.account_number is None
        assert result.address is None


# -----------------------------------------------------------------------
# Test merge / correction logic
# -----------------------------------------------------------------------
class TestMergeContext:
    """Tests for the context merging and correction strategy."""

    def test_merge_new_field_into_empty(self) -> None:
        """Adding a name to an empty context works correctly."""
        existing = CitizenContext()
        update = CitizenContext(citizen_name="Jane Doe")
        merged = merge_context(existing=existing, update=update)
        assert merged.citizen_name == "Jane Doe"

    def test_merge_preserves_existing_fields(self) -> None:
        """Updating one field does not erase other existing fields."""
        existing = CitizenContext(
            citizen_name="Jane Doe",
            case_number="CR-2024-0001",
        )
        update = CitizenContext(service_type="water")
        merged = merge_context(existing=existing, update=update)
        assert merged.citizen_name == "Jane Doe"
        assert merged.case_number == "CR-2024-0001"
        assert merged.service_type == "water"

    def test_correction_overwrites_old_value(self) -> None:
        """If a citizen corrects their name, the new value overwrites the old."""
        existing = CitizenContext(citizen_name="Jane Doe")
        update = CitizenContext(citizen_name="Janet Doe")
        merged = merge_context(existing=existing, update=update)
        assert merged.citizen_name == "Janet Doe"

    def test_address_subfield_merge(self) -> None:
        """Updating just the ZIP code preserves the existing street."""
        existing = CitizenContext(
            address=Address(street="123 Main St", city="Springfield"),
        )
        update = CitizenContext(
            address=Address(zip_code="62704"),
        )
        merged = merge_context(existing=existing, update=update)
        assert merged.address is not None
        assert merged.address.street == "123 Main St"
        assert merged.address.city == "Springfield"
        assert merged.address.zip_code == "62704"

    def test_address_correction(self) -> None:
        """Correcting a street address preserves other address components."""
        existing = CitizenContext(
            address=Address(
                street="123 Main St",
                city="Springfield",
                zip_code="62704",
            ),
        )
        # Citizen corrects the street
        update = CitizenContext(
            address=Address(street="456 Oak Ave"),
        )
        merged = merge_context(existing=existing, update=update)
        assert merged.address is not None
        assert merged.address.street == "456 Oak Ave"
        assert merged.address.city == "Springfield"
        assert merged.address.zip_code == "62704"

    def test_merge_empty_update_changes_nothing(self) -> None:
        """An empty update leaves the existing context unchanged."""
        existing = CitizenContext(
            citizen_name="Jane Doe",
            case_number="CR-2024-0001",
            service_type="trash",
        )
        update = CitizenContext()
        merged = merge_context(existing=existing, update=update)
        assert merged.citizen_name == "Jane Doe"
        assert merged.case_number == "CR-2024-0001"
        assert merged.service_type == "trash"


# -----------------------------------------------------------------------
# Test _parse_tool_use_response (converting flat tool output to model)
# -----------------------------------------------------------------------
class TestParseToolUseResponse:
    """Tests for parsing the Bedrock Converse tool_use response."""

    def test_parse_full_response(self) -> None:
        """A tool response with all fields is parsed correctly."""
        tool_input: dict[str, Any] = {
            "citizen_name": "John Smith",
            "street": "789 Elm St",
            "city": "Oakville",
            "zip_code": "60601",
            "case_number": "CR-2025-0100",
            "account_number": "ACC-9999",
            "service_type": "building permit",
        }
        result = _parse_tool_use_response(tool_input=tool_input)
        assert result.citizen_name == "John Smith"
        assert result.address is not None
        assert result.address.street == "789 Elm St"
        assert result.address.city == "Oakville"
        assert result.address.zip_code == "60601"
        assert result.case_number == "CR-2025-0100"
        assert result.account_number == "ACC-9999"
        assert result.service_type == "building permit"

    def test_parse_partial_response(self) -> None:
        """A tool response with only some fields leaves others as None."""
        tool_input: dict[str, Any] = {
            "citizen_name": "Maria Garcia",
        }
        result = _parse_tool_use_response(tool_input=tool_input)
        assert result.citizen_name == "Maria Garcia"
        assert result.address is None
        assert result.case_number is None

    def test_parse_empty_response(self) -> None:
        """An empty tool response returns a fully empty context."""
        result = _parse_tool_use_response(tool_input={})
        assert result.citizen_name is None
        assert result.address is None
        assert result.case_number is None


# -----------------------------------------------------------------------
# Test extract_entities with LLM mocked
# -----------------------------------------------------------------------
class TestExtractEntitiesWithMockedLLM:
    """Tests for the combined extraction pipeline with mocked Bedrock calls."""

    def _mock_converse_response(self, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Build a mock Bedrock Converse response containing a tool_use block.

        Args:
            tool_input: The JSON payload the model would return as tool input.

        Returns:
            A dict shaped like a Bedrock Converse API response.
        """
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "mock-123",
                                "name": "extract_citizen_entities",
                                "input": tool_input,
                            }
                        }
                    ]
                }
            }
        }

    @patch("citizen_memory.extraction.boto3.client")
    def test_llm_extracts_name_and_service(self, mock_boto3_client: MagicMock) -> None:
        """Turn 1: 'My name is Jane Doe and I need help with water service.'"""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "citizen_name": "Jane Doe",
            "service_type": "water",
        })

        result = extract_entities(
            text="My name is Jane Doe and I need help with water service.",
            use_llm=True,
        )
        assert result.citizen_name == "Jane Doe"
        assert result.service_type == "water"

    @patch("citizen_memory.extraction.boto3.client")
    def test_llm_extracts_full_address(self, mock_boto3_client: MagicMock) -> None:
        """Turn 2: 'I live at 456 Oak Avenue, Springfield, 62704.'"""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "street": "456 Oak Avenue",
            "city": "Springfield",
            "zip_code": "62704",
        })

        result = extract_entities(
            text="I live at 456 Oak Avenue, Springfield, 62704.",
            use_llm=True,
        )
        assert result.address is not None
        assert result.address.street == "456 Oak Avenue"
        assert result.address.city == "Springfield"
        # Regex also finds 62704, which overlays the LLM result
        assert result.address.zip_code == "62704"

    @patch("citizen_memory.extraction.boto3.client")
    def test_llm_with_case_number_and_name(self, mock_boto3_client: MagicMock) -> None:
        """Turn 3: 'This is John Smith calling about CR-2024-0456.'"""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "citizen_name": "John Smith",
            "case_number": "CR-2024-0456",
        })

        result = extract_entities(
            text="This is John Smith calling about CR-2024-0456.",
            use_llm=True,
        )
        assert result.citizen_name == "John Smith"
        # Regex captures case number and overlays it
        assert result.case_number == "CR-2024-0456"

    @patch("citizen_memory.extraction.boto3.client")
    def test_llm_correction_scenario(self, mock_boto3_client: MagicMock) -> None:
        """Turn 4: Citizen corrects their name — new value should take effect."""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "citizen_name": "Janet Doe",
        })

        # Simulate existing context from previous turns
        existing = CitizenContext(
            citizen_name="Jane Doe",
            service_type="water",
        )

        # Extract from correction turn
        update = extract_entities(
            text="Actually, my name is Janet Doe, not Jane.",
            use_llm=True,
        )

        # Merge the correction
        merged = merge_context(existing=existing, update=update)
        assert merged.citizen_name == "Janet Doe"
        # Previous fields preserved
        assert merged.service_type == "water"

    @patch("citizen_memory.extraction.boto3.client")
    def test_llm_ambiguous_input(self, mock_boto3_client: MagicMock) -> None:
        """Turn 5: Ambiguous input — LLM returns empty, no regex matches."""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = self._mock_converse_response({})

        result = extract_entities(
            text="I'm not sure what I need, can you help me figure it out?",
            use_llm=True,
        )
        assert result.citizen_name is None
        assert result.case_number is None
        assert result.address is None
        assert result.service_type is None

    @patch("citizen_memory.extraction.boto3.client")
    def test_llm_multiple_entities(self, mock_boto3_client: MagicMock) -> None:
        """Turn 6: Multiple entities in a single turn."""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "citizen_name": "Maria Garcia",
            "street": "100 First Ave",
            "city": "Riverside",
            "zip_code": "92501",
            "service_type": "trash collection",
            "account_number": "55667788",
        })

        text = (
            "Hi, I'm Maria Garcia at 100 First Ave, Riverside 92501. "
            "Account number 55667788, I need trash collection resumed."
        )
        result = extract_entities(text=text, use_llm=True)

        assert result.citizen_name == "Maria Garcia"
        assert result.address is not None
        assert result.address.street == "100 First Ave"
        assert result.address.city == "Riverside"
        assert result.address.zip_code == "92501"
        assert result.service_type == "trash collection"
        # Regex captures account number and overlays it
        assert result.account_number == "55667788"

    @patch("citizen_memory.extraction.boto3.client")
    def test_llm_failure_falls_back_to_regex(
        self, mock_boto3_client: MagicMock
    ) -> None:
        """Turn 7: LLM call fails — regex results are used as fallback."""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        mock_bedrock.converse.side_effect = Exception("Bedrock unavailable")

        text = "My case is CR-2025-0101 and my ZIP is 30301."
        result = extract_entities(text=text, use_llm=True)

        # Regex still captures structured identifiers
        assert result.case_number == "CR-2025-0101"
        assert result.address is not None
        assert result.address.zip_code == "30301"
        # Name won't be extracted without LLM
        assert result.citizen_name is None

    def test_regex_only_mode(self) -> None:
        """Turn 8: use_llm=False skips LLM, uses only regex."""
        text = "Case REF-2025-00042, account #11-222-333, ZIP 55401."
        result = extract_entities(text=text, use_llm=False)

        assert result.case_number == "REF-2025-00042"
        assert result.account_number == "11-222-333"
        assert result.address is not None
        assert result.address.zip_code == "55401"
        # No LLM means no name or service type extraction
        assert result.citizen_name is None
        assert result.service_type is None

    @patch("citizen_memory.extraction.boto3.client")
    def test_regex_overrides_llm_for_case_number(
        self, mock_boto3_client: MagicMock
    ) -> None:
        """Turn 9: Regex result takes precedence over LLM for case numbers."""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        # LLM returns a slightly different case number format
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "case_number": "cr-2024-0456",  # lowercase from LLM
        })

        text = "My case is CR-2024-0456."
        result = extract_entities(text=text, use_llm=True)

        # Regex uppercases the case number, and it overrides the LLM result
        assert result.case_number == "CR-2024-0456"

    @patch("citizen_memory.extraction.boto3.client")
    def test_address_correction_across_turns(
        self, mock_boto3_client: MagicMock
    ) -> None:
        """Turn 10: Citizen corrects their street address across turns."""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock

        # Turn A: citizen gives initial address
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "street": "123 Wrong St",
            "city": "Springfield",
            "zip_code": "62704",
        })
        turn_a = extract_entities(
            text="I'm at 123 Wrong St, Springfield 62704.",
            use_llm=True,
        )
        existing = merge_context(existing=CitizenContext(), update=turn_a)

        # Turn B: citizen corrects the street
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "street": "456 Correct Ave",
        })
        turn_b = extract_entities(
            text="Sorry, I meant 456 Correct Ave, not 123 Wrong St.",
            use_llm=True,
        )
        final = merge_context(existing=existing, update=turn_b)

        assert final.address is not None
        assert final.address.street == "456 Correct Ave"
        # City and ZIP preserved from turn A
        assert final.address.city == "Springfield"
        assert final.address.zip_code == "62704"

    @patch("citizen_memory.extraction.boto3.client")
    def test_reference_number_extraction(
        self, mock_boto3_client: MagicMock
    ) -> None:
        """Turn 11: Citizen provides a reference number distinct from case number."""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "reference_number": "REF-ABC-001",
            "service_type": "building permit",
        })

        result = extract_entities(
            text="I have a reference REF-ABC-001 for my building permit application.",
            use_llm=True,
        )
        assert result.reference_number == "REF-ABC-001"
        assert result.service_type == "building permit"

    @patch("citizen_memory.extraction.boto3.client")
    def test_full_multi_turn_accumulation(
        self, mock_boto3_client: MagicMock
    ) -> None:
        """Turn 12: Simulate a 3-turn conversation accumulating context."""
        mock_bedrock = MagicMock()
        mock_boto3_client.return_value = mock_bedrock
        context = CitizenContext()

        # Turn 1: Citizen gives name
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "citizen_name": "Alex Rivera",
        })
        update = extract_entities(text="Hi, I'm Alex Rivera.", use_llm=True)
        context = merge_context(existing=context, update=update)

        # Turn 2: Citizen gives case number and service
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "case_number": "CR-2025-0200",
            "service_type": "pothole repair",
        })
        update = extract_entities(
            text="I filed CR-2025-0200 about pothole repair on my street.",
            use_llm=True,
        )
        context = merge_context(existing=context, update=update)

        # Turn 3: Citizen gives address
        mock_bedrock.converse.return_value = self._mock_converse_response({
            "street": "789 Pine Rd",
            "city": "Denver",
            "zip_code": "80202",
        })
        update = extract_entities(
            text="The pothole is near my home at 789 Pine Rd, Denver 80202.",
            use_llm=True,
        )
        context = merge_context(existing=context, update=update)

        # Verify all accumulated context
        assert context.citizen_name == "Alex Rivera"
        assert context.case_number == "CR-2025-0200"
        assert context.service_type == "pothole repair"
        assert context.address is not None
        assert context.address.street == "789 Pine Rd"
        assert context.address.city == "Denver"
        assert context.address.zip_code == "80202"


# -----------------------------------------------------------------------
# Regex pattern unit tests
# -----------------------------------------------------------------------
class TestRegexPatterns:
    """Direct tests for the compiled regex patterns."""

    def test_case_number_pattern_matches(self) -> None:
        """Verify the case number regex matches expected formats."""
        assert CASE_NUMBER_PATTERN.search("CR-2024-0456") is not None
        assert CASE_NUMBER_PATTERN.search("REF-2025-12345") is not None
        assert CASE_NUMBER_PATTERN.search("CASE-2023-001") is not None

    def test_case_number_pattern_rejects(self) -> None:
        """Verify the case number regex rejects non-matching strings."""
        assert CASE_NUMBER_PATTERN.search("C-2024-0456") is None  # prefix too short
        assert CASE_NUMBER_PATTERN.search("CR-24-0456") is None  # year too short
        assert CASE_NUMBER_PATTERN.search("random text") is None

    def test_account_number_pattern_matches(self) -> None:
        """Verify the account number regex matches expected formats."""
        assert ACCOUNT_NUMBER_PATTERN.search("account number 12345678") is not None
        assert ACCOUNT_NUMBER_PATTERN.search("Account #98-765-432") is not None
        assert ACCOUNT_NUMBER_PATTERN.search("account: 11223344") is not None

    def test_zip_code_pattern_matches(self) -> None:
        """Verify the ZIP code regex matches expected formats."""
        assert ZIP_CODE_PATTERN.search("62704") is not None
        assert ZIP_CODE_PATTERN.search("90210-1234") is not None


# -----------------------------------------------------------------------
# Model tests
# -----------------------------------------------------------------------
class TestCitizenContextModel:
    """Tests for the CitizenContext Pydantic model."""

    def test_default_all_none(self) -> None:
        """A default CitizenContext has all fields as None."""
        ctx = CitizenContext()
        assert ctx.citizen_name is None
        assert ctx.address is None
        assert ctx.case_number is None
        assert ctx.reference_number is None
        assert ctx.account_number is None
        assert ctx.service_type is None

    def test_model_dump_exclude_none(self) -> None:
        """model_dump with exclude_none omits None fields."""
        ctx = CitizenContext(citizen_name="Test User")
        dumped = ctx.model_dump(exclude_none=True)
        assert dumped == {"citizen_name": "Test User"}

    def test_address_model(self) -> None:
        """Address model stores street, city, and zip_code."""
        addr = Address(street="1 Main St", city="Anytown", zip_code="12345")
        assert addr.street == "1 Main St"
        assert addr.city == "Anytown"
        assert addr.zip_code == "12345"
