"""Unit tests for the outage lookup tool."""

from tools.outage_lookup.models import (
    AdvisoryType,
    OutageStatus,
    ServiceType,
)
from tools.outage_lookup.query import lookup_outages


class TestFilterByArea:
    """lookup_outages should return only outages in the requested area."""

    def test_returns_outages_for_riverside(self):
        results = lookup_outages("Riverside")
        assert len(results) > 0
        assert all(o.affected_area == "Riverside" for o in results)

    def test_area_filter_is_case_insensitive(self):
        results = lookup_outages("riverside")
        assert len(results) > 0
        assert all(o.affected_area == "Riverside" for o in results)

    def test_returns_outages_for_downtown(self):
        results = lookup_outages("Downtown")
        assert len(results) > 0
        assert all(o.affected_area == "Downtown" for o in results)


class TestFilterByServiceType:
    """lookup_outages should filter by service_type when provided."""

    def test_filter_water_in_riverside(self):
        results = lookup_outages("Riverside", service_type=ServiceType.WATER)
        assert len(results) >= 1
        assert all(o.service_type == ServiceType.WATER for o in results)

    def test_filter_power_in_downtown(self):
        results = lookup_outages("Downtown", service_type=ServiceType.POWER)
        assert len(results) >= 1
        assert all(o.service_type == ServiceType.POWER for o in results)

    def test_no_match_for_service_type(self):
        results = lookup_outages("Riverside", service_type=ServiceType.INTERNET)
        assert results == []


class TestIncludeScheduled:
    """lookup_outages should respect the include_scheduled flag."""

    def test_scheduled_included_by_default(self):
        results = lookup_outages("Riverside")
        statuses = {o.status for o in results}
        assert OutageStatus.SCHEDULED in statuses

    def test_exclude_scheduled(self):
        results = lookup_outages("Riverside", include_scheduled=False)
        assert all(o.status != OutageStatus.SCHEDULED for o in results)
        assert len(results) > 0

    def test_exclude_scheduled_downtown(self):
        all_results = lookup_outages("Downtown")
        filtered = lookup_outages("Downtown", include_scheduled=False)
        assert len(filtered) < len(all_results)
        assert all(o.status != OutageStatus.SCHEDULED for o in filtered)


class TestAdvisorySurfacing:
    """Outages with health advisories must be surfaced correctly."""

    def test_boil_water_advisory_present(self):
        results = lookup_outages("Riverside", service_type=ServiceType.WATER)
        advisories = [o for o in results if o.advisory_type == AdvisoryType.BOIL_WATER]
        assert len(advisories) >= 1

    def test_do_not_drink_advisory_present(self):
        results = lookup_outages("Industrial Park")
        advisories = [
            o for o in results if o.advisory_type == AdvisoryType.DO_NOT_DRINK
        ]
        assert len(advisories) >= 1

    def test_advisory_type_field_always_set(self):
        results = lookup_outages("Downtown")
        for outage in results:
            assert outage.advisory_type is not None


class TestEmptyResults:
    """lookup_outages should return an empty list when nothing matches."""

    def test_unknown_area(self):
        results = lookup_outages("Nonexistent Neighbourhood")
        assert results == []

    def test_known_area_wrong_service(self):
        results = lookup_outages("Oakwood Heights", service_type=ServiceType.GAS)
        assert results == []
