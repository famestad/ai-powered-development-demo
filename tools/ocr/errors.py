from __future__ import annotations

from enum import Enum


class OcrErrorCode(str, Enum):
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    INVALID_IMAGE = "INVALID_IMAGE"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"


class OcrError(Exception):
    """Structured OCR failure — no provider stack traces leak upward."""

    def __init__(self, code: OcrErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"[{code.value}] {message}")
