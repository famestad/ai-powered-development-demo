from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class OcrBlock(BaseModel):
    """A single text block extracted by OCR with bounding-box geometry."""

    text: str
    bbox: tuple[int, int, int, int] = Field(
        description="Bounding box as (left, top, width, height) in pixels",
    )
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, v: float) -> float:
        return max(0.0, min(1.0, v))
