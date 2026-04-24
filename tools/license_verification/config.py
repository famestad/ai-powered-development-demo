"""Config-driven messages for license status and violation severity.

All citizen-facing wording for license verification responses is centralized
here so that language can be tuned without changing formatter or caller code.
"""

from tools.license_verification.models import LicenseStatus, ViolationSeverity

# -- Status display config ---------------------------------------------------

STATUS_WARNINGS: dict[LicenseStatus, str] = {
    LicenseStatus.EXPIRED: (
        "⚠️ This license is EXPIRED. The contractor is not currently "
        "authorized to perform work under this license."
    ),
    LicenseStatus.SUSPENDED: (
        "⚠️ This license is SUSPENDED. The contractor is not currently "
        "authorized to perform work under this license pending further review."
    ),
    LicenseStatus.REVOKED: (
        "⚠️ This license has been REVOKED. The contractor is no longer "
        "authorized to perform work under this license."
    ),
}
"""Warning banners shown when a license is not active.

Active licenses do not receive a warning banner.
"""

STATUS_LABELS: dict[LicenseStatus, str] = {
    LicenseStatus.ACTIVE: "Active",
    LicenseStatus.EXPIRED: "Expired",
    LicenseStatus.SUSPENDED: "Suspended",
    LicenseStatus.REVOKED: "Revoked",
}
"""Human-readable labels for each license status."""

# -- Violation severity display config ----------------------------------------

VIOLATION_SEVERITY_LABELS: dict[ViolationSeverity, str] = {
    ViolationSeverity.MINOR: "Minor",
    ViolationSeverity.MODERATE: "Moderate",
    ViolationSeverity.MAJOR: "Major",
}
"""Human-readable labels for violation severity levels."""

# -- Contextual framing messages ----------------------------------------------

ACTIVE_WITH_VIOLATIONS_NOTE: str = (
    "This license is currently active. However, the following "
    "violation(s) are on record. This information is provided for "
    "transparency and does not necessarily affect the license status."
)
"""Framing text shown when an active license has violations on record."""

ACTIVE_CLEAN_NOTE: str = (
    "This license is currently active with no violations on record."
)
"""Framing text shown when an active license has no violations."""

NOT_FOUND_MESSAGE: str = (
    "No contractor license was found matching your search. Please "
    "double-check the license number or contractor name and try again. "
    "If you need further assistance, contact the Maplewood Licensing "
    "Division at (555) 555-0140."
)
"""Message shown when no license matches the lookup."""
