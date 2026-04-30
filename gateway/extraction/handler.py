"""POST /extract/front — synchronous front-of-license extraction endpoint."""

from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from gateway.extraction.adapters import OcrAdapter, ParserAdapter, StorageAdapter
from gateway.extraction.exceptions import ExtractionError
from gateway.extraction.pipeline import run_extraction

logger = logging.getLogger(__name__)


class ExtractFrontRequest(BaseModel):
    request_id: str = Field(..., min_length=1)


_storage: Optional[StorageAdapter] = None
_ocr: Optional[OcrAdapter] = None
_parser: Optional[ParserAdapter] = None


def configure(
    storage: StorageAdapter,
    ocr: OcrAdapter,
    parser: ParserAdapter,
) -> None:
    global _storage, _ocr, _parser
    _storage = storage
    _ocr = ocr
    _parser = parser


def handle_extract_front(
    body: dict[str, Any],
    state_hint: Optional[str] = None,
) -> tuple[dict[str, Any], int]:
    if _storage is None or _ocr is None or _parser is None:
        logger.error("Extraction adapters not configured")
        return {"error": "Internal server error", "reason": "misconfigured"}, 500

    try:
        req = ExtractFrontRequest(**body)
    except Exception:
        return {
            "error": "Invalid request body",
            "reason": "validation_error",
        }, 400

    try:
        result = run_extraction(
            _storage,
            _ocr,
            _parser,
            req.request_id,
            state_hint=state_hint,
        )
    except ExtractionError as exc:
        return {
            "error": str(exc),
            "reason": exc.reason_code,
        }, exc.status_code
    except Exception:
        logger.exception("Unexpected error during extraction")
        return {"error": "Internal server error", "reason": "unknown"}, 500

    return result.model_dump(), 200
