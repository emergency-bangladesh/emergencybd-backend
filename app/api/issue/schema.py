from datetime import datetime
from typing import Literal, Sequence
from uuid import UUID

from pydantic import EmailStr

from ...database.models.issue import Issue, IssueResponseStatus, IssueStatus
from ..global_schema import BaseModel


# Schema for GET /issues/
class GetIssuesData(BaseModel):
    has_more: bool
    issues: Sequence[Issue]


# Schemas for issue creation
class BloodDonationIssueCreate(BaseModel):
    full_name: str
    emergency_phone_number: str
    patient_name: str
    blood_group: str
    amount_bag: int
    hospital_name: str
    district: str
    upazila: str
    instructions: str | None = None
    phone_number: str
    email_address: EmailStr


class LostAndFoundIssueCreate(BaseModel):
    full_name: str
    emergency_phone_number: str
    name_of_person: str
    age_of_person: int
    last_seen_location: str
    details: str
    district: str
    upazila: str
    blood_group: str | None = None
    occupation: str | None = None
    phone_number: str
    email_address: EmailStr


class IssueCreateData(BaseModel):
    issue_uuid: UUID


# Schemas for reading detailed issue data
class BloodDonationIssueRead(BaseModel):
    issue_uuid: UUID
    status: IssueStatus
    created_at: datetime
    last_updated: datetime
    account_uuid: UUID
    phone_number: str
    email_address: EmailStr
    category: Literal["blood_donation"] = "blood_donation"
    patient_name: str
    blood_group: str
    amount_bag: int
    hospital_name: str
    district: str
    upazila: str
    instructions: str | None
    contact_person_name: str
    emergency_phone_number: str


class LostAndFoundIssueRead(BaseModel):
    issue_uuid: UUID
    status: IssueStatus
    created_at: datetime
    last_updated: datetime
    account_uuid: UUID
    phone_number: str
    email_address: EmailStr
    category: Literal["lost_and_found"] = "lost_and_found"
    name_of_person: str
    age_of_person: int
    last_seen_location: str
    details: str
    district: str
    upazila: str
    blood_group: str | None
    occupation: str | None
    contact_person_name: str
    emergency_phone_number: str


# Schemas for updates and responses
class IssueUpdateData(BaseModel):
    issue_uuid: UUID
    status: IssueStatus


class IssueResponseCreateData(BaseModel):
    issue: UUID
    volunteer_uuid: UUID
    status_mark: IssueResponseStatus | None = None


class IssueResponseRead(BaseModel):
    volunteer_uuid: UUID
    status_mark: IssueResponseStatus | None
    created_at: datetime

    model_config = {"from_attributes": True}


class IssueDeleteData(BaseModel):
    issue_uuid: UUID
