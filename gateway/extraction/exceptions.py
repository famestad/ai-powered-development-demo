"""Extraction pipeline exceptions with reason codes."""

from __future__ import annotations


class ExtractionError(Exception):
    reason_code: str
    status_code: int

    def __init__(self, message: str) -> None:
        super().__init__(message)


class RequestNotFoundError(ExtractionError):
    reason_code = "request_id_not_found"
    status_code = 404


class ImageNotIngestedError(ExtractionError):
    reason_code = "image_not_ingested"
    status_code = 409


class OcrFailureError(ExtractionError):
    reason_code = "ocr_failure"
    status_code = 502
