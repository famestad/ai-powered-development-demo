"""Unit tests for the license verification response formatter."""

from datetime import date

import pytest

from tools.license_verification.config import (
    ACTIVE_CLEAN_NOTE,
    ACTIVE_WITH_VIOLATIONS_NOTE,
    NOT_FOUND_MESSAGE,
    STATUS_LABELS,
    STATUS_WARNINGS,
    VIOLATION_SEVERITY_LABELS,
)
from tools.license_verification.formatter import (
    format_license_list_response,
    format_license_response,
    format_not_found_response,
)
from tools.license_verification.models import (
    License,
    LicenseStatus,
    Violation,
    ViolationSeverity,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_license(
    status: LicenseStatus = LicenseStatus.ACTIVE,
    violations: list[Violation] | None = None,
) -> License:
    """Build a License with sensible defaults for testing.

    Args:
        status: The license status to set.
        violations: Optional list of violations to attach.

    Returns:
        A License instance populated with test data.
    """
    return License(
        license_number="CTR-2024-00123",
        holder_name="Acme Construction LLC",
        license_type="General",
        status=status,
        expiration_date=date(2026, 12, 31),
        violations=violations or [],
    )


def _make_violation(
    severity: ViolationSeverity = ViolationSeverity.MINOR,
) -> Violation:
    """Build a Violation with sensible defaults for testing.

    Args:
        severity: The violation severity to set.

    Returns:
        A Violation instance populated with test data.
    """
    return Violation(
        description="Failure to display license on-site",
        severity=severity,
        date=date(2025, 6, 15),
    )


# ---------------------------------------------------------------------------
# Config completeness
# ---------------------------------------------------------------------------


class TestConfigCompleteness:
    """Verify that config dicts cover all enum members."""

    def test_status_labels_cover_all_statuses(self) -> None:
        """Every LicenseStatus must have a label in STATUS_LABELS."""
        for status in LicenseStatus:
            assert status in STATUS_LABELS, f"Missing label for {status}"

    def test_violation_severity_labels_cover_all_severities(self) -> None:
        """Every ViolationSeverity must have a label in VIOLATION_SEVERITY_LABELS."""
        for severity in ViolationSeverity:
            assert severity in VIOLATION_SEVERITY_LABELS, (
                f"Missing label for {severity}"
            )

    def test_non_active_statuses_have_warnings(self) -> None:
        """Every non-active status must have a warning in STATUS_WARNINGS."""
        non_active = [s for s in LicenseStatus if s != LicenseStatus.ACTIVE]
        for status in non_active:
            assert status in STATUS_WARNINGS, f"Missing warning for {status}"

    def test_active_status_has_no_warning(self) -> None:
        """Active status should not appear in STATUS_WARNINGS."""
        assert LicenseStatus.ACTIVE not in STATUS_WARNINGS


# ---------------------------------------------------------------------------
# Active license, no violations
# ---------------------------------------------------------------------------


class TestActiveLicenseNoViolations:
    """Tests for formatting an active license with a clean record."""

    def test_contains_license_details(self) -> None:
        """Response must include all core license fields."""
        result = format_license_response(_make_license())
        assert "CTR-2024-00123" in result
        assert "Acme Construction LLC" in result
        assert "General" in result
        assert "Active" in result
        assert "December 31, 2026" in result

    def test_contains_clean_note(self) -> None:
        """Response must include the active-clean framing note."""
        result = format_license_response(_make_license())
        assert ACTIVE_CLEAN_NOTE in result

    def test_does_not_contain_warning(self) -> None:
        """Response must not include any status warning banner."""
        result = format_license_response(_make_license())
        assert "⚠️" not in result

    def test_does_not_contain_violations_header(self) -> None:
        """Response must not include a violations section."""
        result = format_license_response(_make_license())
        assert "Violations on Record" not in result


# ---------------------------------------------------------------------------
# Active license, with violations
# ---------------------------------------------------------------------------


class TestActiveLicenseWithViolations:
    """Tests for formatting an active license that has violations on record."""

    def test_contains_violations_note(self) -> None:
        """Response must include the active-with-violations framing note."""
        violation = _make_violation()
        result = format_license_response(
            _make_license(violations=[violation])
        )
        assert ACTIVE_WITH_VIOLATIONS_NOTE in result

    def test_contains_violation_details(self) -> None:
        """Response must list each violation with severity and date."""
        violation = _make_violation(severity=ViolationSeverity.MODERATE)
        result = format_license_response(
            _make_license(violations=[violation])
        )
        assert "Moderate" in result
        assert "Failure to display license on-site" in result
        assert "June 15, 2025" in result

    def test_does_not_contain_warning(self) -> None:
        """Active licenses with violations should not show a warning banner."""
        violation = _make_violation()
        result = format_license_response(
            _make_license(violations=[violation])
        )
        assert "⚠️" not in result

    def test_multiple_violations(self) -> None:
        """All violations must appear in the response."""
        violations = [
            Violation(
                description="Failure to display license on-site",
                severity=ViolationSeverity.MINOR,
                date=date(2025, 3, 1),
            ),
            Violation(
                description="Work performed outside license scope",
                severity=ViolationSeverity.MAJOR,
                date=date(2025, 7, 20),
            ),
        ]
        result = format_license_response(
            _make_license(violations=violations)
        )
        assert "Failure to display license on-site" in result
        assert "Work performed outside license scope" in result
        assert "Minor" in result
        assert "Major" in result


# ---------------------------------------------------------------------------
# Expired license
# ---------------------------------------------------------------------------


class TestExpiredLicense:
    """Tests for formatting an expired license."""

    def test_leads_with_warning(self) -> None:
        """Response must start with the expired status warning."""
        result = format_license_response(
            _make_license(status=LicenseStatus.EXPIRED)
        )
        assert result.startswith("⚠️")
        assert "EXPIRED" in result

    def test_contains_expired_status_label(self) -> None:
        """The details block must show 'Expired' as the status."""
        result = format_license_response(
            _make_license(status=LicenseStatus.EXPIRED)
        )
        assert "**Status:** Expired" in result

    def test_warning_matches_config(self) -> None:
        """The warning text must match the configured STATUS_WARNINGS entry."""
        result = format_license_response(
            _make_license(status=LicenseStatus.EXPIRED)
        )
        assert STATUS_WARNINGS[LicenseStatus.EXPIRED] in result


# ---------------------------------------------------------------------------
# Suspended license
# ---------------------------------------------------------------------------


class TestSuspendedLicense:
    """Tests for formatting a suspended license."""

    def test_leads_with_warning(self) -> None:
        """Response must start with the suspended status warning."""
        result = format_license_response(
            _make_license(status=LicenseStatus.SUSPENDED)
        )
        assert result.startswith("⚠️")
        assert "SUSPENDED" in result

    def test_contains_suspended_status_label(self) -> None:
        """The details block must show 'Suspended' as the status."""
        result = format_license_response(
            _make_license(status=LicenseStatus.SUSPENDED)
        )
        assert "**Status:** Suspended" in result

    def test_warning_matches_config(self) -> None:
        """The warning text must match the configured STATUS_WARNINGS entry."""
        result = format_license_response(
            _make_license(status=LicenseStatus.SUSPENDED)
        )
        assert STATUS_WARNINGS[LicenseStatus.SUSPENDED] in result


# ---------------------------------------------------------------------------
# Revoked license
# ---------------------------------------------------------------------------


class TestRevokedLicense:
    """Tests for formatting a revoked license."""

    def test_leads_with_warning(self) -> None:
        """Response must start with the revoked status warning."""
        result = format_license_response(
            _make_license(status=LicenseStatus.REVOKED)
        )
        assert result.startswith("⚠️")
        assert "REVOKED" in result

    def test_contains_revoked_status_label(self) -> None:
        """The details block must show 'Revoked' as the status."""
        result = format_license_response(
            _make_license(status=LicenseStatus.REVOKED)
        )
        assert "**Status:** Revoked" in result

    def test_warning_matches_config(self) -> None:
        """The warning text must match the configured STATUS_WARNINGS entry."""
        result = format_license_response(
            _make_license(status=LicenseStatus.REVOKED)
        )
        assert STATUS_WARNINGS[LicenseStatus.REVOKED] in result


# ---------------------------------------------------------------------------
# Not-found response
# ---------------------------------------------------------------------------


class TestNotFoundResponse:
    """Tests for the no-match / not-found response."""

    def test_format_not_found_returns_configured_message(self) -> None:
        """format_not_found_response must return the NOT_FOUND_MESSAGE."""
        assert format_not_found_response() == NOT_FOUND_MESSAGE

    def test_empty_list_returns_not_found(self) -> None:
        """An empty license list must produce the not-found message."""
        assert format_license_list_response(licenses=[]) == NOT_FOUND_MESSAGE

    def test_not_found_mentions_licensing_division(self) -> None:
        """The not-found message should direct citizens to the Licensing Division."""
        assert "Licensing Division" in format_not_found_response()


# ---------------------------------------------------------------------------
# List formatter
# ---------------------------------------------------------------------------


class TestListFormatter:
    """Tests for formatting multiple license results."""

    def test_single_license_no_divider(self) -> None:
        """A single-element list should not contain a divider."""
        result = format_license_list_response(licenses=[_make_license()])
        assert "---" not in result

    def test_single_license_matches_single_format(self) -> None:
        """A single-element list should match format_license_response output."""
        lic = _make_license()
        assert format_license_list_response(licenses=[lic]) == format_license_response(lic)

    def test_multiple_licenses_separated_by_divider(self) -> None:
        """Multiple licenses must be separated by a divider."""
        licenses = [_make_license(), _make_license(status=LicenseStatus.EXPIRED)]
        result = format_license_list_response(licenses=licenses)
        assert "---" in result

    def test_multiple_licenses_contain_all_records(self) -> None:
        """All license records must appear in the response."""
        lic_a = License(
            license_number="CTR-2024-00001",
            holder_name="Alpha Builders",
            license_type="Electrical",
            status=LicenseStatus.ACTIVE,
            expiration_date=date(2026, 6, 30),
        )
        lic_b = License(
            license_number="CTR-2024-00002",
            holder_name="Beta Plumbing",
            license_type="Plumbing",
            status=LicenseStatus.SUSPENDED,
            expiration_date=date(2025, 1, 15),
        )
        result = format_license_list_response(licenses=[lic_a, lic_b])
        assert "CTR-2024-00001" in result
        assert "Alpha Builders" in result
        assert "CTR-2024-00002" in result
        assert "Beta Plumbing" in result


# ---------------------------------------------------------------------------
# Non-active license with violations
# ---------------------------------------------------------------------------


class TestNonActiveLicenseWithViolations:
    """Tests for non-active licenses that also have violations."""

    @pytest.mark.parametrize("status", [
        LicenseStatus.EXPIRED,
        LicenseStatus.SUSPENDED,
        LicenseStatus.REVOKED,
    ])
    def test_shows_warning_and_violations(self, status: LicenseStatus) -> None:
        """Non-active licenses with violations should show both warning and violations."""
        violation = _make_violation(severity=ViolationSeverity.MAJOR)
        result = format_license_response(
            _make_license(status=status, violations=[violation])
        )
        assert "⚠️" in result
        assert "Violations on Record" in result
        assert "Major" in result

    @pytest.mark.parametrize("status", [
        LicenseStatus.EXPIRED,
        LicenseStatus.SUSPENDED,
        LicenseStatus.REVOKED,
    ])
    def test_does_not_show_active_violations_note(self, status: LicenseStatus) -> None:
        """Non-active licenses should not show the active-with-violations framing."""
        violation = _make_violation()
        result = format_license_response(
            _make_license(status=status, violations=[violation])
        )
        assert ACTIVE_WITH_VIOLATIONS_NOTE not in result
