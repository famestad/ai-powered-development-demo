# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Core data models for the AAMVA license parser."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class OcrBlock(BaseModel):
    """A single text block returned by an OCR engine."""

    text: str = Field(description="Recognised text content.")
    confidence: float = Field(
        ge=0.0, le=1.0, description="OCR engine confidence (0–1)."
    )
    x: float = Field(description="Left edge of the bounding box (normalised 0–1).")
    y: float = Field(description="Top edge of the bounding box (normalised 0–1).")
    width: float = Field(description="Width of the bounding box (normalised 0–1).")
    height: float = Field(description="Height of the bounding box (normalised 0–1).")


class FieldName(str, Enum):
    """AAMVA standard field names found on a driver-license front."""

    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    DATE_OF_BIRTH = "date_of_birth"
    EXPIRATION_DATE = "expiration_date"
    ISSUE_DATE = "issue_date"
    DL_NUMBER = "dl_number"
    ADDRESS = "address"
    CITY = "city"
    STATE = "state"
    ZIP_CODE = "zip_code"
    SEX = "sex"
    HEIGHT = "height"
    WEIGHT = "weight"
    EYE_COLOR = "eye_color"
    CLASS = "class"
    ENDORSEMENTS = "endorsements"
    RESTRICTIONS = "restrictions"


class MatchType(str, Enum):
    """How the field value was matched to its label."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    POSITIONAL = "positional"


class ExtractedField(BaseModel):
    """A single parsed field with its value and confidence metadata."""

    field_name: FieldName
    value: str | None = Field(
        default=None, description="Extracted value, or None if missing."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Combined confidence score for this field (0–1).",
    )
    match_type: MatchType | None = Field(
        default=None,
        description="How the value was located (None when the field is missing).",
    )
    source_block_indices: list[int] = Field(
        default_factory=list,
        description="Indices into the original OcrBlock list that contributed to this field.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-fatal issues encountered during extraction.",
    )


class LicenseRecord(BaseModel):
    """Complete extraction result for a single driver-license front."""

    fields: dict[FieldName, ExtractedField] = Field(
        description="Per-field extraction results keyed by AAMVA field name."
    )
    overall_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Aggregate confidence across all fields.",
    )
    state_profile_used: str = Field(
        description="Name of the StateProfile applied during parsing."
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Record-level warnings (e.g. many missing fields).",
    )
