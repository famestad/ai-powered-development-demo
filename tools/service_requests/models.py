"""Pydantic models for utility service requests."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class RequestType(str, Enum):
    """Type of utility service request."""

    START = "start"
    STOP = "stop"
    TRANSFER = "transfer"


class ServiceType(str, Enum):
    """Type of utility service."""

    WATER = "water"
    POWER = "power"
    GAS = "gas"


class RequestStatus(str, Enum):
    """Current status of the service request."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Address(BaseModel):
    """Mailing or service address."""

    street: str = Field(min_length=1)
    city: str = Field(min_length=1)
    zip_code: str = Field(pattern=r"^\d{5}(-\d{4})?$")


class ServiceRequest(BaseModel):
    """A utility service request (start, stop, or transfer)."""

    id: str = Field(description="Reference number in SR-YYYY-NNNN format.")
    request_type: RequestType
    service_type: ServiceType
    current_address: Address | None = None
    new_address: Address | None = None
    preferred_start_date: date
    account_number: str = Field(min_length=1)
    status: RequestStatus = RequestStatus.PENDING
    created_at: datetime = Field(default_factory=datetime.utcnow)
