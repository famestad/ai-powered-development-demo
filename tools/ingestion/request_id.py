from __future__ import annotations

import uuid
from datetime import datetime, timezone


def generate_request_id() -> str:
    datestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    unique = uuid.uuid4().hex[:12]
    return f"ING-{datestamp}-{unique}"
