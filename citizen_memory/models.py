# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Pydantic models for citizen session context.

Defines the structured schema for citizen-provided details extracted
during conversations. These models represent the target output of the
entity extraction pipeline and are used to accumulate context across
multiple conversation turns.

This module satisfies the CitizenContext schema requirement from Issue #4.
"""

from typing import Optional

from pydantic import BaseModel, Field


class Address(BaseModel):
    """Structured address extracted from citizen conversation.

    Attributes:
        street: Street address line (e.g. "123 Main St").
        city: City name (e.g. "Springfield").
        zip_code: ZIP or postal code (e.g. "62704").
    """

    street: Optional[str] = Field(
        default=None,
        description="Street address line, e.g. '123 Main St'",
    )
    city: Optional[str] = Field(
        default=None,
        description="City name, e.g. 'Springfield'",
    )
    zip_code: Optional[str] = Field(
        default=None,
        description="ZIP or postal code, e.g. '62704'",
    )


class CitizenContext(BaseModel):
    """Accumulated context about a citizen across conversation turns.

    Each field is Optional because any given conversation turn may only
    mention a subset of these details. Partial updates are merged into
    the running context so that later values overwrite earlier ones
    (supporting corrections).

    Attributes:
        citizen_name: Full name of the citizen (e.g. "Jane Doe").
        address: Structured address with street, city, and zip_code.
        case_number: Case/reference number (e.g. "CR-2024-0456").
        reference_number: Alternate reference identifier.
        account_number: Account or utility number.
        service_type: Type of municipal service (e.g. "water", "building permit").
    """

    citizen_name: Optional[str] = Field(
        default=None,
        description="Full name of the citizen, e.g. 'Jane Doe'",
    )
    address: Optional[Address] = Field(
        default=None,
        description="Structured address with street, city, and zip_code",
    )
    case_number: Optional[str] = Field(
        default=None,
        description="Case or reference number, e.g. 'CR-2024-0456'",
    )
    reference_number: Optional[str] = Field(
        default=None,
        description="Alternate reference identifier",
    )
    account_number: Optional[str] = Field(
        default=None,
        description="Account or utility number",
    )
    service_type: Optional[str] = Field(
        default=None,
        description="Type of municipal service, e.g. 'water', 'building permit'",
    )
