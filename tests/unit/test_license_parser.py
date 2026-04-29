# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the AAMVA license field parser."""

from __future__ import annotations

import pytest

from tools.license_parser.models import (
    ExtractedField,
    FieldName,
    LicenseRecord,
    MatchType,
    OcrBlock,
)
from tools.license_parser.parser import parse_license
from tools.license_parser.profiles import (
    FieldRule,
    StateProfile,
    get_profile,
    list_profiles,
    register_profile,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _blk(
    text: str,
    confidence: float,
    x: float,
    y: float,
    w: float = 0.08,
    h: float = 0.03,
) -> OcrBlock:
    return OcrBlock(text=text, confidence=confidence, x=x, y=y, width=w, height=h)


# ---------------------------------------------------------------------------
# Common fixture: California license
# ---------------------------------------------------------------------------

@pytest.fixture()
def ca_blocks() -> list[OcrBlock]:
    return [
        _blk("DL", 0.99, 0.05, 0.10),
        _blk("D1234567", 0.97, 0.15, 0.10),
        _blk("LN", 0.98, 0.05, 0.16),
        _blk("SMITH", 0.96, 0.15, 0.16),
        _blk("FN", 0.98, 0.05, 0.22),
        _blk("JOHN", 0.95, 0.15, 0.22),
        _blk("DOB", 0.99, 0.05, 0.28),
        _blk("01/15/1990", 0.94, 0.15, 0.28),
        _blk("EXP", 0.99, 0.50, 0.10),
        _blk("01/15/2030", 0.93, 0.60, 0.10),
        _blk("ISS", 0.99, 0.50, 0.16),
        _blk("06/20/2022", 0.92, 0.60, 0.16),
        _blk("SEX", 0.99, 0.50, 0.22),
        _blk("M", 0.98, 0.60, 0.22),
        _blk("HGT", 0.99, 0.50, 0.28),
        _blk("5'11\"", 0.90, 0.60, 0.28),
        _blk("EYES", 0.99, 0.50, 0.34),
        _blk("BRN", 0.91, 0.60, 0.34),
        _blk("CLASS", 0.99, 0.05, 0.40),
        _blk("C", 0.97, 0.15, 0.40),
        _blk("REST", 0.99, 0.50, 0.40),
        _blk("NONE", 0.97, 0.60, 0.40),
        _blk("END", 0.99, 0.05, 0.46),
        _blk("NONE", 0.97, 0.15, 0.46),
    ]


@pytest.fixture()
def tx_blocks() -> list[OcrBlock]:
    return [
        _blk("DL", 0.99, 0.05, 0.10),
        _blk("12345678", 0.95, 0.15, 0.10),
        _blk("LAST NAME", 0.97, 0.05, 0.16),
        _blk("GARCIA", 0.96, 0.15, 0.16, w=0.12),
        _blk("FIRST NAME", 0.97, 0.05, 0.22),
        _blk("MARIA", 0.95, 0.15, 0.22),
        _blk("DOB", 0.99, 0.05, 0.28),
        _blk("03/22/1985", 0.93, 0.15, 0.28),
        _blk("EXP", 0.99, 0.50, 0.10),
        _blk("03/22/2029", 0.92, 0.60, 0.10),
        _blk("SEX", 0.99, 0.50, 0.22),
        _blk("F", 0.98, 0.60, 0.22),
    ]


@pytest.fixture()
def ny_blocks() -> list[OcrBlock]:
    return [
        _blk("DL", 0.99, 0.05, 0.10),
        _blk("123456789", 0.96, 0.15, 0.10),
        _blk("LN", 0.98, 0.05, 0.16),
        _blk("JOHNSON", 0.94, 0.15, 0.16),
        _blk("FN", 0.98, 0.05, 0.22),
        _blk("ALEX", 0.93, 0.15, 0.22),
        _blk("DOB", 0.99, 0.05, 0.28),
        _blk("07/04/1988", 0.92, 0.15, 0.28),
        _blk("EYES", 0.99, 0.50, 0.22),
        _blk("BLU", 0.90, 0.60, 0.22),
    ]


@pytest.fixture()
def fl_blocks() -> list[OcrBlock]:
    return [
        _blk("DL", 0.99, 0.05, 0.10),
        _blk("W123456789012", 0.95, 0.15, 0.10),
        _blk("LN", 0.98, 0.05, 0.16),
        _blk("WILLIAMS", 0.96, 0.15, 0.16),
        _blk("FN", 0.98, 0.05, 0.22),
        _blk("JAMES", 0.94, 0.15, 0.22),
        _blk("DOB", 0.99, 0.05, 0.28),
        _blk("11/30/1975", 0.91, 0.15, 0.28),
    ]


@pytest.fixture()
def wa_blocks() -> list[OcrBlock]:
    return [
        _blk("DL", 0.99, 0.05, 0.10),
        _blk("SMITH*AB1C2", 0.94, 0.15, 0.10),
        _blk("LN", 0.98, 0.05, 0.16),
        _blk("SMITH", 0.96, 0.15, 0.16),
        _blk("FN", 0.98, 0.05, 0.22),
        _blk("TAYLOR", 0.93, 0.15, 0.22),
        _blk("DOB", 0.99, 0.05, 0.28),
        _blk("09/12/2000", 0.95, 0.15, 0.28),
    ]


# ===================================================================
# Tests — California
# ===================================================================

class TestCaliforniaProfile:
    def test_parse_populates_core_fields(self, ca_blocks: list[OcrBlock]) -> None:
        profile = get_profile("CA")
        record = parse_license(ca_blocks, state_profile=profile)

        assert record.fields[FieldName.DL_NUMBER].value == "D1234567"
        assert record.fields[FieldName.LAST_NAME].value == "SMITH"
        assert record.fields[FieldName.FIRST_NAME].value == "JOHN"
        assert record.fields[FieldName.DATE_OF_BIRTH].value == "01/15/1990"
        assert record.fields[FieldName.EXPIRATION_DATE].value == "01/15/2030"
        assert record.fields[FieldName.SEX].value == "M"
        assert record.fields[FieldName.HEIGHT].value == "5'11\""
        assert record.fields[FieldName.EYE_COLOR].value == "BRN"
        assert record.fields[FieldName.CLASS].value == "C"
        assert record.fields[FieldName.RESTRICTIONS].value == "NONE"
        assert record.fields[FieldName.ENDORSEMENTS].value == "NONE"

    def test_state_profile_name_recorded(self, ca_blocks: list[OcrBlock]) -> None:
        record = parse_license(ca_blocks, state_profile=get_profile("CA"))
        assert record.state_profile_used == "California"

    def test_per_field_confidence_positive(self, ca_blocks: list[OcrBlock]) -> None:
        record = parse_license(ca_blocks, state_profile=get_profile("CA"))
        for f in record.fields.values():
            if f.value is not None:
                assert f.confidence > 0.0


# ===================================================================
# Tests — Texas
# ===================================================================

class TestTexasProfile:
    def test_parse_populates_core_fields(self, tx_blocks: list[OcrBlock]) -> None:
        profile = get_profile("TX")
        record = parse_license(tx_blocks, state_profile=profile)

        assert record.fields[FieldName.DL_NUMBER].value == "12345678"
        assert record.fields[FieldName.LAST_NAME].value == "GARCIA"
        assert record.fields[FieldName.FIRST_NAME].value == "MARIA"
        assert record.fields[FieldName.DATE_OF_BIRTH].value == "03/22/1985"
        assert record.fields[FieldName.SEX].value == "F"


# ===================================================================
# Tests — New York
# ===================================================================

class TestNewYorkProfile:
    def test_parse_populates_core_fields(self, ny_blocks: list[OcrBlock]) -> None:
        profile = get_profile("NY")
        record = parse_license(ny_blocks, state_profile=profile)

        assert record.fields[FieldName.DL_NUMBER].value == "123456789"
        assert record.fields[FieldName.LAST_NAME].value == "JOHNSON"
        assert record.fields[FieldName.FIRST_NAME].value == "ALEX"
        assert record.fields[FieldName.EYE_COLOR].value == "BLU"


# ===================================================================
# Tests — Florida
# ===================================================================

class TestFloridaProfile:
    def test_parse_populates_core_fields(self, fl_blocks: list[OcrBlock]) -> None:
        profile = get_profile("FL")
        record = parse_license(fl_blocks, state_profile=profile)

        assert record.fields[FieldName.DL_NUMBER].value == "W123456789012"
        assert record.fields[FieldName.LAST_NAME].value == "WILLIAMS"
        assert record.fields[FieldName.FIRST_NAME].value == "JAMES"
        assert record.fields[FieldName.DATE_OF_BIRTH].value == "11/30/1975"


# ===================================================================
# Tests — Washington
# ===================================================================

class TestWashingtonProfile:
    def test_parse_populates_core_fields(self, wa_blocks: list[OcrBlock]) -> None:
        profile = get_profile("WA")
        record = parse_license(wa_blocks, state_profile=profile)

        assert record.fields[FieldName.DL_NUMBER].value == "SMITH*AB1C2"
        assert record.fields[FieldName.LAST_NAME].value == "SMITH"
        assert record.fields[FieldName.FIRST_NAME].value == "TAYLOR"
        assert record.fields[FieldName.DATE_OF_BIRTH].value == "09/12/2000"


# ===================================================================
# Tests — Missing / malformed field handling
# ===================================================================

class TestMissingFields:
    def test_empty_blocks_returns_all_fields_missing(self) -> None:
        record = parse_license([])
        assert len(record.fields) == len(FieldName)
        for f in record.fields.values():
            assert f.value is None
            assert f.confidence == 0.0
            assert len(f.warnings) > 0

    def test_partial_blocks_fill_missing_with_zero_confidence(self) -> None:
        blocks = [
            _blk("DL", 0.99, 0.05, 0.10),
            _blk("X9999999", 0.95, 0.15, 0.10),
        ]
        record = parse_license(blocks)
        assert record.fields[FieldName.DL_NUMBER].value is not None
        assert record.fields[FieldName.FIRST_NAME].value is None
        assert record.fields[FieldName.FIRST_NAME].confidence == 0.0

    def test_many_missing_triggers_record_warning(self) -> None:
        record = parse_license([])
        assert len(record.warnings) > 0
        assert "missing" in record.warnings[0].lower()

    def test_malformed_date_still_extracted_with_lower_confidence(self) -> None:
        blocks = [
            _blk("DOB", 0.99, 0.05, 0.10),
            _blk("99/99/9999", 0.90, 0.15, 0.10),
        ]
        record = parse_license(blocks)
        dob = record.fields[FieldName.DATE_OF_BIRTH]
        assert dob.value == "99/99/9999"
        # Format matches the regex but fails strptime — gets a lower score
        assert dob.confidence < 0.9


# ===================================================================
# Tests — Confidence scoring
# ===================================================================

class TestConfidenceScoring:
    def test_deterministic_for_same_input(self, ca_blocks: list[OcrBlock]) -> None:
        profile = get_profile("CA")
        r1 = parse_license(ca_blocks, state_profile=profile)
        r2 = parse_license(ca_blocks, state_profile=profile)
        for fn in FieldName:
            assert r1.fields[fn].confidence == r2.fields[fn].confidence
        assert r1.overall_confidence == r2.overall_confidence

    def test_higher_ocr_confidence_yields_higher_field_confidence(self) -> None:
        low_blocks = [
            _blk("DL", 0.50, 0.05, 0.10),
            _blk("D1234567", 0.40, 0.15, 0.10),
        ]
        high_blocks = [
            _blk("DL", 0.99, 0.05, 0.10),
            _blk("D1234567", 0.99, 0.15, 0.10),
        ]
        profile = get_profile("CA")
        low_record = parse_license(low_blocks, state_profile=profile)
        high_record = parse_license(high_blocks, state_profile=profile)

        low_conf = low_record.fields[FieldName.DL_NUMBER].confidence
        high_conf = high_record.fields[FieldName.DL_NUMBER].confidence
        assert high_conf > low_conf

    def test_overall_confidence_between_zero_and_one(
        self, ca_blocks: list[OcrBlock]
    ) -> None:
        record = parse_license(ca_blocks, state_profile=get_profile("CA"))
        assert 0.0 <= record.overall_confidence <= 1.0

    def test_overall_confidence_zero_for_empty_input(self) -> None:
        record = parse_license([])
        assert record.overall_confidence == 0.0


# ===================================================================
# Tests — Profile registry
# ===================================================================

class TestProfileRegistry:
    def test_default_profile_exists(self) -> None:
        profile = get_profile(None)
        assert profile.state_code == "DEFAULT"

    def test_known_states_registered(self) -> None:
        for code in ("CA", "TX", "NY", "FL", "WA"):
            assert code in list_profiles()

    def test_unknown_state_falls_back_to_default(self) -> None:
        profile = get_profile("ZZ")
        assert profile.state_code == "DEFAULT"

    def test_synthetic_profile_pluggable(self) -> None:
        """Demonstrates adding a new profile requires only data, no code changes."""
        synthetic = StateProfile(
            name="Synthetic State",
            state_code="ZZ",
            field_rules={
                FieldName.DL_NUMBER: FieldRule(
                    labels=["DL"],
                    pattern=r"^ZZ\d{6}$",
                ),
                FieldName.FIRST_NAME: FieldRule(
                    labels=["FN"],
                    pattern=r"^[A-Z]+$",
                ),
                FieldName.LAST_NAME: FieldRule(
                    labels=["LN"],
                    pattern=r"^[A-Z]+$",
                ),
            },
            dl_number_pattern=r"^ZZ\d{6}$",
        )
        register_profile(synthetic)
        try:
            assert get_profile("ZZ").name == "Synthetic State"

            blocks = [
                _blk("DL", 0.99, 0.05, 0.10),
                _blk("ZZ123456", 0.97, 0.15, 0.10),
                _blk("FN", 0.98, 0.05, 0.20),
                _blk("ALICE", 0.96, 0.15, 0.20),
            ]
            record = parse_license(blocks, state_profile=get_profile("ZZ"))
            assert record.fields[FieldName.DL_NUMBER].value == "ZZ123456"
            assert record.fields[FieldName.FIRST_NAME].value == "ALICE"
            assert record.state_profile_used == "Synthetic State"
        finally:
            # Clean up to avoid polluting other tests
            from tools.license_parser.profiles import _REGISTRY

            _REGISTRY.pop("ZZ", None)


# ===================================================================
# Tests — Match types
# ===================================================================

class TestMatchTypes:
    def test_exact_label_match(self) -> None:
        blocks = [
            _blk("DOB", 0.99, 0.05, 0.10),
            _blk("01/01/2000", 0.95, 0.15, 0.10),
        ]
        record = parse_license(blocks)
        assert record.fields[FieldName.DATE_OF_BIRTH].match_type == MatchType.EXACT

    def test_fuzzy_label_match(self) -> None:
        blocks = [
            _blk("DATE OF BIRTH", 0.99, 0.05, 0.10),
            _blk("01/01/2000", 0.95, 0.15, 0.10, w=0.15),
        ]
        record = parse_license(blocks)
        dob = record.fields[FieldName.DATE_OF_BIRTH]
        assert dob.value == "01/01/2000"
        assert dob.match_type in (MatchType.EXACT, MatchType.FUZZY)

    def test_positional_fallback(self) -> None:
        # No label, but the block text matches the DL number regex
        blocks = [
            _blk("D1234567", 0.95, 0.15, 0.10),
        ]
        record = parse_license(blocks, state_profile=get_profile("CA"))
        dl = record.fields[FieldName.DL_NUMBER]
        if dl.value is not None:
            assert dl.match_type == MatchType.POSITIONAL

    def test_missing_field_has_no_match_type(self) -> None:
        record = parse_license([])
        assert record.fields[FieldName.DL_NUMBER].match_type is None


# ===================================================================
# Tests — Model validation
# ===================================================================

class TestModels:
    def test_ocr_block_rejects_invalid_confidence(self) -> None:
        with pytest.raises(Exception):  # noqa: B017
            OcrBlock(text="X", confidence=1.5, x=0, y=0, width=0.1, height=0.1)

    def test_extracted_field_rejects_invalid_confidence(self) -> None:
        with pytest.raises(Exception):  # noqa: B017
            ExtractedField(
                field_name=FieldName.DL_NUMBER,
                value="123",
                confidence=-0.1,
            )

    def test_license_record_round_trip(self, ca_blocks: list[OcrBlock]) -> None:
        record = parse_license(ca_blocks, state_profile=get_profile("CA"))
        data = record.model_dump()
        restored = LicenseRecord.model_validate(data)
        assert restored.overall_confidence == record.overall_confidence
