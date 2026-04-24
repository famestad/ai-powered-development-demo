"""Mock contractor license dataset for the City of Maplewood."""

from datetime import date

from tools.contractor_license.models import License, LicenseStatus, Violation

LICENSES: list[License] = [
    # Active — electrical, no violations
    License(
        license_number="ML-2024-0451",
        contractor_name="Rivera Electric LLC",
        trade="electrical",
        status=LicenseStatus.ACTIVE,
        issue_date=date(2024, 3, 15),
        expiration_date=date(2026, 3, 15),
        violations=[],
    ),
    # Active — plumbing, one violation (resolved)
    License(
        license_number="ML-2023-0287",
        contractor_name="Nguyen Plumbing & Heating",
        trade="plumbing",
        status=LicenseStatus.ACTIVE,
        issue_date=date(2023, 6, 1),
        expiration_date=date(2025, 6, 1),
        violations=[
            Violation(
                date=date(2024, 1, 18),
                type="permit_violation",
                description="Work commenced before permit was approved.",
                resolution_status="resolved",
            ),
        ],
    ),
    # Expired — general, no violations
    License(
        license_number="ML-2021-0102",
        contractor_name="Oakdale Builders Inc.",
        trade="general",
        status=LicenseStatus.EXPIRED,
        issue_date=date(2021, 9, 10),
        expiration_date=date(2023, 9, 10),
        violations=[],
    ),
    # Suspended — electrical, multiple violations
    License(
        license_number="ML-2022-0389",
        contractor_name="Briggs & Son Electrical",
        trade="electrical",
        status=LicenseStatus.SUSPENDED,
        issue_date=date(2022, 4, 22),
        expiration_date=date(2025, 4, 22),
        violations=[
            Violation(
                date=date(2024, 5, 3),
                type="safety_violation",
                description="Faulty wiring installation found during inspection.",
                resolution_status="pending",
            ),
            Violation(
                date=date(2024, 8, 12),
                type="code_violation",
                description=(
                    "Electrical panel installation did not meet NEC 2023 standards."
                ),
                resolution_status="unresolved",
            ),
        ],
    ),
    # Revoked — plumbing, violation
    License(
        license_number="ML-2020-0078",
        contractor_name="QuickFix Plumbing",
        trade="plumbing",
        status=LicenseStatus.REVOKED,
        issue_date=date(2020, 1, 5),
        expiration_date=date(2024, 1, 5),
        violations=[
            Violation(
                date=date(2023, 11, 20),
                type="fraud",
                description="Submitted falsified inspection reports.",
                resolution_status="unresolved",
            ),
        ],
    ),
    # Active — general, no violations (second general contractor)
    License(
        license_number="ML-2024-0512",
        contractor_name="Maplewood Construction Group",
        trade="general",
        status=LicenseStatus.ACTIVE,
        issue_date=date(2024, 7, 1),
        expiration_date=date(2026, 7, 1),
        violations=[],
    ),
    # Active — HVAC, no violations
    License(
        license_number="ML-2023-0198",
        contractor_name="Nguyen Plumbing & Heating",
        trade="hvac",
        status=LicenseStatus.ACTIVE,
        issue_date=date(2023, 8, 15),
        expiration_date=date(2025, 8, 15),
        violations=[],
    ),
]
