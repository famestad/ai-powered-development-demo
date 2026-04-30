"""Unit tests for the extraction HTTP handler layer."""

from __future__ import annotations

from typing import Optional

import pytest

from gateway.extraction import handler as extraction_handler
from gateway.extraction.adapters import OcrAdapter, ParserAdapter, StorageAdapter
from gateway.extraction.handler import handle_extract_front
from gateway.extraction.models import (
    IngestionStatus,
    LicenseField,
    LicenseRecord,
    NormalizedImage,
    OcrResult,
)


# ---------------------------------------------------------------------------
# Reusable stub adapters
# ---------------------------------------------------------------------------


class FakeStorage(StorageAdapter):
    def __init__(self, images: Optional[dict[str, NormalizedImage]] = None):
        self._images = images or {}

    def load(self, request_id: str) -> Optional[NormalizedImage]:
        return self._images.get(request_id)


class FakeOcr(OcrAdapter):
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


class FakeParser(ParserAdapter):
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

ACCEPTED = NormalizedImage(
    request_id="req-ok",
    status=IngestionStatus.ACCEPTED,
    image_bytes=b"\x89PNG",
)

REJECTED = NormalizedImage(
    request_id="req-rej",
    status=IngestionStatus.REJECTED,
)

GOOD_OCR = OcrResult(raw_text="JOHN DOE DL12345", provider_confidence=0.95)

GOOD_RECORD = LicenseRecord(
    first_name=LicenseField(value="JOHN", confidence=0.98),
    last_name=LicenseField(value="DOE", confidence=0.96),
    license_number=LicenseField(value="DL12345", confidence=0.97),
)


@pytest.fixture(autouse=True)
def _configure_defaults():
    """Reset adapters between tests."""
    extraction_handler.configure(
        storage=FakeStorage({"req-ok": ACCEPTED, "req-rej": REJECTED}),
        ocr=FakeOcr(GOOD_OCR),
        parser=FakeParser(GOOD_RECORD),
    )
    yield
    extraction_handler._storage = None
    extraction_handler._ocr = None
    extraction_handler._parser = None


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_200_with_populated_result(self):
        body, status = handle_extract_front({"request_id": "req-ok"})

        assert status == 200
        assert body["request_id"] == "req-ok"
        assert body["license_record"]["first_name"]["value"] == "JOHN"
        assert body["overall_confidence"] > 0
        assert isinstance(body["warnings"], list)


# ---------------------------------------------------------------------------
# Error responses
# ---------------------------------------------------------------------------


class TestErrorResponses:
    def test_404_for_unknown_request_id(self):
        body, status = handle_extract_front({"request_id": "no-such-id"})

        assert status == 404
        assert body["reason"] == "request_id_not_found"

    def test_409_for_rejected_image(self):
        body, status = handle_extract_front({"request_id": "req-rej"})

        assert status == 409
        assert body["reason"] == "image_not_ingested"

    def test_502_for_ocr_failure(self):
        extraction_handler.configure(
            storage=FakeStorage({"req-ok": ACCEPTED}),
            ocr=FakeOcr(raise_exc=RuntimeError("boom")),
            parser=FakeParser(),
        )

        body, status = handle_extract_front({"request_id": "req-ok"})

        assert status == 502
        assert body["reason"] == "ocr_failure"

    def test_no_stack_trace_leaked_on_502(self):
        extraction_handler.configure(
            storage=FakeStorage({"req-ok": ACCEPTED}),
            ocr=FakeOcr(raise_exc=RuntimeError("secret info")),
            parser=FakeParser(),
        )

        body, status = handle_extract_front({"request_id": "req-ok"})

        assert status == 502
        assert "secret info" not in body.get("error", "")
        assert "Traceback" not in str(body)

    def test_400_for_missing_request_id(self):
        body, status = handle_extract_front({})

        assert status == 400
        assert body["reason"] == "validation_error"

    def test_400_for_empty_request_id(self):
        body, status = handle_extract_front({"request_id": ""})

        assert status == 400
        assert body["reason"] == "validation_error"

    def test_500_when_not_configured(self):
        extraction_handler._storage = None
        extraction_handler._ocr = None
        extraction_handler._parser = None

        body, status = handle_extract_front({"request_id": "req-ok"})

        assert status == 500
        assert body["reason"] == "misconfigured"


# ---------------------------------------------------------------------------
# state_hint
# ---------------------------------------------------------------------------


class TestStateHint:
    def test_state_hint_passed_through(self):
        parser = FakeParser(GOOD_RECORD)
        extraction_handler.configure(
            storage=FakeStorage({"req-ok": ACCEPTED}),
            ocr=FakeOcr(GOOD_OCR),
            parser=parser,
        )

        handle_extract_front({"request_id": "req-ok"}, state_hint="CA")

        assert parser.last_state_hint == "CA"

    def test_state_hint_none_by_default(self):
        parser = FakeParser(GOOD_RECORD)
        extraction_handler.configure(
            storage=FakeStorage({"req-ok": ACCEPTED}),
            ocr=FakeOcr(GOOD_OCR),
            parser=parser,
        )

        handle_extract_front({"request_id": "req-ok"})

        assert parser.last_state_hint is None


# ---------------------------------------------------------------------------
# Low confidence
# ---------------------------------------------------------------------------


class TestLowConfidence:
    def test_200_with_warning_on_low_confidence(self):
        low_record = LicenseRecord(
            first_name=LicenseField(value="J", confidence=0.30),
        )
        extraction_handler.configure(
            storage=FakeStorage({"req-ok": ACCEPTED}),
            ocr=FakeOcr(OcrResult(raw_text="J", provider_confidence=0.30)),
            parser=FakeParser(low_record),
        )

        body, status = handle_extract_front({"request_id": "req-ok"})

        assert status == 200
        assert any(w["code"] == "low_confidence_overall" for w in body["warnings"])
