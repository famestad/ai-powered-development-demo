# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Entity extraction utilities for citizen conversations.

Extracts structured entities (name, address, case number, account number,
service type) from a single conversation turn. Uses two complementary
strategies:

1. **Regex extraction** — fast, deterministic matching for well-structured
   identifiers such as case numbers (CR-YYYY-NNNN), account numbers, and
   ZIP codes.

2. **LLM-based extraction** — uses Bedrock Converse with tool_use /
   function calling to parse natural language into the CitizenContext schema.
   Designed to integrate with the Strands SDK's model invocation so no
   separate LLM call is needed when running inside an agent.

The two strategies are combined: regex results are overlaid on LLM results
so that deterministic matches take precedence for structured identifiers.
"""

import logging
import re
from typing import Any, Optional

import boto3

from citizen_memory.models import Address, CitizenContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Regex patterns for well-structured identifiers
# ---------------------------------------------------------------------------

# Case number: letters followed by dash, 4-digit year, dash, digits
# Examples: CR-2024-0456, REF-2025-12345, CASE-2023-001
CASE_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    r"\b([A-Z]{2,5}-\d{4}-\d{3,6})\b",
    re.IGNORECASE,
)

# Account number: "account" keyword followed by a number with optional dashes
# Examples: "account number 12345678", "account #12-345-678"
ACCOUNT_NUMBER_PATTERN: re.Pattern[str] = re.compile(
    r"account\s*(?:number|num|no|#|:)?\s*[#:]?\s*(\d[\d\-]{4,})",
    re.IGNORECASE,
)

# ZIP code: 5 digits, optionally followed by dash and 4 digits
# Examples: "62704", "90210-1234"
ZIP_CODE_PATTERN: re.Pattern[str] = re.compile(
    r"\b(\d{5}(?:-\d{4})?)\b",
)


# ---------------------------------------------------------------------------
# Tool definition for Bedrock Converse tool_use extraction
# ---------------------------------------------------------------------------

# This tool spec is sent to Bedrock Converse so the model returns structured
# JSON matching our CitizenContext schema. The model "calls" this tool with
# the extracted fields, and we parse the tool input as entity data.
ENTITY_EXTRACTION_TOOL_SPEC: dict[str, Any] = {
    "toolSpec": {
        "name": "extract_citizen_entities",
        "description": (
            "Extract structured citizen information from the conversation text. "
            "Only include fields that are explicitly mentioned in the text. "
            "Leave out any fields that are not clearly stated."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "citizen_name": {
                        "type": "string",
                        "description": "Full name of the citizen if mentioned",
                    },
                    "street": {
                        "type": "string",
                        "description": "Street address if mentioned, e.g. '123 Main St'",
                    },
                    "city": {
                        "type": "string",
                        "description": "City name if mentioned",
                    },
                    "zip_code": {
                        "type": "string",
                        "description": "ZIP or postal code if mentioned",
                    },
                    "case_number": {
                        "type": "string",
                        "description": "Case or reference number if mentioned, e.g. 'CR-2024-0456'",
                    },
                    "reference_number": {
                        "type": "string",
                        "description": "Alternate reference identifier if mentioned",
                    },
                    "account_number": {
                        "type": "string",
                        "description": "Account or utility number if mentioned",
                    },
                    "service_type": {
                        "type": "string",
                        "description": "Type of municipal service if mentioned (e.g. water, trash, building permit)",
                    },
                },
                "required": [],
            }
        },
    }
}


def extract_entities_with_regex(text: str) -> CitizenContext:
    """Extract entities from text using regex patterns only.

    This is a fast, deterministic extraction pass that identifies
    well-structured identifiers without calling an LLM. It handles:
    - Case numbers matching the CR-YYYY-NNNN pattern
    - Account numbers following the "account" keyword
    - ZIP codes (5-digit or 5+4 format)

    Args:
        text: A single conversation turn from the citizen.

    Returns:
        A CitizenContext with only the regex-matched fields populated.
        Fields not found in the text are left as None.
    """
    result_fields: dict[str, Any] = {}

    # Extract case number
    case_match = CASE_NUMBER_PATTERN.search(text)
    if case_match:
        result_fields["case_number"] = case_match.group(1).upper()

    # Extract account number
    account_match = ACCOUNT_NUMBER_PATTERN.search(text)
    if account_match:
        result_fields["account_number"] = account_match.group(1)

    # Extract ZIP code — only store if it looks like a standalone ZIP,
    # not part of a longer number that was already captured
    zip_match = ZIP_CODE_PATTERN.search(text)
    if zip_match:
        zip_value = zip_match.group(1)
        # Avoid false positives: don't flag the ZIP if it was already
        # captured as part of a case or account number
        already_captured = False
        if case_match and zip_value in case_match.group(0):
            already_captured = True
        if account_match and zip_value in account_match.group(0):
            already_captured = True
        if not already_captured:
            result_fields["address"] = Address(zip_code=zip_value)

    return CitizenContext(**result_fields)


def _parse_tool_use_response(tool_input: dict[str, Any]) -> CitizenContext:
    """Parse the tool_use response from Bedrock Converse into a CitizenContext.

    Converts the flat tool input JSON (which has street, city, zip_code at the
    top level) into the nested CitizenContext model (which nests them under address).

    Args:
        tool_input: The JSON input from the model's tool_use call. Contains
            flat keys like "citizen_name", "street", "city", "zip_code", etc.

    Returns:
        A CitizenContext populated with the fields the model extracted.

    Raises:
        ValidationError: If the tool input contains values that fail
            Pydantic validation on the CitizenContext model.
    """
    context_fields: dict[str, Any] = {}

    # Build nested Address if any address components are present
    address_parts: dict[str, str] = {}
    for address_key in ("street", "city", "zip_code"):
        value = tool_input.get(address_key)
        if value:
            address_parts[address_key] = value

    if address_parts:
        context_fields["address"] = Address(**address_parts)

    # Copy non-address fields directly
    for field_name in ("citizen_name", "case_number", "reference_number",
                       "account_number", "service_type"):
        value = tool_input.get(field_name)
        if value:
            context_fields[field_name] = value

    return CitizenContext(**context_fields)


def extract_entities_with_llm(
    text: str,
    model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region: Optional[str] = None,
) -> CitizenContext:
    """Extract entities from a conversation turn using Bedrock Converse tool_use.

    Sends the conversation text to Bedrock Converse with a tool definition
    matching the CitizenContext schema. The model is forced to call the
    extraction tool (via toolChoice=any), returning structured JSON that
    is parsed into a CitizenContext.

    This function makes a direct Bedrock Converse API call. When running
    inside a Strands agent, prefer using extract_entities() which combines
    regex and LLM extraction, or integrate the ENTITY_EXTRACTION_TOOL_SPEC
    into the agent's tool list to avoid a separate LLM call.

    Args:
        text: A single conversation turn from the citizen.
        model_id: Bedrock model ID to use for extraction. Defaults to
            Claude Sonnet.
        region: AWS region for the Bedrock client. Defaults to us-east-1.

    Returns:
        A CitizenContext with fields extracted by the LLM. Fields not
        mentioned in the text are left as None.

    Raises:
        ClientError: If the Bedrock Converse API call fails.
        ValidationError: If the model returns data that fails Pydantic
            validation.
    """
    if region is None:
        region = "us-east-1"

    # Create Bedrock Runtime client for the Converse API
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=region,
    )

    # System prompt instructs the model to extract entities only —
    # no chit-chat, no hallucinated values.
    system_prompt = (
        "You are an entity extraction assistant. Your ONLY job is to identify "
        "structured information from the citizen's message and call the "
        "extract_citizen_entities tool with the values you find. "
        "Only extract values that are explicitly stated in the text. "
        "Do NOT guess or infer values that are not clearly present. "
        "If no entities are found, call the tool with an empty object."
    )

    response = bedrock_client.converse(
        modelId=model_id,
        system=[{"text": system_prompt}],
        messages=[
            {
                "role": "user",
                "content": [{"text": text}],
            }
        ],
        toolConfig={
            "tools": [ENTITY_EXTRACTION_TOOL_SPEC],
            # Force the model to use the extraction tool
            "toolChoice": {"any": {}},
        },
    )

    # Parse the tool_use block from the response
    output_content = response.get("output", {}).get("message", {}).get("content", [])
    for block in output_content:
        if "toolUse" in block:
            tool_input = block["toolUse"].get("input", {})
            return _parse_tool_use_response(tool_input=tool_input)

    # If no tool_use block was returned (unexpected), return empty context
    logger.warning(
        "Bedrock Converse did not return a tool_use block for text: %s",
        text[:100],
    )
    return CitizenContext()


def merge_context(
    existing: CitizenContext,
    update: CitizenContext,
) -> CitizenContext:
    """Merge an update into the existing citizen context.

    Implements the correction/overwrite strategy: non-None fields in the
    update overwrite the corresponding fields in the existing context.
    None fields in the update are left unchanged, preserving previously
    extracted values.

    For the nested Address field, merging is done at the sub-field level
    so that updating just the ZIP code does not erase a previously
    extracted street address.

    Args:
        existing: The current accumulated CitizenContext.
        update: A partial CitizenContext from the latest conversation turn.

    Returns:
        A new CitizenContext with the merged result.
    """
    merged_data: dict[str, Any] = existing.model_dump()

    update_data = update.model_dump(exclude_none=True)

    # Handle address merging at the sub-field level
    if "address" in update_data and update_data["address"] is not None:
        existing_address = merged_data.get("address") or {}
        updated_address = update_data.pop("address")
        # Only overwrite sub-fields that are present in the update
        for key, value in updated_address.items():
            if value is not None:
                existing_address[key] = value
        merged_data["address"] = existing_address

    # Overwrite top-level fields
    for key, value in update_data.items():
        merged_data[key] = value

    return CitizenContext(**merged_data)


def extract_entities(
    text: str,
    use_llm: bool = True,
    model_id: str = "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    region: Optional[str] = None,
) -> CitizenContext:
    """Extract structured entities from a single conversation turn.

    Combines regex-based and LLM-based extraction strategies. Regex
    results take precedence for well-structured identifiers (case numbers,
    account numbers, ZIP codes) since they are deterministic and fast.
    LLM results fill in natural-language entities (name, service type,
    address text).

    Args:
        text: A single conversation turn from the citizen.
        use_llm: Whether to invoke the Bedrock Converse LLM for
            natural-language extraction. Set to False for regex-only
            extraction (useful in tests or when LLM is unavailable).
        model_id: Bedrock model ID for LLM extraction. Defaults to
            Claude Sonnet.
        region: AWS region for the Bedrock client. Defaults to us-east-1.

    Returns:
        A CitizenContext with extracted fields. Fields not mentioned in
        the text are left as None.
    """
    # Step 1: Regex extraction (always runs — fast and deterministic)
    regex_result = extract_entities_with_regex(text=text)

    if not use_llm:
        return regex_result

    # Step 2: LLM-based extraction
    try:
        llm_result = extract_entities_with_llm(
            text=text,
            model_id=model_id,
            region=region,
        )
    except Exception:
        logger.exception("LLM extraction failed, falling back to regex-only results")
        return regex_result

    # Step 3: Merge — LLM provides the base, regex overwrites for
    # structured identifiers (regex is more reliable for those patterns)
    return merge_context(existing=llm_result, update=regex_result)
