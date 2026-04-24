"""Citizen-safe response formatter for contractor license verification results.

Produces user-facing text from License data, leading with status warnings when
the license is not active and surfacing violations with appropriate framing.
"""

from tools.license_verification.config import (
    ACTIVE_CLEAN_NOTE,
    ACTIVE_WITH_VIOLATIONS_NOTE,
    NOT_FOUND_MESSAGE,
    STATUS_LABELS,
    STATUS_WARNINGS,
    VIOLATION_SEVERITY_LABELS,
)
from tools.license_verification.models import License, LicenseStatus, Violation


def format_license_response(license: License) -> str:
    """Format a single license record into a citizen-safe response string.

    The response is structured as follows:
    1. A status warning banner (if the license is not active).
    2. Core license details (number, holder, type, status, expiration).
    3. A violations section (if any violations exist on the record).

    Args:
        license: The License record to format.

    Returns:
        A formatted, citizen-facing string describing the license.
    """
    sections: list[str] = []

    # Status warning (non-active licenses only)
    warning = STATUS_WARNINGS.get(license.status)
    if warning is not None:
        sections.append(warning)

    # Core details
    sections.append(_format_details(license))

    # Violations / clean note
    if license.status == LicenseStatus.ACTIVE and not license.violations:
        sections.append(ACTIVE_CLEAN_NOTE)
    elif license.violations:
        if license.status == LicenseStatus.ACTIVE:
            sections.append(ACTIVE_WITH_VIOLATIONS_NOTE)
        sections.append(_format_violations(license.violations))

    return "\n\n".join(sections)


def format_license_list_response(licenses: list[License]) -> str:
    """Format a list of license records into a citizen-safe response string.

    Each license is formatted individually and separated by a divider. If the
    list is empty, the not-found message is returned.

    Args:
        licenses: A list of License records to format.

    Returns:
        A formatted, citizen-facing string describing all matching licenses,
        or the not-found message if the list is empty.
    """
    if not licenses:
        return NOT_FOUND_MESSAGE

    if len(licenses) == 1:
        return format_license_response(licenses[0])

    formatted = [format_license_response(lic) for lic in licenses]
    return "\n\n---\n\n".join(formatted)


def format_not_found_response() -> str:
    """Return the citizen-facing message for a license lookup with no results.

    Returns:
        The configured not-found message string.
    """
    return NOT_FOUND_MESSAGE


def _format_details(license: License) -> str:
    """Format the core detail block for a license.

    Args:
        license: The License record whose details to format.

    Returns:
        A multi-line string with license number, holder, type, status,
        and expiration date.
    """
    status_label = STATUS_LABELS[license.status]
    return (
        f"**License Number:** {license.license_number}\n"
        f"**Holder:** {license.holder_name}\n"
        f"**Type:** {license.license_type}\n"
        f"**Status:** {status_label}\n"
        f"**Expiration Date:** {license.expiration_date.strftime('%B %d, %Y')}"
    )


def _format_violations(violations: list[Violation]) -> str:
    """Format a list of violations into a readable section.

    Args:
        violations: The list of Violation records to format.

    Returns:
        A multi-line string listing each violation with severity and date.
    """
    lines: list[str] = ["**Violations on Record:**"]
    for violation in violations:
        severity_label = VIOLATION_SEVERITY_LABELS[violation.severity]
        lines.append(
            f"- [{severity_label}] {violation.description} "
            f"({violation.date.strftime('%B %d, %Y')})"
        )
    return "\n".join(lines)
