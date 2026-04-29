from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class IngestionMetadata(BaseModel):
    request_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    content_hash: str
    created_at: str
    original_path: str
    normalized_path: str


class StorageBackend(ABC):
    @abstractmethod
    def save(
        self,
        request_id: str,
        normalized_bytes: bytes,
        metadata: dict[str, Any],
    ) -> str:
        """Save normalized image bytes and metadata. Returns the stored path."""

    @abstractmethod
    def load(self, request_id: str) -> tuple[bytes, dict[str, Any]]:
        """Load normalized bytes and metadata for a request_id."""


class LocalFilesystemBackend(StorageBackend):
    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)

    def save(
        self,
        request_id: str,
        normalized_bytes: bytes,
        metadata: dict[str, Any],
    ) -> str:
        dest = self._base / request_id
        dest.mkdir(parents=True, exist_ok=True)

        content_hash = hashlib.sha256(normalized_bytes).hexdigest()

        image_path = dest / "normalized.bin"
        image_path.write_bytes(normalized_bytes)

        record = IngestionMetadata(
            request_id=request_id,
            original_filename=metadata.get("original_filename", ""),
            content_type=metadata.get("content_type", ""),
            size_bytes=metadata.get("size_bytes", len(normalized_bytes)),
            content_hash=content_hash,
            created_at=datetime.now(tz=timezone.utc).isoformat(),
            original_path=metadata.get("original_path", ""),
            normalized_path=str(image_path),
        )
        meta_path = dest / "metadata.json"
        meta_path.write_text(record.model_dump_json(indent=2))

        return str(image_path)

    def load(self, request_id: str) -> tuple[bytes, dict[str, Any]]:
        dest = self._base / request_id
        image_path = dest / "normalized.bin"
        meta_path = dest / "metadata.json"

        if not image_path.exists() or not meta_path.exists():
            raise FileNotFoundError(
                f"No ingestion record found for request_id={request_id}"
            )

        normalized_bytes = image_path.read_bytes()
        metadata = json.loads(meta_path.read_text())
        return normalized_bytes, metadata
