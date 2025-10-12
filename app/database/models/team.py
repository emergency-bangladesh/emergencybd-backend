from datetime import date, datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from ...utils.time import get_utc_time

if TYPE_CHECKING:
    from .team_plan import TeamPlan
    from .volunteer import Volunteer


class TeamMemberRole(str, Enum):
    leader = "leader"
    co_leader = "co_leader"
    member = "member"


class Team(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    name: str = Field(index=True, unique=True)
    expiration_date: date = Field(index=True)
    leader_uuid: UUID = Field(
        foreign_key="volunteer.uuid", index=True, ondelete="CASCADE"
    )
    co_leader_uuid: UUID | None = Field(
        default=None, foreign_key="volunteer.uuid", index=True, ondelete="SET NULL"
    )
    created_at: datetime = Field(default_factory=get_utc_time)
    last_updated: datetime = Field(default_factory=get_utc_time)

    leader: "Volunteer" = Relationship(
        back_populates="teams_led",
        sa_relationship_kwargs={"foreign_keys": "[Team.leader_uuid]"},
    )
    co_leader: "Volunteer" = Relationship(
        back_populates="teams_co_led",
        sa_relationship_kwargs={"foreign_keys": "[Team.co_leader_uuid]"},
    )
    members: list["TeamMember"] = Relationship(
        back_populates="team", cascade_delete=True
    )
    plans: list["TeamPlan"] = Relationship(back_populates="team", cascade_delete=True)


class TeamMember(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    team_uuid: UUID = Field(foreign_key="team.uuid", index=True, ondelete="CASCADE")
    volunteer_uuid: UUID = Field(
        foreign_key="volunteer.uuid", index=True, ondelete="CASCADE"
    )
    role: TeamMemberRole = Field(index=True, default=TeamMemberRole.member)
    joined_at: datetime = Field(default_factory=get_utc_time)

    team: "Team" = Relationship(back_populates="members")
    volunteer: "Volunteer" = Relationship(back_populates="team_memberships")
