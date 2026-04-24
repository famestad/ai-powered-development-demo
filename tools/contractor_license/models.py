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


class Violation(BaseModel):
    """A single violation on a contractor's record."""

    date: date = Field(description="Date the violation was recorded.")
    type: str = Field(description="Category of the violation.")
    description: str = Field(description="Details of the violation.")
    resolution_status: str = Field(
        description="Current resolution state (e.g. resolved, pending, unresolved)."
    )


class License(BaseModel):
    """A contractor license issued by the City of Maplewood."""

    license_number: str = Field(description="Unique license identifier.")
    contractor_name: str = Field(description="Full name of the licensed contractor.")
    trade: str = Field(description="Trade category (e.g. electrical, plumbing).")
    status: LicenseStatus = Field(description="Current license status.")
    issue_date: date = Field(description="Date the license was originally issued.")
    expiration_date: date = Field(description="Date the license expires.")
    violations: list[Violation] = Field(
        default_factory=list,
        description="Violations on record for this license.",
    )
