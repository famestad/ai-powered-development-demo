from __future__ import annotations

import os

from tools.ocr.adapter import OcrAdapter


def create_ocr_adapter(
    provider: str | None = None,
    **kwargs: object,
) -> OcrAdapter:
    """Instantiate the configured OCR adapter.

    Provider resolution order:
      1. Explicit *provider* argument
      2. ``OCR_PROVIDER`` environment variable
      3. Defaults to ``"mock"``
    """
    provider = provider or os.environ.get("OCR_PROVIDER", "mock")

    if provider == "textract":
        from tools.ocr.textract_adapter import TextractAdapter

        return TextractAdapter(region=kwargs.get("region"))  # type: ignore[arg-type]

    if provider == "mock":
        from tools.ocr.mock_adapter import MockOcrAdapter

        return MockOcrAdapter(
            fixture_name=kwargs.get("fixture_name", "standard_license"),  # type: ignore[arg-type]
        )

    raise ValueError(f"Unknown OCR provider: {provider!r}")
