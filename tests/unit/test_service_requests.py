"""Unit tests for the service request data model and mock data source."""

from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from tools.service_requests.models import (
    Address,
    RequestStatus,
    RequestType,
    ServiceRequest,
    ServiceType,
)
from tools.service_requests.store import (
    create_service_request,
    get_service_request,
    reset_store,
)

FUTURE_DATE = date.today() + timedelta(days=30)
PAST_DATE = date.today() - timedelta(days=1)

VALID_ADDRESS_A = Address(street="123 Maple St", city="Maplewood", zip_code="07040")
VALID_ADDRESS_B = Address(street="456 Oak Ave", city="Maplewood", zip_code="07040")


@pytest.fixture(autouse=True)
def _clean_store():
    """Reset the in-memory store before each test."""
    reset_store()


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------


class TestAddressModel:
    """Tests for the Address Pydantic model."""

    def test_valid_address(self):
        addr = Address(street="10 Main St", city="Maplewood", zip_code="07040")
        assert addr.street == "10 Main St"

    def test_zip_plus_four(self):
        addr = Address(street="10 Main St", city="Maplewood", zip_code="07040-1234")
        assert addr.zip_code == "07040-1234"

    def test_invalid_zip_rejected(self):
        with pytest.raises(ValidationError):
            Address(street="10 Main St", city="Maplewood", zip_code="ABCDE")

    def test_empty_street_rejected(self):
        with pytest.raises(ValidationError):
            Address(street="", city="Maplewood", zip_code="07040")

    def test_empty_city_rejected(self):
        with pytest.raises(ValidationError):
            Address(street="10 Main St", city="", zip_code="07040")


# ---------------------------------------------------------------------------
# create_service_request — happy paths
# ---------------------------------------------------------------------------


class TestCreateStartRequest:
    """Start-service request creation."""

    def test_start_request_returns_populated_model(self):
        req = create_service_request(
            request_type=RequestType.START,
            service_type=ServiceType.WATER,
            account_number="ACCT-001",
            preferred_start_date=FUTURE_DATE,
            new_address=VALID_ADDRESS_A,
        )
        assert isinstance(req, ServiceRequest)
        assert req.request_type == RequestType.START
        assert req.service_type == ServiceType.WATER
        assert req.new_address == VALID_ADDRESS_A
        assert req.status == RequestStatus.PENDING
        assert req.account_number == "ACCT-001"

    def test_start_request_persisted(self):
        req = create_service_request(
            request_type=RequestType.START,
            service_type=ServiceType.POWER,
            account_number="ACCT-002",
            preferred_start_date=FUTURE_DATE,
            new_address=VALID_ADDRESS_B,
        )
        assert get_service_request(req.id) == req


class TestCreateStopRequest:
    """Stop-service request creation."""

    def test_stop_request_returns_populated_model(self):
        req = create_service_request(
            request_type=RequestType.STOP,
            service_type=ServiceType.GAS,
            account_number="ACCT-003",
            preferred_start_date=FUTURE_DATE,
            current_address=VALID_ADDRESS_A,
        )
        assert req.request_type == RequestType.STOP
        assert req.current_address == VALID_ADDRESS_A


class TestCreateTransferRequest:
    """Transfer-service request creation."""

    def test_transfer_request_returns_populated_model(self):
        req = create_service_request(
            request_type=RequestType.TRANSFER,
            service_type=ServiceType.WATER,
            account_number="ACCT-004",
            preferred_start_date=FUTURE_DATE,
            current_address=VALID_ADDRESS_A,
            new_address=VALID_ADDRESS_B,
        )
        assert req.request_type == RequestType.TRANSFER
        assert req.current_address == VALID_ADDRESS_A
        assert req.new_address == VALID_ADDRESS_B


# ---------------------------------------------------------------------------
# Validation — date
# ---------------------------------------------------------------------------


class TestDateValidation:
    """Past start dates must be rejected."""

    def test_past_start_date_rejected(self):
        with pytest.raises(ValueError, match="cannot be in the past"):
            create_service_request(
                request_type=RequestType.START,
                service_type=ServiceType.WATER,
                account_number="ACCT-005",
                preferred_start_date=PAST_DATE,
                new_address=VALID_ADDRESS_A,
            )

    def test_today_is_accepted(self):
        req = create_service_request(
            request_type=RequestType.START,
            service_type=ServiceType.WATER,
            account_number="ACCT-006",
            preferred_start_date=date.today(),
            new_address=VALID_ADDRESS_A,
        )
        assert req.preferred_start_date == date.today()


# ---------------------------------------------------------------------------
# Validation — missing required addresses
# ---------------------------------------------------------------------------


class TestMissingAddressValidation:
    """Required addresses per request_type must be enforced."""

    def test_start_requires_new_address(self):
        with pytest.raises(ValueError, match="new_address is required"):
            create_service_request(
                request_type=RequestType.START,
                service_type=ServiceType.WATER,
                account_number="ACCT-010",
                preferred_start_date=FUTURE_DATE,
            )

    def test_stop_requires_current_address(self):
        with pytest.raises(ValueError, match="current_address is required"):
            create_service_request(
                request_type=RequestType.STOP,
                service_type=ServiceType.GAS,
                account_number="ACCT-011",
                preferred_start_date=FUTURE_DATE,
            )

    def test_transfer_requires_current_address(self):
        with pytest.raises(ValueError, match="current_address is required"):
            create_service_request(
                request_type=RequestType.TRANSFER,
                service_type=ServiceType.POWER,
                account_number="ACCT-012",
                preferred_start_date=FUTURE_DATE,
                new_address=VALID_ADDRESS_B,
            )

    def test_transfer_requires_new_address(self):
        with pytest.raises(ValueError, match="new_address is required"):
            create_service_request(
                request_type=RequestType.TRANSFER,
                service_type=ServiceType.POWER,
                account_number="ACCT-013",
                preferred_start_date=FUTURE_DATE,
                current_address=VALID_ADDRESS_A,
            )


# ---------------------------------------------------------------------------
# Reference number format and uniqueness
# ---------------------------------------------------------------------------


class TestReferenceNumber:
    """SR-YYYY-NNNN reference numbers."""

    def test_format(self):
        req = create_service_request(
            request_type=RequestType.START,
            service_type=ServiceType.WATER,
            account_number="ACCT-020",
            preferred_start_date=FUTURE_DATE,
            new_address=VALID_ADDRESS_A,
        )
        import re

        assert re.match(r"^SR-\d{4}-\d{4}$", req.id)

    def test_uniqueness(self):
        ids = set()
        for i in range(50):
            req = create_service_request(
                request_type=RequestType.START,
                service_type=ServiceType.WATER,
                account_number=f"ACCT-{100 + i}",
                preferred_start_date=FUTURE_DATE,
                new_address=VALID_ADDRESS_A,
            )
            ids.add(req.id)
        assert len(ids) == 50

    def test_sequential_numbering(self):
        r1 = create_service_request(
            request_type=RequestType.START,
            service_type=ServiceType.WATER,
            account_number="ACCT-200",
            preferred_start_date=FUTURE_DATE,
            new_address=VALID_ADDRESS_A,
        )
        r2 = create_service_request(
            request_type=RequestType.STOP,
            service_type=ServiceType.GAS,
            account_number="ACCT-201",
            preferred_start_date=FUTURE_DATE,
            current_address=VALID_ADDRESS_A,
        )
        year = date.today().year
        assert r1.id == f"SR-{year}-0001"
        assert r2.id == f"SR-{year}-0002"
