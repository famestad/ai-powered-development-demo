"""Query function for filtering the outage dataset."""

from tools.outage_lookup.mock_data import OUTAGES
from tools.outage_lookup.models import Outage, OutageStatus, ServiceType


def lookup_outages(
    area: str,
    service_type: ServiceType | None = None,
    include_scheduled: bool = True,
) -> list[Outage]:
    """Return outages matching the given filters.

    Args:
        area: Neighbourhood or district to search (case-insensitive).
        service_type: Optional service filter (water/power/gas/internet).
        include_scheduled: When False, exclude outages with status "scheduled".

    Returns:
        List of matching Outage records.
    """
    results: list[Outage] = []
    area_lower = area.lower()

    for outage in OUTAGES:
        if outage.affected_area.lower() != area_lower:
            continue
        if service_type is not None and outage.service_type != service_type:
            continue
        if not include_scheduled and outage.status == OutageStatus.SCHEDULED:
            continue
        results.append(outage)

    return results
