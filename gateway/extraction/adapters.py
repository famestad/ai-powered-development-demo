"""Abstract adapter interfaces for the extraction pipeline."""

from __future__ import annotations

import abc
from typing import Optional

from gateway.extraction.models import LicenseRecord, NormalizedImage, OcrResult


class StorageAdapter(abc.ABC):
    @abc.abstractmethod
    def load(self, request_id: str) -> Optional[NormalizedImage]:
        """Return the NormalizedImage for *request_id*, or None if not found."""


class OcrAdapter(abc.ABC):
    @abc.abstractmethod
    def recognise(self, image: NormalizedImage) -> OcrResult:
        """Run OCR on the image and return raw text + confidence."""


class ParserAdapter(abc.ABC):
    @abc.abstractmethod
    def parse(
        self, ocr: OcrResult, *, state_hint: Optional[str] = None
    ) -> LicenseRecord:
        """Parse OCR text into a structured LicenseRecord."""
