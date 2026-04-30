"""Unit tests for the extraction pipeline orchestration."""

from __future__ import annotations

from typing import Optional

import pytest

from gateway.extraction.adapters import OcrAdapter, ParserAdapter, StorageAdapter
from gateway.extraction.exceptions import (
    ImageNotIngestedError,
    OcrFailureError,
    RequestNotFoundError,
)
from gateway.extraction.models import (
    ExtractionResult,
    IngestionStatus,
    LicenseField,
    LicenseRecord,
    NormalizedImage,
    OcrResult,
)
from gateway.extraction.pipeline import LOW_CONFIDENCE_THRESHOLD, run_extraction


# ---------------------------------------------------------------------------
# Stub adapters
# ---------------------------------------------------------------------------


class StubStorage(StorageAdapter):
    def __init__(self, images: Optional[dict[str, NormalizedImage]] = None):
        self._images = images or {}

    def load(self, request_id: str) -> Optional[NormalizedImage]:
        return self._images.get(request_id)


class StubOcr(OcrAdapter):
    def __init__(
        self,
        result: Optional[OcrResult] = None,
        *,
        raise_exc: Optional[Exception] = None,
    ):
        self._result = result
        self._raise_exc = raise_exc

    def recognise(self, image: NormalizedImage) -> OcrResult:
        if self._raise_exc:
            raise self._raise_exc
        assert self._result is not None
        return self._result


class StubParser(ParserAdapter):
    def __init__(self, record: Optional[LicenseRecord] = None):
        self._record = record or LicenseRecord()
        self.last_state_hint: Optional[str] = None

    def parse(
        self, ocr: OcrResult, *, state_hint: Optional[str] = None
    ) -> LicenseRecord:
        self.last_state_hint = state_hint
        return self._record


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ACCEPTED_IMAGE = NormalizedImage(
    request_id="req-1",
    status=IngestionStatus.ACCEPTED,
    image_bytes=b"\x89PNG",
)

REJECTED_IMAGE = NormalizedImage(
    request_id="req-2",
    status=IngestionStatus.REJECTED,
)

PENDING_IMAGE = NormalizedImage(
    request_id="req-3",
    status=IngestionStatus.PENDING,
)

HIGH_CONF_OCR = OcrResult(raw_text="JOHN DOE DL12345", provider_confidence=0.95)
LOW_CONF_OCR = OcrResult(raw_text="J??? D??", provider_confidence=0.40)

HIGH_CONF_RECORD = LicenseRecord(
    first_name=LicenseField(value="JOHN", confidence=0.98),
    last_name=LicenseField(value="DOE", confidence=0.96),
    license_number=LicenseField(value="DL12345", confidence=0.97),
)

LOW_CONF_RECORD = LicenseRecord(
    first_name=LicenseField(value="J???", confidence=0.30),
    last_name=LicenseField(value="D??", confidence=0.25),
)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_returns_extraction_result(self):
        storage = StubStorage({"req-1": ACCEPTED_IMAGE})
        ocr = StubOcr(HIGH_CONF_OCR)
        parser = StubParser(HIGH_CONF_RECORD)

        result = run_extraction(storage, ocr, parser, "req-1")

        assert isinstance(result, ExtractionResult)
        assert result.request_id == "req-1"
        assert result.license_record.first_name.value == "JOHN"
        assert result.overall_confidence > LOW_CONFIDENCE_THRESHOLD
        assert result.warnings == []

    def test_state_hint_forwarded_to_parser(self):
        storage = StubStorage({"req-1": ACCEPTED_IMAGE})
        ocr = StubOcr(HIGH_CONF_OCR)
        parser = StubParser(HIGH_CONF_RECORD)

        run_extraction(storage, ocr, parser, "req-1", state_hint="NY")

        assert parser.last_state_hint == "NY"


# ---------------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------------


class TestRequestNotFound:
    def test_unknown_request_id_raises(self):
        storage = StubStorage({})
        ocr = StubOcr(HIGH_CONF_OCR)
        parser = StubParser()

        with pytest.raises(RequestNotFoundError) as exc_info:
            run_extraction(storage, ocr, parser, "no-such-id")
        assert exc_info.value.reason_code == "request_id_not_found"
        assert exc_info.value.status_code == 404


class TestImageNotIngested:
    @pytest.mark.parametrize(
        "image",
        [REJECTED_IMAGE, PENDING_IMAGE],
        ids=["rejected", "pending"],
    )
    def test_non_accepted_status_raises(self, image: NormalizedImage):
        storage = StubStorage({image.request_id: image})
        ocr = StubOcr(HIGH_CONF_OCR)
        parser = StubParser()

        with pytest.raises(ImageNotIngestedError) as exc_info:
            run_extraction(storage, ocr, parser, image.request_id)
        assert exc_info.value.reason_code == "image_not_ingested"
        assert exc_info.value.status_code == 409


class TestOcrFailure:
    def test_ocr_exception_surfaces_as_502(self):
        storage = StubStorage({"req-1": ACCEPTED_IMAGE})
        ocr = StubOcr(raise_exc=RuntimeError("provider down"))
        parser = StubParser()

        with pytest.raises(OcrFailureError) as exc_info:
            run_extraction(storage, ocr, parser, "req-1")
        assert exc_info.value.reason_code == "ocr_failure"
        assert exc_info.value.status_code == 502


# ---------------------------------------------------------------------------
# Low confidence warning
# ---------------------------------------------------------------------------


class TestLowConfidenceWarning:
    def test_low_confidence_produces_warning(self):
        storage = StubStorage({"req-1": ACCEPTED_IMAGE})
        ocr = StubOcr(LOW_CONF_OCR)
        parser = StubParser(LOW_CONF_RECORD)

        result = run_extraction(storage, ocr, parser, "req-1")

        assert result.overall_confidence < LOW_CONFIDENCE_THRESHOLD
        assert len(result.warnings) == 1
        assert result.warnings[0].code == "low_confidence_overall"

    def test_high_confidence_no_warning(self):
        storage = StubStorage({"req-1": ACCEPTED_IMAGE})
        ocr = StubOcr(HIGH_CONF_OCR)
        parser = StubParser(HIGH_CONF_RECORD)

        result = run_extraction(storage, ocr, parser, "req-1")

        assert result.warnings == []
