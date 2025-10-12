from datetime import date, datetime
from uuid import UUID

from ...database.models.team import TeamMemberRole
from ..global_schema import BaseModel


class TeamRead(BaseModel):
    uuid: UUID
    name: str
    expiration_date: date
    leader_uuid: UUID
    co_leader_uuid: UUID | None
    created_at: datetime
    last_updated: datetime
    members_count: int


class TeamCreate(BaseModel):
    name: str
    expiration_date: datetime
    co_leader_uuid: UUID | None = None


class TeamCreateData(BaseModel):
    team_uuid: UUID


class TeamUpdate(BaseModel):
    name: str | None = None
    expiration_date: datetime | None = None
    leader_uuid: UUID | None = None
    co_leader_uuid: UUID | None = None


class TeamUpdateData(BaseModel):
    team_uuid: UUID


class TeamMemberRead(BaseModel):
    team_uuid: UUID
    volunteer_uuid: UUID
    role: TeamMemberRole
    joined_at: datetime

    model_config = {"from_attributes": True}


class TeamMemberCreate(BaseModel):
    volunteer_uuid: UUID
    role: TeamMemberRole


class TeamMemberCreateData(BaseModel):
    team_uuid: UUID
    volunteer_uuid: UUID


class TeamMemberDeleteData(BaseModel):
    team_uuid: UUID
    volunteer_uuid: UUID
