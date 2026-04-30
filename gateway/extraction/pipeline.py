"""Extraction pipeline: storage → OCR → parser → result."""

from __future__ import annotations

import logging
from typing import Optional

from gateway.extraction.adapters import OcrAdapter, ParserAdapter, StorageAdapter
from gateway.extraction.exceptions import (
    ImageNotIngestedError,
    OcrFailureError,
    RequestNotFoundError,
)
from gateway.extraction.models import (
    ExtractionResult,
    ExtractionWarning,
    IngestionStatus,
)

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_THRESHOLD = 0.80


def _field_confidences(record_dict: dict) -> list[float]:
    values: list[float] = []
    for v in record_dict.values():
        if isinstance(v, dict) and "confidence" in v:
            values.append(v["confidence"])
    return values


def run_extraction(
    storage: StorageAdapter,
    ocr: OcrAdapter,
    parser: ParserAdapter,
    request_id: str,
    *,
    state_hint: Optional[str] = None,
) -> ExtractionResult:
    image = storage.load(request_id)
    if image is None:
        raise RequestNotFoundError(f"No record for request_id={request_id}")

    if image.status != IngestionStatus.ACCEPTED:
        raise ImageNotIngestedError(
            f"request_id={request_id} has status '{image.status.value}', "
            "expected 'accepted'"
        )

    try:
        ocr_result = ocr.recognise(image)
    except Exception as exc:
        logger.exception("OCR provider failure for request_id=%s", request_id)
        raise OcrFailureError(
            f"OCR provider failed for request_id={request_id}"
        ) from exc

    license_record = parser.parse(ocr_result, state_hint=state_hint)

    field_confs = _field_confidences(license_record.model_dump())
    if field_confs:
        overall_confidence = sum(field_confs) / len(field_confs)
    else:
        overall_confidence = ocr_result.provider_confidence

    warnings: list[ExtractionWarning] = []
    if overall_confidence < LOW_CONFIDENCE_THRESHOLD:
        warnings.append(
            ExtractionWarning(
                code="low_confidence_overall",
                message=(
                    f"Overall confidence {overall_confidence:.2f} is below "
                    f"threshold {LOW_CONFIDENCE_THRESHOLD:.2f}"
                ),
            )
        )

    return ExtractionResult(
        request_id=request_id,
        license_record=license_record,
        overall_confidence=round(overall_confidence, 4),
        warnings=warnings,
    )
