# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""State-specific profiles for AAMVA licence parsing.

Each profile is pure data — adding a new state requires no parser code changes.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from tools.license_parser.models import FieldName


class FieldRule(BaseModel):
    """Declarative rule that tells the parser how to locate one field."""

    labels: list[str] = Field(
        description="Label strings to look for (case-insensitive)."
    )
    pattern: str | None = Field(
        default=None,
        description="Regex that the extracted value must match for format validation.",
    )
    date_format: str | None = Field(
        default=None,
        description="strptime format string if this field is a date.",
    )

    def compiled_pattern(self) -> re.Pattern[str] | None:
        if self.pattern is None:
            return None
        return re.compile(self.pattern, re.IGNORECASE)


class StateProfile(BaseModel):
    """All state-specific parsing rules for a single jurisdiction."""

    name: str = Field(description="Human-readable profile name (e.g. 'California').")
    state_code: str = Field(description="Two-letter state abbreviation.")
    field_rules: dict[FieldName, FieldRule] = Field(
        description="Per-field extraction rules."
    )
    dl_number_pattern: str = Field(
        description="Regex for the state's DL number format."
    )


# ---------------------------------------------------------------------------
# Profile registry
# ---------------------------------------------------------------------------
_REGISTRY: dict[str, StateProfile] = {}


def register_profile(profile: StateProfile) -> None:
    """Register a state profile (keyed by upper-cased state_code)."""
    _REGISTRY[profile.state_code.upper()] = profile


def get_profile(state_code: str | None) -> StateProfile:
    """Return the profile for *state_code*, falling back to the default."""
    if state_code is not None:
        profile = _REGISTRY.get(state_code.upper())
        if profile is not None:
            return profile
    return _REGISTRY["DEFAULT"]


def list_profiles() -> list[str]:
    """Return registered state codes."""
    return sorted(_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Common field rules shared by most states
# ---------------------------------------------------------------------------
_COMMON_RULES: dict[FieldName, FieldRule] = {
    FieldName.FIRST_NAME: FieldRule(
        labels=["FN", "FIRST NAME", "FIRST", "GIVEN NAME"],
        pattern=r"^[A-Z][A-Za-z\s\-']+$",
    ),
    FieldName.LAST_NAME: FieldRule(
        labels=["LN", "LAST NAME", "LAST", "FAMILY NAME", "SURNAME"],
        pattern=r"^[A-Z][A-Za-z\s\-']+$",
    ),
    FieldName.DATE_OF_BIRTH: FieldRule(
        labels=["DOB", "DATE OF BIRTH", "BIRTH DATE"],
        pattern=r"^\d{2}[/\-]\d{2}[/\-]\d{4}$",
        date_format="%m/%d/%Y",
    ),
    FieldName.EXPIRATION_DATE: FieldRule(
        labels=["EXP", "EXPIRES", "EXPIRATION DATE", "EXPIRATION"],
        pattern=r"^\d{2}[/\-]\d{2}[/\-]\d{4}$",
        date_format="%m/%d/%Y",
    ),
    FieldName.ISSUE_DATE: FieldRule(
        labels=["ISS", "ISSUED", "ISSUE DATE"],
        pattern=r"^\d{2}[/\-]\d{2}[/\-]\d{4}$",
        date_format="%m/%d/%Y",
    ),
    FieldName.DL_NUMBER: FieldRule(
        labels=["DL", "LIC NO", "LICENSE NUMBER", "DL NO", "DRIVER LICENSE"],
        pattern=r"^[A-Z0-9\-]+$",
    ),
    FieldName.ADDRESS: FieldRule(
        labels=["ADDR", "ADDRESS", "STREET"],
        pattern=r"^[A-Za-z0-9\s\.,#\-]+$",
    ),
    FieldName.CITY: FieldRule(
        labels=["CITY"],
        pattern=r"^[A-Za-z\s\-]+$",
    ),
    FieldName.STATE: FieldRule(
        labels=["STATE", "ST"],
        pattern=r"^[A-Z]{2}$",
    ),
    FieldName.ZIP_CODE: FieldRule(
        labels=["ZIP", "ZIP CODE", "POSTAL CODE"],
        pattern=r"^\d{5}(-\d{4})?$",
    ),
    FieldName.SEX: FieldRule(
        labels=["SEX", "GENDER"],
        pattern=r"^[MF]$",
    ),
    FieldName.HEIGHT: FieldRule(
        labels=["HGT", "HEIGHT", "HT"],
        pattern=r"^\d['\-]\d{2}\"?$|^\d{3}\s*(?:cm|in)?$",
    ),
    FieldName.WEIGHT: FieldRule(
        labels=["WGT", "WEIGHT", "WT"],
        pattern=r"^\d{2,3}\s*(?:lbs?|kg)?$",
    ),
    FieldName.EYE_COLOR: FieldRule(
        labels=["EYES", "EYE COLOR", "EYE CLR"],
        pattern=r"^[A-Z]{2,5}$",
    ),
    FieldName.CLASS: FieldRule(
        labels=["CLASS", "DL CLASS", "LICENSE CLASS"],
        pattern=r"^[A-Z0-9]+$",
    ),
    FieldName.ENDORSEMENTS: FieldRule(
        labels=["END", "ENDORSEMENTS", "ENDORSE"],
        pattern=r"^[A-Z0-9\s,]+$|^NONE$",
    ),
    FieldName.RESTRICTIONS: FieldRule(
        labels=["REST", "RESTRICTIONS", "RSTR"],
        pattern=r"^[A-Z0-9\s,]+$|^NONE$",
    ),
}


def _build_rules(
    overrides: dict[FieldName, FieldRule] | None = None,
) -> dict[FieldName, FieldRule]:
    rules = dict(_COMMON_RULES)
    if overrides:
        rules.update(overrides)
    return rules


# ---------------------------------------------------------------------------
# Default (generic) profile
# ---------------------------------------------------------------------------
register_profile(
    StateProfile(
        name="Default (Generic)",
        state_code="DEFAULT",
        field_rules=_build_rules(),
        dl_number_pattern=r"^[A-Z0-9\-]{4,20}$",
    )
)

# ---------------------------------------------------------------------------
# California
# ---------------------------------------------------------------------------
register_profile(
    StateProfile(
        name="California",
        state_code="CA",
        field_rules=_build_rules(
            {
                FieldName.DL_NUMBER: FieldRule(
                    labels=["DL", "LIC NO", "DRIVER LICENSE"],
                    pattern=r"^[A-Z]\d{7}$",
                ),
            }
        ),
        dl_number_pattern=r"^[A-Z]\d{7}$",
    )
)

# ---------------------------------------------------------------------------
# Texas
# ---------------------------------------------------------------------------
register_profile(
    StateProfile(
        name="Texas",
        state_code="TX",
        field_rules=_build_rules(
            {
                FieldName.DL_NUMBER: FieldRule(
                    labels=["DL", "LIC NO", "DRIVER LICENSE"],
                    pattern=r"^\d{8}$",
                ),
            }
        ),
        dl_number_pattern=r"^\d{8}$",
    )
)

# ---------------------------------------------------------------------------
# New York
# ---------------------------------------------------------------------------
register_profile(
    StateProfile(
        name="New York",
        state_code="NY",
        field_rules=_build_rules(
            {
                FieldName.DL_NUMBER: FieldRule(
                    labels=["DL", "LIC NO", "DRIVER LICENSE", "CLIENT ID"],
                    pattern=r"^\d{9}$",
                ),
            }
        ),
        dl_number_pattern=r"^\d{9}$",
    )
)

# ---------------------------------------------------------------------------
# Florida
# ---------------------------------------------------------------------------
register_profile(
    StateProfile(
        name="Florida",
        state_code="FL",
        field_rules=_build_rules(
            {
                FieldName.DL_NUMBER: FieldRule(
                    labels=["DL", "LIC NO", "DRIVER LICENSE"],
                    pattern=r"^[A-Z]\d{12}$",
                ),
            }
        ),
        dl_number_pattern=r"^[A-Z]\d{12}$",
    )
)

# ---------------------------------------------------------------------------
# Washington
# ---------------------------------------------------------------------------
register_profile(
    StateProfile(
        name="Washington",
        state_code="WA",
        field_rules=_build_rules(
            {
                FieldName.DL_NUMBER: FieldRule(
                    labels=["DL", "LIC NO", "DRIVER LICENSE"],
                    pattern=r"^[A-Z*]{1,7}[A-Z0-9*]{5}$",
                ),
            }
        ),
        dl_number_pattern=r"^[A-Z*]{1,7}[A-Z0-9*]{5}$",
    )
)
