"""Entity extraction from citizen messages.

Uses regex patterns to pull structured entities (addresses, case numbers,
phone numbers, emails, names) from free-text citizen messages. This is a
lightweight, deterministic approach that avoids an extra LLM call per turn.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, Optional

from .schema import CitizenContext

logger = logging.getLogger(__name__)

# Regex patterns for entity extraction
_CASE_NUMBER_RE = re.compile(
    r"(?:case|ticket|ref(?:erence)?|incident)[\s#:]*([A-Z]{0,4}\d{4,10})",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?:phone|cell|mobile|tel|call me at|reach me at)[\s:]*"
    r"(\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(
    r"(?:email|e-mail|mail|reach me at|contact me at)[\s:]*"
    r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)",
    re.IGNORECASE,
)
# Standalone email (without keyword prefix)
_STANDALONE_EMAIL_RE = re.compile(
    r"\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b"
)
_ADDRESS_RE = re.compile(
    r"(?:address|live at|located at|at|street|my address is)[\s:]*"
    r"(\d+\s+[A-Za-z0-9\s.,]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Way|Place|Pl|Circle|Cir)[.,]?\s*"
    r"(?:[A-Za-z\s]+,?\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)?)",
    re.IGNORECASE,
)
_NAME_RE = re.compile(
    r"(?:my name is|I'm|I am|this is|name:)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
    re.IGNORECASE,
)


def extract_entities(message: str) -> CitizenContext:
    """Extract entities from a citizen message into a CitizenContext.

    Returns a CitizenContext with only the fields that were found in this
    message. Fields that were not mentioned will be None.
    """
    ctx = CitizenContext()
    additional: Dict[str, str] = {}

    # Case number
    match = _CASE_NUMBER_RE.search(message)
    if match:
        ctx.case_number = match.group(1).strip()
        logger.debug("Extracted case_number: %s", ctx.case_number)

    # Phone
    match = _PHONE_RE.search(message)
    if match:
        ctx.phone_number = match.group(1).strip()
        logger.debug("Extracted phone_number: %s", ctx.phone_number)

    # Email (keyword-prefixed first, then standalone)
    match = _EMAIL_RE.search(message)
    if match:
        ctx.email = match.group(1).strip()
    else:
        match = _STANDALONE_EMAIL_RE.search(message)
        if match:
            ctx.email = match.group(1).strip()
    if ctx.email:
        logger.debug("Extracted email: %s", ctx.email)

    # Address
    match = _ADDRESS_RE.search(message)
    if match:
        ctx.address = match.group(1).strip().rstrip(",.")
        logger.debug("Extracted address: %s", ctx.address)

    # Name
    match = _NAME_RE.search(message)
    if match:
        ctx.citizen_name = match.group(1).strip()
        logger.debug("Extracted citizen_name: %s", ctx.citizen_name)

    ctx.additional_entities = additional
    return ctx
