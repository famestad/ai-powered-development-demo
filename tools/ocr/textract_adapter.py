from __future__ import annotations

import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from tools.ocr.adapter import OcrAdapter
from tools.ocr.errors import OcrError, OcrErrorCode
from tools.ocr.models import OcrBlock

logger = logging.getLogger(__name__)

_ERROR_MAP: dict[str, OcrErrorCode] = {
    "InvalidParameterException": OcrErrorCode.INVALID_IMAGE,
    "InvalidS3ObjectException": OcrErrorCode.INVALID_IMAGE,
    "UnsupportedDocumentException": OcrErrorCode.INVALID_IMAGE,
    "ProvisionedThroughputExceededException": OcrErrorCode.QUOTA_EXCEEDED,
    "ThrottlingException": OcrErrorCode.QUOTA_EXCEEDED,
    "InternalServerError": OcrErrorCode.PROVIDER_UNAVAILABLE,
}


class TextractAdapter(OcrAdapter):
    """OCR implementation backed by AWS Textract detect_document_text."""

    def __init__(self, region: str | None = None) -> None:
        self._client = boto3.client("textract", region_name=region)

    def extract(self, normalized_image: bytes) -> list[OcrBlock]:
        try:
            response = self._client.detect_document_text(
                Document={"Bytes": normalized_image},
            )
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            mapped = _ERROR_MAP.get(error_code, OcrErrorCode.UNKNOWN)
            raise OcrError(mapped, f"Textract call failed: {error_code}") from None
        except BotoCoreError:
            raise OcrError(
                OcrErrorCode.PROVIDER_UNAVAILABLE,
                "Textract service unreachable",
            ) from None

        blocks: list[OcrBlock] = []
        for block in response.get("Blocks", []):
            if block["BlockType"] not in ("LINE", "WORD"):
                continue

            text = block.get("Text", "")
            confidence = block.get("Confidence", 0.0) / 100.0
            geo = block.get("Geometry", {}).get("BoundingBox", {})

            width_img = response.get("DocumentMetadata", {}).get("Pages", 1)
            left = int(geo.get("Left", 0) * 1000)
            top = int(geo.get("Top", 0) * 1000)
            w = int(geo.get("Width", 0) * 1000)
            h = int(geo.get("Height", 0) * 1000)

            blocks.append(
                OcrBlock(text=text, bbox=(left, top, w, h), confidence=confidence)
            )

        return blocks
