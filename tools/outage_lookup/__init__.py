"""Outage lookup tool — data model, mock data, and query function."""

from tools.outage_lookup.models import AdvisoryType, Outage, OutageStatus, ServiceType
from tools.outage_lookup.query import lookup_outages

__all__ = [
    "AdvisoryType",
    "Outage",
    "OutageStatus",
    "ServiceType",
    "lookup_outages",
]
