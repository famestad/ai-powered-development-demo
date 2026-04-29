from __future__ import annotations

import json
from pathlib import Path

from tools.ocr.adapter import OcrAdapter
from tools.ocr.models import OcrBlock

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class MockOcrAdapter(OcrAdapter):
    """Deterministic test double that returns fixture data without external calls."""

    def __init__(self, fixture_name: str = "standard_license") -> None:
        fixture_path = FIXTURES_DIR / f"{fixture_name}.json"
        with open(fixture_path) as f:
            raw = json.load(f)
        self._blocks = [OcrBlock(**b) for b in raw]

    def extract(self, normalized_image: bytes) -> list[OcrBlock]:
        return list(self._blocks)
