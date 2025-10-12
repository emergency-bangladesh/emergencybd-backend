from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from sqlmodel import Field, Relationship, SQLModel

from ...utils.time import get_utc_time

if TYPE_CHECKING:
    from .team import Team
    from .volunteer import Volunteer


class TeamPlan(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    title: str = Field(index=True)
    description: str
    team_uuid: UUID = Field(foreign_key="team.uuid", index=True, ondelete="CASCADE")
    target_district: str = Field(index=True)
    target_upazila: str = Field(index=True)
    start_date: date = Field(index=True)
    end_date: date = Field(index=True)
    created_at: datetime = Field(default_factory=get_utc_time)
    last_updated: datetime = Field(default_factory=get_utc_time)

    team: "Team" = Relationship(back_populates="plans")
    activities: list["PlanActivity"] = Relationship(
        back_populates="plan", cascade_delete=True
    )


class PlanActivity(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    plan_uuid: UUID = Field(foreign_key="teamplan.uuid", index=True, ondelete="CASCADE")
    details: str
    exact_location: str
    effective_date: date = Field(index=True)
    created_at: datetime = Field(default_factory=get_utc_time)
    last_updated: datetime = Field(default_factory=get_utc_time)

    plan: "TeamPlan" = Relationship(back_populates="activities")
    updates: list["ActivityUpdate"] = Relationship(
        back_populates="activity", cascade_delete=True
    )


class ActivityUpdate(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    activity_uuid: UUID = Field(
        foreign_key="planactivity.uuid", index=True, ondelete="CASCADE"
    )
    volunteer_uuid: UUID = Field(
        foreign_key="volunteer.uuid", index=True, ondelete="CASCADE"
    )
    title: str = Field(index=True)
    details: str
    effective_time: datetime = Field(index=True)
    created_at: datetime = Field(default_factory=get_utc_time)
    last_updated: datetime = Field(default_factory=get_utc_time)

    activity: "PlanActivity" = Relationship(back_populates="updates")
    volunteer: "Volunteer" = Relationship(back_populates="activity_updates")
