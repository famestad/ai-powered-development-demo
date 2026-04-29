"""Unit tests for tools.ocr — mock round-trip, confidence normalization, error mapping."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from tools.ocr.adapter import OcrAdapter
from tools.ocr.errors import OcrError, OcrErrorCode
from tools.ocr.factory import create_ocr_adapter
from tools.ocr.mock_adapter import MockOcrAdapter
from tools.ocr.models import OcrBlock
from tools.ocr.textract_adapter import TextractAdapter


# ---------------------------------------------------------------------------
# OcrBlock model
# ---------------------------------------------------------------------------


class TestOcrBlock:
    def test_valid_block(self):
        block = OcrBlock(text="HELLO", bbox=(10, 20, 100, 30), confidence=0.95)
        assert block.text == "HELLO"
        assert block.bbox == (10, 20, 100, 30)
        assert block.confidence == 0.95

    def test_confidence_clamped_above_one(self):
        block = OcrBlock(text="X", bbox=(0, 0, 1, 1), confidence=1.5)
        assert block.confidence == 1.0

    def test_confidence_clamped_below_zero(self):
        block = OcrBlock(text="X", bbox=(0, 0, 1, 1), confidence=-0.1)
        assert block.confidence == 0.0

    def test_confidence_boundaries(self):
        b0 = OcrBlock(text="X", bbox=(0, 0, 1, 1), confidence=0.0)
        b1 = OcrBlock(text="X", bbox=(0, 0, 1, 1), confidence=1.0)
        assert b0.confidence == 0.0
        assert b1.confidence == 1.0


# ---------------------------------------------------------------------------
# Mock adapter round-trip
# ---------------------------------------------------------------------------


class TestMockAdapter:
    def test_conforms_to_interface(self):
        adapter = MockOcrAdapter(fixture_name="standard_license")
        assert isinstance(adapter, OcrAdapter)

    def test_standard_license_round_trip(self):
        adapter = MockOcrAdapter(fixture_name="standard_license")
        blocks = adapter.extract(b"dummy-image-bytes")
        assert len(blocks) == 18
        assert all(isinstance(b, OcrBlock) for b in blocks)
        assert blocks[0].text == "DRIVER LICENSE"

    def test_faded_license_round_trip(self):
        adapter = MockOcrAdapter(fixture_name="faded_license")
        blocks = adapter.extract(b"dummy")
        assert len(blocks) == 15
        assert all(b.confidence <= 1.0 for b in blocks)

    def test_rotated_license_round_trip(self):
        adapter = MockOcrAdapter(fixture_name="rotated_license")
        blocks = adapter.extract(b"dummy")
        assert len(blocks) == 17

    def test_deterministic_output(self):
        adapter = MockOcrAdapter(fixture_name="standard_license")
        first = adapter.extract(b"a")
        second = adapter.extract(b"b")
        assert first == second

    def test_missing_fixture_raises(self):
        with pytest.raises(FileNotFoundError):
            MockOcrAdapter(fixture_name="nonexistent_fixture")

    def test_all_confidences_normalized(self):
        for name in ("standard_license", "faded_license", "rotated_license"):
            adapter = MockOcrAdapter(fixture_name=name)
            for block in adapter.extract(b"x"):
                assert 0.0 <= block.confidence <= 1.0


# ---------------------------------------------------------------------------
# Textract adapter — error mapping (mocked boto3)
# ---------------------------------------------------------------------------


class TestTextractErrorMapping:
    def _make_client_error(self, code: str) -> ClientError:
        return ClientError(
            {"Error": {"Code": code, "Message": "test"}},
            "DetectDocumentText",
        )

    def test_invalid_parameter_maps_to_invalid_image(self):
        adapter = TextractAdapter.__new__(TextractAdapter)
        adapter._client = MagicMock()
        adapter._client.detect_document_text.side_effect = self._make_client_error(
            "InvalidParameterException"
        )
        with pytest.raises(OcrError) as exc_info:
            adapter.extract(b"bad")
        assert exc_info.value.code == OcrErrorCode.INVALID_IMAGE

    def test_throttling_maps_to_quota_exceeded(self):
        adapter = TextractAdapter.__new__(TextractAdapter)
        adapter._client = MagicMock()
        adapter._client.detect_document_text.side_effect = self._make_client_error(
            "ThrottlingException"
        )
        with pytest.raises(OcrError) as exc_info:
            adapter.extract(b"img")
        assert exc_info.value.code == OcrErrorCode.QUOTA_EXCEEDED

    def test_internal_server_error_maps_to_provider_unavailable(self):
        adapter = TextractAdapter.__new__(TextractAdapter)
        adapter._client = MagicMock()
        adapter._client.detect_document_text.side_effect = self._make_client_error(
            "InternalServerError"
        )
        with pytest.raises(OcrError) as exc_info:
            adapter.extract(b"img")
        assert exc_info.value.code == OcrErrorCode.PROVIDER_UNAVAILABLE

    def test_unknown_error_code_maps_to_unknown(self):
        adapter = TextractAdapter.__new__(TextractAdapter)
        adapter._client = MagicMock()
        adapter._client.detect_document_text.side_effect = self._make_client_error(
            "SomeNewException"
        )
        with pytest.raises(OcrError) as exc_info:
            adapter.extract(b"img")
        assert exc_info.value.code == OcrErrorCode.UNKNOWN

    def test_confidence_normalization_from_textract(self):
        adapter = TextractAdapter.__new__(TextractAdapter)
        adapter._client = MagicMock()
        adapter._client.detect_document_text.return_value = {
            "Blocks": [
                {
                    "BlockType": "LINE",
                    "Text": "HELLO",
                    "Confidence": 95.5,
                    "Geometry": {
                        "BoundingBox": {
                            "Left": 0.1,
                            "Top": 0.2,
                            "Width": 0.3,
                            "Height": 0.05,
                        }
                    },
                }
            ],
        }
        blocks = adapter.extract(b"img")
        assert len(blocks) == 1
        assert blocks[0].confidence == pytest.approx(0.955, abs=0.001)
        assert blocks[0].text == "HELLO"


# ---------------------------------------------------------------------------
# OcrError
# ---------------------------------------------------------------------------


class TestOcrError:
    def test_attributes(self):
        err = OcrError(OcrErrorCode.TIMEOUT, "took too long")
        assert err.code == OcrErrorCode.TIMEOUT
        assert err.message == "took too long"
        assert "TIMEOUT" in str(err)

    def test_is_exception(self):
        assert issubclass(OcrError, Exception)


# ---------------------------------------------------------------------------
# Factory / config
# ---------------------------------------------------------------------------


class TestFactory:
    def test_default_is_mock(self):
        adapter = create_ocr_adapter()
        assert isinstance(adapter, MockOcrAdapter)

    def test_explicit_mock(self):
        adapter = create_ocr_adapter(provider="mock")
        assert isinstance(adapter, MockOcrAdapter)

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("OCR_PROVIDER", "mock")
        adapter = create_ocr_adapter()
        assert isinstance(adapter, MockOcrAdapter)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown OCR provider"):
            create_ocr_adapter(provider="nonexistent")

    @patch("tools.ocr.textract_adapter.boto3")
    def test_textract_provider(self, mock_boto):
        adapter = create_ocr_adapter(provider="textract", region="us-east-1")
        assert isinstance(adapter, TextractAdapter)
