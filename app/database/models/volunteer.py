from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Column, Field, Relationship, SQLModel

from ...types.datetime_utc import SADateTimeUTC
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
    picture_missing = "picture_missing"


class Volunteer(SQLModel, table=True):
    uuid: UUID = Field(
        foreign_key="account.uuid", primary_key=True, index=True, ondelete="CASCADE"
    )
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
    created_at: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )
    last_updated: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )

    @property
    def unique_id(self) -> str:
        return self.created_at.strftime("%y%m%d%H%M%S%f")

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
    team_memberships: list["TeamMember"] = Relationship(back_populates="volunteer")
    activity_updates: list["ActivityUpdate"] = Relationship(back_populates="volunteer")
