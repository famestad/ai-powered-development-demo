# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Citizen memory module for extracting and managing structured context
from citizen conversations. Provides entity extraction from natural language
using both regex patterns and LLM-based structured output.
"""

from citizen_memory.extraction import (
    extract_entities,
    extract_entities_with_regex,
    merge_context,
)
from citizen_memory.models import Address, CitizenContext

__all__ = [
    "Address",
    "CitizenContext",
    "extract_entities",
    "extract_entities_with_regex",
    "merge_context",
]
