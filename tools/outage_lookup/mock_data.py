"""Mock outage dataset for the City of Maplewood demo."""

from datetime import datetime, timezone

from tools.outage_lookup.models import (
    AdvisoryType,
    Outage,
    OutageStatus,
    ServiceType,
)

OUTAGES: list[Outage] = [
    # Active water main break with boil-water advisory
    Outage(
        id="OUT-001",
        service_type=ServiceType.WATER,
        status=OutageStatus.ACTIVE,
        affected_area="Riverside",
        start_time=datetime(2026, 4, 21, 6, 30, tzinfo=timezone.utc),
        estimated_restoration=datetime(2026, 4, 22, 18, 0, tzinfo=timezone.utc),
        cause="Water main break at Riverside Blvd and 3rd Ave",
        advisory_type=AdvisoryType.BOIL_WATER,
    ),
    # Active power outage
    Outage(
        id="OUT-002",
        service_type=ServiceType.POWER,
        status=OutageStatus.ACTIVE,
        affected_area="Downtown",
        start_time=datetime(2026, 4, 22, 2, 15, tzinfo=timezone.utc),
        estimated_restoration=datetime(2026, 4, 22, 14, 0, tzinfo=timezone.utc),
        cause="Transformer failure at Main St substation",
        advisory_type=AdvisoryType.NONE,
    ),
    # Scheduled gas maintenance
    Outage(
        id="OUT-003",
        service_type=ServiceType.GAS,
        status=OutageStatus.SCHEDULED,
        affected_area="Riverside",
        start_time=datetime(2026, 4, 25, 8, 0, tzinfo=timezone.utc),
        estimated_restoration=datetime(2026, 4, 25, 17, 0, tzinfo=timezone.utc),
        cause="Planned gas line inspection and valve replacement",
        advisory_type=AdvisoryType.NONE,
    ),
    # Resolved internet outage
    Outage(
        id="OUT-004",
        service_type=ServiceType.INTERNET,
        status=OutageStatus.RESOLVED,
        affected_area="Oakwood Heights",
        start_time=datetime(2026, 4, 19, 14, 0, tzinfo=timezone.utc),
        estimated_restoration=datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        cause="Fiber optic cable cut during road construction",
        advisory_type=AdvisoryType.NONE,
    ),
    # Scheduled power maintenance in Downtown
    Outage(
        id="OUT-005",
        service_type=ServiceType.POWER,
        status=OutageStatus.SCHEDULED,
        affected_area="Downtown",
        start_time=datetime(2026, 4, 26, 22, 0, tzinfo=timezone.utc),
        estimated_restoration=datetime(2026, 4, 27, 6, 0, tzinfo=timezone.utc),
        cause="Electrical grid upgrade — overnight rolling maintenance",
        advisory_type=AdvisoryType.NONE,
    ),
    # Active water contamination with do-not-drink advisory
    Outage(
        id="OUT-006",
        service_type=ServiceType.WATER,
        status=OutageStatus.ACTIVE,
        affected_area="Industrial Park",
        start_time=datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc),
        estimated_restoration=None,
        cause="Chemical spill detected near water treatment intake",
        advisory_type=AdvisoryType.DO_NOT_DRINK,
    ),
    # Resolved power outage in Riverside
    Outage(
        id="OUT-007",
        service_type=ServiceType.POWER,
        status=OutageStatus.RESOLVED,
        affected_area="Riverside",
        start_time=datetime(2026, 4, 18, 16, 0, tzinfo=timezone.utc),
        estimated_restoration=datetime(2026, 4, 18, 20, 0, tzinfo=timezone.utc),
        cause="Downed power line due to severe weather",
        advisory_type=AdvisoryType.NONE,
    ),
]
