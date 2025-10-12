from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from ...utils.time import get_utc_time

if TYPE_CHECKING:
    from .account import Account
    from .volunteer import Volunteer


class IssueCategory(str, Enum):
    # For now we are working with blood_donation and lost_and_found
    blood_donation = "blood_donation"
    # fire = "fire"
    # natural_disaster = "natural_disaster"
    lost_and_found = "lost_and_found"
    # other = "other"


class IssueStatus(str, Enum):
    open = "open"
    working = "working"
    solved = "solved"
    invalid = "invalid"


class IssueResponseStatus(str, Enum):
    working = "working"
    solved = "solved"
    invalid = "invalid"


class Issue(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    account_uuid: UUID = Field(
        foreign_key="account.uuid", index=True, ondelete="CASCADE"
    )
    emergency_phone_number: str = Field(index=True)
    status: IssueStatus = Field(index=True, default=IssueStatus.open)
    category: IssueCategory = Field(index=True)
    created_at: datetime = Field(default_factory=get_utc_time)
    last_updated: datetime = Field(default_factory=get_utc_time)

    account: "Account" = Relationship()
    volunteer_responses: list["VolunteerIssueResponse"] = Relationship(
        back_populates="issue", cascade_delete=True
    )


# for issue.category='blood_donation'
class BloodDonationIssue(SQLModel, table=True):
    uuid: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        foreign_key="issue.uuid",
        ondelete="CASCADE",
    )
    patient_name: str = Field(index=True)
    blood_group: str
    amount_bag: int
    hospital_name: str
    district: str
    upazila: str
    instructions: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=get_utc_time)
    last_updated: datetime = Field(default_factory=get_utc_time)

    issue: "Issue" = Relationship()


# for issue.category = 'lost_and_found'
class LostAndFoundIssue(SQLModel, table=True):
    uuid: UUID = Field(
        default_factory=uuid4,
        primary_key=True,
        index=True,
        foreign_key="issue.uuid",
        ondelete="CASCADE",
    )
    name_of_person: str = Field(index=True)
    age_of_person: int
    last_seen_location: str
    details: str
    district: str
    upazila: str
    blood_group: str | None = Field(default=None)
    occupation: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=get_utc_time)
    last_updated: datetime = Field(default_factory=get_utc_time)

    issue: "Issue" = Relationship()


class VolunteerIssueResponse(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    issue_uuid: UUID = Field(foreign_key="issue.uuid", index=True)
    volunteer_uuid: UUID = Field(foreign_key="volunteer.uuid", index=True)
    status_mark: IssueResponseStatus | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=get_utc_time)

    issue: "Issue" = Relationship(back_populates="volunteer_responses")
    volunteer: "Volunteer" = Relationship(back_populates="issue_responses")
