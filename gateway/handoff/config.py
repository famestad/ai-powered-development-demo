"""Configuration for the handoff orchestrator.

Provides Pydantic models for business hours, SLA timers, and always-escalate
topic lists. Configuration can be loaded from YAML files or environment
variables.
"""

from __future__ import annotations

import os
from datetime import time
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class BusinessHoursConfig(BaseModel):
    """Defines when human agents are available for warm handoff."""

    start: time = Field(
        default=time(8, 0),
        description="Start of business hours (local time).",
    )
    end: time = Field(
        default=time(17, 0),
        description="End of business hours (local time).",
    )
    days: list[int] = Field(
        default=[0, 1, 2, 3, 4],
        description="Days of the week when agents are available (0=Mon, 6=Sun).",
    )
    timezone: str = Field(
        default="America/Chicago",
        description="IANA timezone for business hours.",
    )


class SLAConfig(BaseModel):
    """SLA timers for handoff flows."""

    warm_handoff_timeout_seconds: int = Field(
        default=120,
        description=(
            "Seconds to wait for a warm handoff connection before "
            "falling back to callback."
        ),
    )
    callback_response_hours: int = Field(
        default=4,
        description="Target hours for a callback response.",
    )
    ticket_response_hours: int = Field(
        default=24,
        description="Target hours for a ticket response.",
    )
    warm_handoff_estimated_wait_minutes: int = Field(
        default=5,
        description="Estimated wait time shown to citizens for warm handoff.",
    )


class HandoffConfig(BaseModel):
    """Top-level handoff orchestrator configuration."""

    always_escalate_topics: list[str] = Field(
        default=[
            "discrimination",
            "harassment",
            "personal_safety",
            "emergency",
            "ada_accommodation",
            "whistleblower",
        ],
        description=(
            "Topic categories that always trigger handoff regardless of "
            "confidence thresholds."
        ),
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum classifier confidence to trigger handoff for "
            "non-always-escalate topics."
        ),
    )
    business_hours: BusinessHoursConfig = Field(
        default_factory=BusinessHoursConfig,
        description="Business hours for warm handoff availability.",
    )
    sla: SLAConfig = Field(
        default_factory=SLAConfig,
        description="SLA timers for handoff flows.",
    )


def load_config(config_path: str | Path | None = None) -> HandoffConfig:
    """Load handoff configuration from a YAML file or environment variable.

    Resolution order:
    1. Explicit ``config_path`` argument
    2. ``HANDOFF_CONFIG_PATH`` environment variable
    3. Default configuration values

    Args:
        config_path: Optional path to a YAML configuration file.

    Returns:
        A validated HandoffConfig instance.
    """
    path = config_path or os.environ.get("HANDOFF_CONFIG_PATH")

    if path is not None:
        resolved = Path(path)
        if resolved.is_file():
            raw: dict[str, Any] = yaml.safe_load(resolved.read_text()) or {}
            return HandoffConfig.model_validate(raw)

    return HandoffConfig()
