# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Rule-based parser that maps OCR blocks to a populated LicenseRecord."""

from __future__ import annotations

import re
from datetime import datetime

from tools.license_parser.models import (
    ExtractedField,
    FieldName,
    LicenseRecord,
    MatchType,
    OcrBlock,
)
from tools.license_parser.profiles import FieldRule, StateProfile, get_profile

# Proximity threshold: maximum normalised distance between a label block and
# its value block to be considered "nearby".
_PROXIMITY_THRESHOLD = 0.15

# Line-grouping tolerance: blocks whose *y* centres differ by less than this
# value are considered on the same line.
_LINE_Y_TOLERANCE = 0.025


# ---------------------------------------------------------------------------
# Confidence helpers
# ---------------------------------------------------------------------------

def _ocr_confidence_score(blocks: list[OcrBlock], indices: list[int]) -> float:
    """Average OCR confidence across the contributing blocks."""
    if not indices:
        return 0.0
    return sum(blocks[i].confidence for i in indices) / len(indices)


def _label_match_score(match_type: MatchType) -> float:
    """Score component based on how the label was matched."""
    return {
        MatchType.EXACT: 1.0,
        MatchType.FUZZY: 0.7,
        MatchType.POSITIONAL: 0.4,
    }[match_type]


def _format_validation_score(value: str, rule: FieldRule) -> float:
    """Score component based on whether the value passes format validation."""
    compiled = rule.compiled_pattern()
    if compiled is None:
        return 0.8
    if not compiled.match(value):
        return 0.3

    if rule.date_format:
        try:
            datetime.strptime(value.replace("-", "/"), rule.date_format)  # noqa: DTZ007
        except ValueError:
            return 0.5
    return 1.0


def _compute_field_confidence(
    blocks: list[OcrBlock],
    indices: list[int],
    match_type: MatchType,
    value: str,
    rule: FieldRule,
) -> float:
    ocr = _ocr_confidence_score(blocks, indices)
    label = _label_match_score(match_type)
    fmt = _format_validation_score(value, rule)
    return round(ocr * 0.4 + label * 0.3 + fmt * 0.3, 4)


def _aggregate_confidence(fields: dict[FieldName, ExtractedField]) -> float:
    """Weighted average: present fields count fully, missing fields pull score down."""
    total = 0.0
    count = len(FieldName)
    for field in fields.values():
        total += field.confidence
    if count == 0:
        return 0.0
    return round(total / count, 4)


# ---------------------------------------------------------------------------
# Block helpers
# ---------------------------------------------------------------------------

def _block_centre(block: OcrBlock) -> tuple[float, float]:
    return (block.x + block.width / 2, block.y + block.height / 2)


def _same_line(a: OcrBlock, b: OcrBlock) -> bool:
    _, ay = _block_centre(a)
    _, by = _block_centre(b)
    return abs(ay - by) < _LINE_Y_TOLERANCE


def _is_right_of(label_block: OcrBlock, candidate: OcrBlock) -> bool:
    return candidate.x > label_block.x + label_block.width - 0.01


def _distance(a: OcrBlock, b: OcrBlock) -> float:
    ax, ay = _block_centre(a)
    bx, by = _block_centre(b)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def _normalise(text: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", text.upper())


# ---------------------------------------------------------------------------
# Label matching
# ---------------------------------------------------------------------------

def _match_label(block_text: str, labels: list[str]) -> MatchType | None:
    """Check whether *block_text* matches any of the given labels."""
    normed = _normalise(block_text)
    for label in labels:
        normed_label = _normalise(label)
        if normed == normed_label:
            return MatchType.EXACT
    for label in labels:
        normed_label = _normalise(label)
        if normed_label in normed or normed in normed_label:
            if len(normed) >= 2:
                return MatchType.FUZZY
    return None


def _find_value_block(
    label_idx: int,
    blocks: list[OcrBlock],
    used: set[int],
) -> int | None:
    """Find the most likely value block for a label at *label_idx*.

    Strategy: prefer blocks to the right on the same line, then blocks
    directly below, within the proximity threshold.
    """
    label_block = blocks[label_idx]

    # Same-line candidates to the right
    same_line_right: list[tuple[float, int]] = []
    for i, blk in enumerate(blocks):
        if i == label_idx or i in used:
            continue
        if _same_line(label_block, blk) and _is_right_of(label_block, blk):
            same_line_right.append((blk.x, i))

    if same_line_right:
        same_line_right.sort()
        return same_line_right[0][1]

    # Below candidates (next line, nearby horizontally)
    below: list[tuple[float, int]] = []
    for i, blk in enumerate(blocks):
        if i == label_idx or i in used:
            continue
        dist = _distance(label_block, blk)
        if dist < _PROXIMITY_THRESHOLD and blk.y > label_block.y:
            below.append((dist, i))

    if below:
        below.sort()
        return below[0][1]

    return None


# ---------------------------------------------------------------------------
# Positional fallback
# ---------------------------------------------------------------------------

def _positional_search(
    field_name: FieldName,
    rule: FieldRule,
    blocks: list[OcrBlock],
    used: set[int],
) -> tuple[int, str] | None:
    """Try to locate a value purely by regex against unused blocks."""
    compiled = rule.compiled_pattern()
    if compiled is None:
        return None
    for i, blk in enumerate(blocks):
        if i in used:
            continue
        text = blk.text.strip()
        if compiled.match(text):
            return (i, text)
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_license(
    ocr_blocks: list[OcrBlock],
    state_profile: StateProfile | None = None,
) -> LicenseRecord:
    """Parse OCR blocks into a LicenseRecord.

    Parameters
    ----------
    ocr_blocks:
        Ordered list of OCR text blocks from the license image.
    state_profile:
        Optional state profile. When ``None`` the default (generic) profile is
        used.
    """
    profile = state_profile or get_profile(None)
    fields: dict[FieldName, ExtractedField] = {}
    used: set[int] = set()
    record_warnings: list[str] = []

    # Pass 1 — label-driven extraction
    for field_name, rule in profile.field_rules.items():
        for blk_idx, blk in enumerate(ocr_blocks):
            if blk_idx in used:
                continue
            match_type = _match_label(blk.text, rule.labels)
            if match_type is None:
                continue

            val_idx = _find_value_block(blk_idx, ocr_blocks, used)
            if val_idx is None:
                continue

            value = ocr_blocks[val_idx].text.strip()
            confidence = _compute_field_confidence(
                ocr_blocks, [val_idx], match_type, value, rule
            )
            fields[field_name] = ExtractedField(
                field_name=field_name,
                value=value,
                confidence=confidence,
                match_type=match_type,
                source_block_indices=[val_idx],
            )
            used.add(blk_idx)
            used.add(val_idx)
            break

    # Pass 2 — positional/regex fallback for fields still missing
    for field_name, rule in profile.field_rules.items():
        if field_name in fields:
            continue
        result = _positional_search(field_name, rule, ocr_blocks, used)
        if result is not None:
            idx, value = result
            confidence = _compute_field_confidence(
                ocr_blocks, [idx], MatchType.POSITIONAL, value, rule
            )
            fields[field_name] = ExtractedField(
                field_name=field_name,
                value=value,
                confidence=confidence,
                match_type=MatchType.POSITIONAL,
                source_block_indices=[idx],
            )
            used.add(idx)

    # Pass 3 — fill missing fields with explicit zero-confidence entries
    for field_name in FieldName:
        if field_name not in fields:
            fields[field_name] = ExtractedField(
                field_name=field_name,
                value=None,
                confidence=0.0,
                match_type=None,
                source_block_indices=[],
                warnings=[f"Field '{field_name.value}' not found in OCR blocks."],
            )

    missing_count = sum(1 for f in fields.values() if f.value is None)
    if missing_count > len(FieldName) // 2:
        record_warnings.append(
            f"{missing_count}/{len(FieldName)} fields missing — "
            "OCR quality or profile mismatch likely."
        )

    overall = _aggregate_confidence(fields)

    return LicenseRecord(
        fields=fields,
        overall_confidence=overall,
        state_profile_used=profile.name,
        warnings=record_warnings,
    )
