"""
Citizen context schema for civic services agents.

Defines the CitizenContext dataclass that holds known information about a
citizen across an ongoing case session. This context is loaded from the
memory wrapper (Issue #4) and injected into the agent system prompt so
the agent can use known details naturally without re-asking.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Optional


@dataclass
class CitizenContext:
    """Known context about a citizen gathered across conversation turns.

    All fields are optional — a new session starts with no context.
    Fields are populated incrementally as the citizen provides information.
    """

    name: Optional[str] = None
    address: Optional[str] = None
    case_number: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[str] = None
    service_type: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Return True if no context has been gathered yet."""
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name == "notes":
                if value:
                    return False
            elif value is not None:
                return False
        return True

    def to_prompt_block(self) -> str:
        """Format known context as a structured block for prompt injection.

        Returns an empty string if no context exists, so callers can
        simply check truthiness before appending.
        """
        if self.is_empty():
            return ""

        lines = ["Known citizen context:"]

        label_map = {
            "name": "Name",
            "address": "Address",
            "case_number": "Case #",
            "phone": "Phone",
            "email": "Email",
            "date_of_birth": "Date of Birth",
            "service_type": "Service Type",
        }

        for attr, label in label_map.items():
            value = getattr(self, attr)
            if value is not None:
                lines.append(f"  {label}: {value}")

        if self.notes:
            lines.append("  Notes:")
            for note in self.notes:
                lines.append(f"    - {note}")

        return "\n".join(lines)
