"""Domain models for the license extraction pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class IngestionStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class NormalizedImage(BaseModel):
    request_id: str
    status: IngestionStatus
    image_bytes: Optional[bytes] = None
    mime_type: str = "image/jpeg"


class OcrResult(BaseModel):
    raw_text: str
    provider_confidence: float = Field(ge=0.0, le=1.0)


class LicenseField(BaseModel):
    value: str
    confidence: float = Field(ge=0.0, le=1.0)


class LicenseRecord(BaseModel):
    first_name: Optional[LicenseField] = None
    last_name: Optional[LicenseField] = None
    middle_name: Optional[LicenseField] = None
    date_of_birth: Optional[LicenseField] = None
    expiration_date: Optional[LicenseField] = None
    issue_date: Optional[LicenseField] = None
    license_number: Optional[LicenseField] = None
    address: Optional[LicenseField] = None
    city: Optional[LicenseField] = None
    state: Optional[LicenseField] = None
    zip_code: Optional[LicenseField] = None
    license_class: Optional[LicenseField] = None
    sex: Optional[LicenseField] = None
    height: Optional[LicenseField] = None
    weight: Optional[LicenseField] = None
    eye_color: Optional[LicenseField] = None
    document_discriminator: Optional[LicenseField] = None


class ExtractionWarning(BaseModel):
    code: str
    message: str


class ExtractionResult(BaseModel):
    request_id: str
    license_record: LicenseRecord
    overall_confidence: float = Field(ge=0.0, le=1.0)
    warnings: list[ExtractionWarning] = Field(default_factory=list)
