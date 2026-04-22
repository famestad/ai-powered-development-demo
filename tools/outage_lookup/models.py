"""Pydantic models for service outages."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ServiceType(str, Enum):
    """Types of municipal utility services."""

    WATER = "water"
    POWER = "power"
    GAS = "gas"
    INTERNET = "internet"


class OutageStatus(str, Enum):
    """Current status of an outage."""

    ACTIVE = "active"
    SCHEDULED = "scheduled"
    RESOLVED = "resolved"


class AdvisoryType(str, Enum):
    """Public health advisory associated with an outage."""

    NONE = "none"
    BOIL_WATER = "boil_water"
    DO_NOT_DRINK = "do_not_drink"


class Outage(BaseModel):
    """A single service outage record."""

    id: str = Field(description="Unique outage identifier.")
    service_type: ServiceType
    status: OutageStatus
    affected_area: str = Field(
        description="Neighbourhood or district affected by the outage."
    )
    start_time: datetime
    estimated_restoration: datetime | None = Field(
        default=None,
        description="Expected time service will be restored.",
    )
    cause: str = Field(description="Brief description of the outage cause.")
    advisory_type: AdvisoryType = Field(default=AdvisoryType.NONE)
