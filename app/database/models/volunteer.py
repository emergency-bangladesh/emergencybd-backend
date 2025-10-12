import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field, Relationship, SQLModel

from ...utils.time import get_utc_time

if TYPE_CHECKING:
    from .account import Account
    from .issue import VolunteerIssueResponse
    from .team import Team, TeamMember
    from .team_plan import ActivityUpdate


class VolunteerIdentifierType(str, Enum):
    brn = "brn"
    nid = "nid"


class VolunteerStatus(str, Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    terminated = "terminated"


class Volunteer(SQLModel, table=True):
    uuid: UUID = Field(foreign_key="account.uuid", primary_key=True, index=True)
    full_name: str
    gender: str = Field(index=True)
    blood_group: str = Field(index=True)
    identifier_type: VolunteerIdentifierType = Field(index=True)
    birth_date_cipher: bytes
    birth_date_nonce: bytes
    permanent_upazila: str = Field(index=True)
    permanent_district: str = Field(index=True)
    current_upazila: str = Field(index=True)
    current_district: str = Field(index=True)
    status: VolunteerStatus = Field(index=True, default=VolunteerStatus.pending)
    created_at: datetime.datetime = Field(default_factory=get_utc_time)
    last_updated: datetime.datetime = Field(default_factory=get_utc_time)

    account: "Account" = Relationship()
    issue_responses: list["VolunteerIssueResponse"] = Relationship(
        back_populates="volunteer", cascade_delete=True
    )
    teams_led: list["Team"] = Relationship(
        back_populates="leader",
        sa_relationship_kwargs={"foreign_keys": "[Team.leader_uuid]"},
    )
    teams_co_led: list["Team"] = Relationship(
        back_populates="co_leader",
        sa_relationship_kwargs={"foreign_keys": "[Team.co_leader_uuid]"},
    )
    team_memberships: list["TeamMember"] = Relationship(
        back_populates="volunteer", cascade_delete=True
    )
    activity_updates: list["ActivityUpdate"] = Relationship(
        back_populates="volunteer", cascade_delete=True
    )
