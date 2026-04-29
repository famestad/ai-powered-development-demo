# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""AAMVA driver-license field parser — maps OCR blocks to LicenseRecord."""

from tools.license_parser.models import (
    ExtractedField,
    FieldName,
    LicenseRecord,
    OcrBlock,
)
from tools.license_parser.parser import parse_license
from tools.license_parser.profiles import StateProfile, get_profile, register_profile

__all__ = [
    "ExtractedField",
    "FieldName",
    "LicenseRecord",
    "OcrBlock",
    "StateProfile",
    "get_profile",
    "parse_license",
    "register_profile",
]
