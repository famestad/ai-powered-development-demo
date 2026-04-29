from __future__ import annotations

from abc import ABC, abstractmethod

from tools.ocr.models import OcrBlock


class OcrAdapter(ABC):
    """Pluggable OCR interface consumed by downstream field-extraction logic."""

    @abstractmethod
    def extract(self, normalized_image: bytes) -> list[OcrBlock]:
        """Run OCR on a pre-processed image and return text blocks with geometry.

        Args:
            normalized_image: Raw image bytes (PNG/JPEG) already preprocessed
                by the ingestion pipeline.

        Returns:
            Ordered list of OcrBlock results.

        Raises:
            OcrError: On any provider failure.
        """
