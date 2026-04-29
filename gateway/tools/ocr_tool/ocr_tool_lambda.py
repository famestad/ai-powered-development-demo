import base64
import json
import logging

from tools.ocr import OcrError, create_ocr_adapter

logger = logging.getLogger()
logger.setLevel(logging.INFO)

_adapter = create_ocr_adapter()


def handler(event, context):
    """OCR extraction Lambda — one tool per Lambda (ADR-0011)."""
    logger.info("ocr_tool invoked")

    try:
        delimiter = "___"
        original_tool_name = context.client_context.custom["bedrockAgentCoreToolName"]
        tool_name = original_tool_name[
            original_tool_name.index(delimiter) + len(delimiter) :
        ]

        if tool_name != "ocr_extract_text":
            return {
                "error": f"This Lambda only supports 'ocr_extract_text', received: {tool_name}"
            }

        image_b64 = event.get("image_base64", "")
        if not image_b64:
            return {"error": "image_base64 is required"}

        try:
            image_bytes = base64.b64decode(image_b64, validate=True)
        except Exception:
            return {"error": "image_base64 is not valid base64"}

        blocks = _adapter.extract(image_bytes)
        payload = [b.model_dump() for b in blocks]

        return {
            "content": [{"type": "text", "text": json.dumps(payload)}],
        }

    except OcrError as exc:
        logger.error("OCR failed: %s", exc)
        return {"error": f"OCR failed [{exc.code.value}]: {exc.message}"}
    except Exception as exc:
        logger.error("Unexpected error: %s", exc)
        return {"error": "Internal server error"}
