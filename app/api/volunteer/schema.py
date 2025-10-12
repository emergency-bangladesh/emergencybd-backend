from datetime import datetime
from typing import Literal
from uuid import UUID

from ...database.models.team import TeamMemberRole
from ..global_schema import BaseModel


class VolunteerCreate(BaseModel):
    full_name: str
    phone_number: str
    email_address: str
    permanent_upazila: str
    permanent_district: str
    current_upazila: str
    current_district: str
    blood_group: Literal["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    identifier_type: Literal["nid", "brn"]
    identifier_value: str
    birth_date: datetime
    password: str
    gender: Literal["male", "female", "intersex"]


class VolunteerListResponse(BaseModel):
    volunteer_uuid: UUID
    full_name: str
    phone_number: str
    email_address: str
    permanent_upazila: str
    permanent_district: str
    current_upazila: str
    current_district: str
    blood_group: str
    status: str

    model_config = {"from_attributes": True}


class TeamInformation(BaseModel):
    team_name: str
    role: TeamMemberRole
    team_uuid: UUID


class VolunteerDetailResponse(BaseModel):
    volunteer_uuid: UUID
    full_name: str
    phone_number: str
    email_address: str
    permanent_upazila: str
    permanent_district: str
    current_upazila: str
    current_district: str
    blood_group: str
    identifier_type: Literal["nid", "brn"]
    status: str
    created_at: datetime
    last_updated: datetime
    issue_responses: int
    current_team_information: TeamInformation | None = None

    model_config = {"from_attributes": True}


class VolunteerUpdate(BaseModel):
    current_upazila: str | None = None
    current_district: str | None = None


class VolunteerCreateData(BaseModel):
    volunteer_uuid: UUID
    status: str


class VolunteerUpdateDeleteData(BaseModel):
    volunteer_uuid: UUID
