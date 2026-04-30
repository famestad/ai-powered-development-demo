"""Extract API Lambda Handler — POST /extract/front."""

from __future__ import annotations

import os

from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.event_handler import (
    APIGatewayRestResolver,
    CORSConfig,
    Response,
)
from aws_lambda_powertools.logging.correlation_paths import API_GATEWAY_REST
from aws_lambda_powertools.utilities.typing import LambdaContext

CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "*")

cors_origins = [
    origin.strip() for origin in CORS_ALLOWED_ORIGINS.split(",") if origin.strip()
]
primary_origin = cors_origins[0] if cors_origins else "*"
extra_origins = cors_origins[1:] if len(cors_origins) > 1 else None

cors_config = CORSConfig(
    allow_origin=primary_origin,
    extra_origins=extra_origins,
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)

tracer = Tracer()
logger = Logger()
app = APIGatewayRestResolver(cors=cors_config)


@app.post("/extract/front")
def extract_front() -> Response:
    """POST /extract/front — run synchronous front-of-license extraction."""
    from gateway.extraction.handler import handle_extract_front

    state_hint = app.current_event.get_query_string_value("state_hint")

    body = app.current_event.json_body or {}

    result, status = handle_extract_front(body, state_hint=state_hint)

    return Response(
        status_code=status,
        content_type="application/json",
        body=result,
    )


@logger.inject_lambda_context(correlation_id_path=API_GATEWAY_REST)
def handler(event: dict, context: LambdaContext) -> dict:
    return app.resolve(event, context)
