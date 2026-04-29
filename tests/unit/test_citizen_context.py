# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for CitizenContext schema validation."""

import json

from gateway.memory.context import CitizenContext


class TestCitizenContextSchema:
    """Validate Pydantic model behaviour for CitizenContext."""

    def test_default_values(self):
        ctx = CitizenContext()
        assert ctx.citizen_name is None
        assert ctx.address is None
        assert ctx.case_number is None
        assert ctx.account_number is None
        assert ctx.service_type is None
        assert ctx.department is None
        assert ctx.prior_requests == []

    def test_full_construction(self):
        ctx = CitizenContext(
            citizen_name="Jane Doe",
            address="123 Main St",
            case_number="CASE-001",
            account_number="ACC-9999",
            service_type="water",
            department="Public Works",
            prior_requests=["billing inquiry", "service outage report"],
        )
        assert ctx.citizen_name == "Jane Doe"
        assert ctx.address == "123 Main St"
        assert ctx.case_number == "CASE-001"
        assert ctx.account_number == "ACC-9999"
        assert ctx.service_type == "water"
        assert ctx.department == "Public Works"
        assert ctx.prior_requests == ["billing inquiry", "service outage report"]

    def test_partial_construction(self):
        ctx = CitizenContext(citizen_name="John Smith", department="DMV")
        assert ctx.citizen_name == "John Smith"
        assert ctx.department == "DMV"
        assert ctx.case_number is None
        assert ctx.prior_requests == []

    def test_json_round_trip(self):
        original = CitizenContext(
            citizen_name="Jane Doe",
            address="456 Oak Ave",
            case_number="CASE-002",
            account_number="ACC-1234",
            service_type="permits",
            department="Planning",
            prior_requests=["zoning question"],
        )
        json_str = original.model_dump_json()
        restored = CitizenContext.model_validate_json(json_str)
        assert restored == original

    def test_json_round_trip_empty(self):
        original = CitizenContext()
        json_str = original.model_dump_json()
        restored = CitizenContext.model_validate_json(json_str)
        assert restored == original

    def test_dict_round_trip(self):
        original = CitizenContext(citizen_name="Test", prior_requests=["a", "b"])
        data = original.model_dump()
        restored = CitizenContext.model_validate(data)
        assert restored == original

    def test_json_output_structure(self):
        ctx = CitizenContext(citizen_name="Jane", service_type="water")
        data = json.loads(ctx.model_dump_json())
        assert "citizen_name" in data
        assert "prior_requests" in data
        assert data["citizen_name"] == "Jane"
        assert data["service_type"] == "water"
        assert data["prior_requests"] == []

    def test_prior_requests_is_list(self):
        ctx = CitizenContext(prior_requests=["one", "two", "three"])
        assert len(ctx.prior_requests) == 3
        assert ctx.prior_requests[1] == "two"

    def test_prior_requests_default_is_independent(self):
        """Ensure each instance gets its own list (no shared mutable default)."""
        ctx1 = CitizenContext()
        ctx2 = CitizenContext()
        ctx1.prior_requests.append("should not appear in ctx2")
        assert ctx2.prior_requests == []

    def test_extra_fields_rejected(self):
        """By default Pydantic ignores extra fields; verify no leakage."""
        ctx = CitizenContext.model_validate({"citizen_name": "X", "ssn": "000-00-0000"})
        assert not hasattr(ctx, "ssn")
