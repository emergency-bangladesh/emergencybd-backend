from datetime import datetime
from uuid import UUID

from ...global_schema import BaseModel


class TeamPlanRead(BaseModel):
    plan_uuid: UUID
    title: str
    description: str
    team_uuid: UUID
    working_district: str
    working_upazila: str
    start_date: datetime
    end_date: datetime
    created_at: datetime
    last_updated: datetime

    model_config = {"from_attributes": True}


class TeamPlanCreate(BaseModel):
    title: str
    description: str
    target_district: str
    target_upazila: str
    start_date: datetime
    end_date: datetime


class TeamPlanCreateData(BaseModel):
    plan_uuid: UUID


class TeamPlanUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    working_district: str | None = None
    working_upazila: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class TeamPlanUpdateData(BaseModel):
    plan_uuid: UUID


class TeamPlanDeleteData(BaseModel):
    plan_uuid: UUID


class PlanActivityRead(BaseModel):
    activity_uuid: UUID
    details: str
    exact_location: str
    effective_date: datetime
    created_at: datetime
    last_updated: datetime

    model_config = {"from_attributes": True}


class PlanActivityCreate(BaseModel):
    details: str
    exact_location: str
    effective_date: datetime


class PlanActivityCreateData(BaseModel):
    activity_uuid: UUID


class PlanActivityUpdate(BaseModel):
    details: str | None = None
    exact_location: str | None = None
    effective_date: datetime | None = None


class PlanActivityUpdateData(BaseModel):
    activity_uuid: UUID


class PlanActivityDeleteData(BaseModel):
    activity_uuid: UUID


class ActivityUpdateRead(BaseModel):
    update_uuid: UUID
    activity_uuid: UUID
    volunteer_uuid: UUID
    title: str
    details: str
    effective_time: datetime
    created_at: datetime
    last_updated: datetime
    model_config = {"from_attributes": True}


class ActivityUpdateCreate(BaseModel):
    volunteer_uuid: UUID
    title: str
    details: str
    effective_time: datetime


class ActivityUpdateCreateData(BaseModel):
    update_uuid: UUID


class ActivityUpdateUpdate(BaseModel):
    volunteer_uuid: UUID | None = None
    title: str | None = None
    details: str | None = None
    effective_time: datetime | None = None


class ActivityUpdateUpdateData(BaseModel):
    update_uuid: UUID
