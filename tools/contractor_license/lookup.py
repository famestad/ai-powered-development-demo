"""Contractor license lookup for the City of Maplewood."""

from tools.contractor_license.data import LICENSES
from tools.contractor_license.models import License


def verify_contractor_license(
    license_number: str | None = None,
    contractor_name: str | None = None,
    trade: str | None = None,
) -> License | list[License] | None:
    """Look up contractor licenses by number, name, or trade.

    Args:
        license_number: Exact license number to look up. When provided,
            returns a single License or None.
        contractor_name: Case-insensitive substring match on contractor name.
        trade: Case-insensitive exact match on trade. Narrows results when
            combined with contractor_name, or returns all licenses for the
            trade when used alone.

    Returns:
        A single License when looking up by license_number (or None on miss),
        or a list of matching licenses (possibly empty) for name/trade queries.
    """
    if license_number is not None:
        for lic in LICENSES:
            if lic.license_number == license_number:
                return lic
        return None

    results = LICENSES

    if contractor_name is not None:
        name_lower = contractor_name.lower()
        results = [
            lic for lic in results if name_lower in lic.contractor_name.lower()
        ]

    if trade is not None:
        trade_lower = trade.lower()
        results = [lic for lic in results if lic.trade.lower() == trade_lower]

    return results
