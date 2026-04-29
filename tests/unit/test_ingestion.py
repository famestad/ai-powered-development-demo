"""Unit tests for the ingestion data model and storage layer."""

import hashlib
import re
from datetime import datetime, timezone

import pytest

from tools.ingestion.models import (
    IngestionRequest,
    IngestionResult,
    IngestionStatus,
    QualityCheckResult,
    QualityReport,
    QualityVerdict,
)
from tools.ingestion.request_id import generate_request_id
from tools.ingestion.storage import LocalFilesystemBackend


# ---------------------------------------------------------------------------
# Pydantic model validation
# ---------------------------------------------------------------------------


class TestIngestionRequest:
    def test_valid_request(self):
        req = IngestionRequest(
            filename="photo.jpg",
            content_type="image/jpeg",
            size_bytes=1024,
            submitted_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert req.filename == "photo.jpg"
        assert req.content_type == "image/jpeg"
        assert req.size_bytes == 1024

    def test_empty_filename_rejected(self):
        with pytest.raises(Exception):
            IngestionRequest(
                filename="",
                content_type="image/jpeg",
                size_bytes=1024,
                submitted_at=datetime.now(tz=timezone.utc),
            )

    def test_empty_content_type_rejected(self):
        with pytest.raises(Exception):
            IngestionRequest(
                filename="photo.jpg",
                content_type="",
                size_bytes=1024,
                submitted_at=datetime.now(tz=timezone.utc),
            )

    def test_zero_size_rejected(self):
        with pytest.raises(Exception):
            IngestionRequest(
                filename="photo.jpg",
                content_type="image/jpeg",
                size_bytes=0,
                submitted_at=datetime.now(tz=timezone.utc),
            )

    def test_negative_size_rejected(self):
        with pytest.raises(Exception):
            IngestionRequest(
                filename="photo.jpg",
                content_type="image/jpeg",
                size_bytes=-1,
                submitted_at=datetime.now(tz=timezone.utc),
            )


class TestQualityReport:
    def test_valid_report(self):
        report = QualityReport(
            resolution=QualityCheckResult(passed=True, score=0.95),
            blur=QualityCheckResult(passed=True, score=0.88),
            glare=QualityCheckResult(passed=False, score=0.3),
            overall_verdict=QualityVerdict.FAIL,
        )
        assert report.resolution.passed is True
        assert report.glare.passed is False
        assert report.overall_verdict == QualityVerdict.FAIL

    def test_all_passed_property(self):
        report = QualityReport(
            resolution=QualityCheckResult(passed=True, score=0.9),
            blur=QualityCheckResult(passed=True, score=0.9),
            glare=QualityCheckResult(passed=True, score=0.9),
            overall_verdict=QualityVerdict.PASS,
        )
        assert report.all_passed is True

    def test_all_passed_false_when_one_fails(self):
        report = QualityReport(
            resolution=QualityCheckResult(passed=True, score=0.9),
            blur=QualityCheckResult(passed=False, score=0.2),
            glare=QualityCheckResult(passed=True, score=0.9),
            overall_verdict=QualityVerdict.FAIL,
        )
        assert report.all_passed is False

    def test_score_out_of_range_rejected(self):
        with pytest.raises(Exception):
            QualityCheckResult(passed=True, score=1.5)

    def test_negative_score_rejected(self):
        with pytest.raises(Exception):
            QualityCheckResult(passed=True, score=-0.1)


class TestIngestionResult:
    def test_valid_result(self):
        result = IngestionResult(
            request_id="ING-20260115-abc123def456",
            stored_path="/data/ING-20260115-abc123def456/normalized.bin",
            content_hash="a" * 64,
            status=IngestionStatus.ACCEPTED,
        )
        assert result.request_id == "ING-20260115-abc123def456"
        assert result.status == IngestionStatus.ACCEPTED
        assert result.quality_report is None
        assert result.rejection_reasons == []

    def test_default_status_is_pending(self):
        result = IngestionResult(
            request_id="ING-20260115-abc123def456",
            content_hash="a" * 64,
        )
        assert result.status == IngestionStatus.PENDING

    def test_empty_request_id_rejected(self):
        with pytest.raises(Exception):
            IngestionResult(request_id="", content_hash="a" * 64)

    def test_result_with_quality_report(self):
        report = QualityReport(
            resolution=QualityCheckResult(passed=True, score=0.95),
            blur=QualityCheckResult(passed=True, score=0.88),
            glare=QualityCheckResult(passed=True, score=0.92),
            overall_verdict=QualityVerdict.PASS,
        )
        result = IngestionResult(
            request_id="ING-20260115-abc123def456",
            stored_path="/data/normalized.bin",
            content_hash="a" * 64,
            status=IngestionStatus.ACCEPTED,
            quality_report=report,
        )
        assert result.quality_report is not None
        assert result.quality_report.all_passed is True

    def test_result_with_rejection_reasons(self):
        result = IngestionResult(
            request_id="ING-20260115-abc123def456",
            content_hash="a" * 64,
            status=IngestionStatus.REJECTED,
            rejection_reasons=["blur_too_high", "resolution_too_low"],
        )
        assert len(result.rejection_reasons) == 2


# ---------------------------------------------------------------------------
# Request ID generation
# ---------------------------------------------------------------------------

REQUEST_ID_PATTERN = re.compile(r"^ING-\d{8}-[0-9a-f]{12}$")


class TestRequestIdGeneration:
    def test_format(self):
        rid = generate_request_id()
        assert REQUEST_ID_PATTERN.match(rid), f"Unexpected format: {rid}"

    def test_contains_current_date(self):
        rid = generate_request_id()
        today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
        assert today in rid

    def test_uniqueness(self):
        ids = {generate_request_id() for _ in range(1000)}
        assert len(ids) == 1000


# ---------------------------------------------------------------------------
# Storage adapter — round-trip
# ---------------------------------------------------------------------------


class TestLocalFilesystemBackend:
    def test_round_trip_preserves_bytes(self, tmp_path):
        backend = LocalFilesystemBackend(tmp_path)
        request_id = "ING-20260115-aabbccddeeff"
        data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 256
        metadata = {
            "original_filename": "scan.png",
            "content_type": "image/png",
            "size_bytes": len(data),
            "original_path": "/uploads/scan.png",
        }

        backend.save(request_id, data, metadata)
        loaded_bytes, loaded_meta = backend.load(request_id)

        assert loaded_bytes == data

    def test_round_trip_preserves_metadata(self, tmp_path):
        backend = LocalFilesystemBackend(tmp_path)
        request_id = "ING-20260115-aabbccddeeff"
        data = b"test-image-bytes"
        metadata = {
            "original_filename": "permit.jpg",
            "content_type": "image/jpeg",
            "size_bytes": len(data),
            "original_path": "/uploads/permit.jpg",
        }

        backend.save(request_id, data, metadata)
        _, loaded_meta = backend.load(request_id)

        assert loaded_meta["original_filename"] == "permit.jpg"
        assert loaded_meta["content_type"] == "image/jpeg"
        assert loaded_meta["size_bytes"] == len(data)
        assert loaded_meta["request_id"] == request_id

    def test_sha256_recorded(self, tmp_path):
        backend = LocalFilesystemBackend(tmp_path)
        request_id = "ING-20260115-112233445566"
        data = b"hello-world-image-data"
        expected_hash = hashlib.sha256(data).hexdigest()
        metadata = {
            "original_filename": "doc.tiff",
            "content_type": "image/tiff",
            "size_bytes": len(data),
        }

        backend.save(request_id, data, metadata)
        _, loaded_meta = backend.load(request_id)

        assert loaded_meta["content_hash"] == expected_hash

    def test_load_missing_raises(self, tmp_path):
        backend = LocalFilesystemBackend(tmp_path)
        with pytest.raises(FileNotFoundError):
            backend.load("ING-20260115-nonexistent0")

    def test_overwrite_same_request_id(self, tmp_path):
        backend = LocalFilesystemBackend(tmp_path)
        request_id = "ING-20260115-aabbccddeeff"
        meta = {"original_filename": "a.png", "content_type": "image/png", "size_bytes": 5}

        backend.save(request_id, b"first", meta)
        backend.save(request_id, b"second", meta)

        loaded_bytes, _ = backend.load(request_id)
        assert loaded_bytes == b"second"

    def test_multiple_request_ids_isolated(self, tmp_path):
        backend = LocalFilesystemBackend(tmp_path)
        meta = {"original_filename": "x.png", "content_type": "image/png", "size_bytes": 1}

        backend.save("ING-20260115-aaaa00000001", b"data-a", meta)
        backend.save("ING-20260115-aaaa00000002", b"data-b", meta)

        bytes_a, _ = backend.load("ING-20260115-aaaa00000001")
        bytes_b, _ = backend.load("ING-20260115-aaaa00000002")

        assert bytes_a == b"data-a"
        assert bytes_b == b"data-b"

    def test_timestamps_recorded(self, tmp_path):
        backend = LocalFilesystemBackend(tmp_path)
        request_id = "ING-20260115-aabbccddeeff"
        data = b"img"
        metadata = {"original_filename": "f.png", "content_type": "image/png", "size_bytes": 3}

        backend.save(request_id, data, metadata)
        _, loaded_meta = backend.load(request_id)

        assert "created_at" in loaded_meta
        datetime.fromisoformat(loaded_meta["created_at"])

    def test_normalized_path_recorded(self, tmp_path):
        backend = LocalFilesystemBackend(tmp_path)
        request_id = "ING-20260115-aabbccddeeff"
        data = b"img"
        metadata = {
            "original_filename": "f.png",
            "content_type": "image/png",
            "size_bytes": 3,
            "original_path": "/uploads/f.png",
        }

        stored_path = backend.save(request_id, data, metadata)
        _, loaded_meta = backend.load(request_id)

        assert loaded_meta["normalized_path"] == stored_path
        assert loaded_meta["original_path"] == "/uploads/f.png"
