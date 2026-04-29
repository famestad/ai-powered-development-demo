"""In-memory store and factory for service requests."""

from datetime import date, datetime

from tools.service_requests.models import (
    Address,
    RequestStatus,
    RequestType,
    ServiceRequest,
    ServiceType,
)

_store: dict[str, ServiceRequest] = {}
_counter: int = 0


def _next_reference_number() -> str:
    global _counter
    _counter += 1
    year = datetime.utcnow().year
    return f"SR-{year}-{_counter:04d}"


def reset_store() -> None:
    """Clear the in-memory store and reset the counter. Intended for tests."""
    global _counter
    _store.clear()
    _counter = 0


def create_service_request(
    *,
    request_type: RequestType,
    service_type: ServiceType,
    account_number: str,
    preferred_start_date: date,
    current_address: Address | None = None,
    new_address: Address | None = None,
) -> ServiceRequest:
    """Create and persist a new service request.

    Raises ValueError for invalid inputs:
    - preferred_start_date in the past
    - missing current_address for stop/transfer requests
    - missing new_address for start/transfer requests
    """
    today = date.today()
    if preferred_start_date < today:
        raise ValueError(
            f"preferred_start_date ({preferred_start_date}) cannot be in the past"
        )

    if request_type in (RequestType.STOP, RequestType.TRANSFER):
        if current_address is None:
            raise ValueError(
                f"current_address is required for {request_type.value} requests"
            )

    if request_type in (RequestType.START, RequestType.TRANSFER):
        if new_address is None:
            raise ValueError(
                f"new_address is required for {request_type.value} requests"
            )

    ref = _next_reference_number()
    request = ServiceRequest(
        id=ref,
        request_type=request_type,
        service_type=service_type,
        current_address=current_address,
        new_address=new_address,
        preferred_start_date=preferred_start_date,
        account_number=account_number,
        status=RequestStatus.PENDING,
    )
    _store[ref] = request
    return request


def get_service_request(reference_number: str) -> ServiceRequest | None:
    """Look up a service request by reference number."""
    return _store.get(reference_number)
