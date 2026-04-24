"""Unit tests for the tools.contractor_license module."""

import pytest

from tools.contractor_license.data import LICENSES
from tools.contractor_license.lookup import verify_contractor_license
from tools.contractor_license.models import License, LicenseStatus, Violation


# ---------------------------------------------------------------------------
# Model and data completeness
# ---------------------------------------------------------------------------

ALL_STATUSES = [
    LicenseStatus.ACTIVE,
    LicenseStatus.EXPIRED,
    LicenseStatus.SUSPENDED,
    LicenseStatus.REVOKED,
]


class TestDataCompleteness:
    """Verify the mock dataset meets acceptance criteria."""

    @pytest.mark.parametrize("status", ALL_STATUSES)
    def test_at_least_one_license_per_status(self, status):
        matches = [lic for lic in LICENSES if lic.status == status]
        assert len(matches) >= 1, f"No license with status {status.value}"

    def test_multiple_trades_represented(self):
        trades = {lic.trade for lic in LICENSES}
        assert len(trades) >= 3, f"Only {len(trades)} trades: {trades}"

    def test_at_least_one_license_with_no_violations(self):
        assert any(len(lic.violations) == 0 for lic in LICENSES)

    def test_at_least_one_license_with_multiple_violations(self):
        assert any(len(lic.violations) > 1 for lic in LICENSES)

    def test_all_entries_are_license_instances(self):
        for lic in LICENSES:
            assert isinstance(lic, License)

    def test_violations_are_violation_instances(self):
        for lic in LICENSES:
            for v in lic.violations:
                assert isinstance(v, Violation)


# ---------------------------------------------------------------------------
# Lookup by license number
# ---------------------------------------------------------------------------


class TestLookupByLicenseNumber:
    """verify_contractor_license(license_number=...) behavior."""

    def test_exact_match_returns_license(self):
        result = verify_contractor_license(license_number="ML-2024-0451")
        assert isinstance(result, License)
        assert result.license_number == "ML-2024-0451"
        assert result.contractor_name == "Rivera Electric LLC"

    def test_miss_returns_none(self):
        result = verify_contractor_license(license_number="ML-0000-0000")
        assert result is None

    @pytest.mark.parametrize("status", ALL_STATUSES)
    def test_can_find_license_in_each_status(self, status):
        target = next(lic for lic in LICENSES if lic.status == status)
        result = verify_contractor_license(license_number=target.license_number)
        assert result is not None
        assert result.status == status


# ---------------------------------------------------------------------------
# Lookup by contractor name
# ---------------------------------------------------------------------------


class TestLookupByContractorName:
    """verify_contractor_license(contractor_name=...) behavior."""

    def test_single_match(self):
        results = verify_contractor_license(contractor_name="Rivera Electric")
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].contractor_name == "Rivera Electric LLC"

    def test_multiple_matches(self):
        results = verify_contractor_license(contractor_name="Nguyen")
        assert isinstance(results, list)
        assert len(results) == 2

    def test_no_match_returns_empty_list(self):
        results = verify_contractor_license(contractor_name="Nonexistent Corp")
        assert isinstance(results, list)
        assert len(results) == 0

    def test_case_insensitive(self):
        results = verify_contractor_license(contractor_name="rivera electric")
        assert len(results) == 1


# ---------------------------------------------------------------------------
# Lookup by name + trade narrowing
# ---------------------------------------------------------------------------


class TestLookupByNameAndTrade:
    """verify_contractor_license(contractor_name=..., trade=...) behavior."""

    def test_name_and_trade_narrows_results(self):
        results = verify_contractor_license(
            contractor_name="Nguyen", trade="plumbing"
        )
        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0].trade == "plumbing"

    def test_name_and_trade_no_overlap(self):
        results = verify_contractor_license(
            contractor_name="Rivera", trade="plumbing"
        )
        assert isinstance(results, list)
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Lookup by trade only
# ---------------------------------------------------------------------------


class TestLookupByTrade:
    """verify_contractor_license(trade=...) behavior."""

    def test_trade_only(self):
        results = verify_contractor_license(trade="electrical")
        assert isinstance(results, list)
        assert len(results) >= 2
        assert all(lic.trade == "electrical" for lic in results)

    def test_trade_case_insensitive(self):
        results = verify_contractor_license(trade="PLUMBING")
        assert len(results) >= 1

    def test_trade_no_match(self):
        results = verify_contractor_license(trade="roofing")
        assert isinstance(results, list)
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Edge: no arguments
# ---------------------------------------------------------------------------


class TestNoArguments:
    """verify_contractor_license() with no arguments."""

    def test_returns_all_licenses(self):
        results = verify_contractor_license()
        assert isinstance(results, list)
        assert len(results) == len(LICENSES)
