# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
"""Pydantic model for structured citizen session context."""

from typing import List, Optional

from pydantic import BaseModel, Field


class CitizenContext(BaseModel):
    """Structured context for a citizen interaction session.

    Stores key information about the citizen and their service request,
    serialized as a JSON blob in AgentCore Memory keyed by session_id.
    """

    citizen_name: Optional[str] = Field(
        default=None, description="Full name of the citizen"
    )
    address: Optional[str] = Field(default=None, description="Citizen's address")
    case_number: Optional[str] = Field(
        default=None, description="Reference case or ticket number"
    )
    account_number: Optional[str] = Field(
        default=None, description="Citizen's account number"
    )
    service_type: Optional[str] = Field(
        default=None, description="Type of service requested (e.g. 'water', 'permits')"
    )
    department: Optional[str] = Field(
        default=None, description="Government department handling the request"
    )
    prior_requests: List[str] = Field(
        default_factory=list,
        description="Summary of prior requests or interactions in this session",
    )
