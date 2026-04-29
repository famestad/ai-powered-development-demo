from __future__ import annotations

import enum
from datetime import datetime

from pydantic import BaseModel, Field


class IngestionStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class QualityVerdict(str, enum.Enum):
    PASS = "pass"
    FAIL = "fail"


class QualityCheckResult(BaseModel):
    passed: bool
    score: float = Field(ge=0.0, le=1.0)


class QualityReport(BaseModel):
    resolution: QualityCheckResult
    blur: QualityCheckResult
    glare: QualityCheckResult
    overall_verdict: QualityVerdict

    @property
    def all_passed(self) -> bool:
        return self.resolution.passed and self.blur.passed and self.glare.passed


class IngestionRequest(BaseModel):
    filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    size_bytes: int = Field(gt=0)
    submitted_at: datetime


class IngestionResult(BaseModel):
    request_id: str = Field(min_length=1)
    stored_path: str = Field(default="")
    content_hash: str = Field(min_length=1)
    status: IngestionStatus = IngestionStatus.PENDING
    quality_report: QualityReport | None = None
    rejection_reasons: list[str] = Field(default_factory=list)
