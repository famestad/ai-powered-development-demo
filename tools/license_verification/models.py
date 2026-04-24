"""Pydantic models for contractor license verification."""

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class LicenseStatus(str, Enum):
    """Possible statuses for a contractor license."""

    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class ViolationSeverity(str, Enum):
    """Severity levels for license violations."""

    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"


class Violation(BaseModel):
    """A single violation on a contractor license record."""

    description: str = Field(
        description="Short description of the violation."
    )
    severity: ViolationSeverity = Field(
        description="Severity level of the violation."
    )
    date: date = Field(
        description="Date the violation was recorded."
    )


class License(BaseModel):
    """A contractor license record returned by the verification tool."""

    license_number: str = Field(
        description="The unique license identifier."
    )
    holder_name: str = Field(
        description="Name of the licensed contractor or business."
    )
    license_type: str = Field(
        description="Type of contractor license (e.g., General, Electrical, Plumbing)."
    )
    status: LicenseStatus = Field(
        description="Current status of the license."
    )
    expiration_date: date = Field(
        description="Date the license expires or expired."
    )
    violations: list[Violation] = Field(
        default_factory=list,
        description="List of violations on record for this license.",
    )
