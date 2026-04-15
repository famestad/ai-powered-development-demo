"""Schema for citizen conversation context.

Defines the data model that captures entities extracted from citizen
conversations (addresses, case numbers, names, etc.) and persists them
across turns so the agent never re-asks for information already provided.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class CitizenContext:
    """Accumulated context extracted from a citizen conversation.

    Fields are populated incrementally as the citizen provides information
    across multiple turns. None means the entity has not been mentioned yet.
    """

    citizen_name: Optional[str] = None
    address: Optional[str] = None
    case_number: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    issue_summary: Optional[str] = None
    additional_entities: Dict[str, str] = field(default_factory=dict)

    def merge(self, other: CitizenContext) -> None:
        """Merge newly extracted entities into this context.

        Only overwrites a field if the incoming value is not None,
        preserving previously captured information.
        """
        for fld in [
            "citizen_name",
            "address",
            "case_number",
            "phone_number",
            "email",
            "issue_summary",
        ]:
            incoming = getattr(other, fld)
            if incoming is not None:
                setattr(self, fld, incoming)
        self.additional_entities.update(other.additional_entities)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "citizen_name": self.citizen_name,
            "address": self.address,
            "case_number": self.case_number,
            "phone_number": self.phone_number,
            "email": self.email,
            "issue_summary": self.issue_summary,
            "additional_entities": self.additional_entities,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> CitizenContext:
        additional = data.get("additional_entities", {})
        return cls(
            citizen_name=data.get("citizen_name"),
            address=data.get("address"),
            case_number=data.get("case_number"),
            phone_number=data.get("phone_number"),
            email=data.get("email"),
            issue_summary=data.get("issue_summary"),
            additional_entities=additional if isinstance(additional, dict) else {},
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, raw: str) -> CitizenContext:
        try:
            return cls.from_dict(json.loads(raw))
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse CitizenContext JSON, returning empty context")
            return cls()

    def has_entities(self) -> bool:
        """Return True if at least one entity has been captured."""
        return any(
            v is not None
            for v in [
                self.citizen_name,
                self.address,
                self.case_number,
                self.phone_number,
                self.email,
                self.issue_summary,
            ]
        ) or bool(self.additional_entities)

    def summary_lines(self) -> List[str]:
        """Return a human-readable list of known facts for prompt injection."""
        lines: List[str] = []
        if self.citizen_name:
            lines.append(f"Name: {self.citizen_name}")
        if self.address:
            lines.append(f"Address: {self.address}")
        if self.case_number:
            lines.append(f"Case number: {self.case_number}")
        if self.phone_number:
            lines.append(f"Phone: {self.phone_number}")
        if self.email:
            lines.append(f"Email: {self.email}")
        if self.issue_summary:
            lines.append(f"Issue: {self.issue_summary}")
        for key, val in self.additional_entities.items():
            lines.append(f"{key}: {val}")
        return lines
