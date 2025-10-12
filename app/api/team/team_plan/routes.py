from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from ....database.models.team import Team
from ....database.models.team_plan import ActivityUpdate, PlanActivity, TeamPlan
from ...dependencies import DatabaseSession, LoggedInAccount
from ...global_schema import ApiResponse
from ..helper import check_permissions
from .schema import (
    ActivityUpdateCreate,
    ActivityUpdateCreateData,
    ActivityUpdateRead,
    ActivityUpdateUpdate,
    ActivityUpdateUpdateData,
    PlanActivityCreate,
    PlanActivityCreateData,
    PlanActivityDeleteData,
    PlanActivityRead,
    PlanActivityUpdate,
    PlanActivityUpdateData,
    TeamPlanCreate,
    TeamPlanCreateData,
    TeamPlanDeleteData,
    TeamPlanRead,
    TeamPlanUpdate,
    TeamPlanUpdateData,
)

router = APIRouter(prefix="/{uuid}/plans")


@router.get("/", response_model=ApiResponse[list[TeamPlanRead]])
def get_team_plans(uuid: UUID, db: DatabaseSession, account: LoggedInAccount):
    check_permissions(db, account, uuid)
    team = db.get(Team, uuid)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )
    return ApiResponse(
        message="Team plans retrieved successfully",
        data=[TeamPlanRead.model_validate(plan) for plan in team.plans],
    )


@router.post(
    "/new",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[TeamPlanCreateData],
)
def create_team_plan(
    uuid: UUID,
    payload: TeamPlanCreate,
    db: DatabaseSession,
    account: LoggedInAccount,
):
    check_permissions(db, account, uuid, leader_or_co_leader_only=True)
    team = db.get(Team, uuid)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found"
        )

    plan = TeamPlan(**payload.model_dump(), uuid=uuid)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return ApiResponse(
        message="Plan created successfully.",
        data=TeamPlanCreateData(plan_uuid=plan.uuid),
    )


@router.patch("/{plan_id}/update", response_model=ApiResponse[TeamPlanUpdateData])
def update_team_plan(
    uuid: UUID,
    plan_id: UUID,
    payload: TeamPlanUpdate,
    db: DatabaseSession,
    account: LoggedInAccount,
):
    check_permissions(db, account, uuid, leader_or_co_leader_only=True)
    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)

    db.add(plan)
    db.commit()
    db.refresh(plan)
    return ApiResponse(
        message="Plan updated successfully.",
        data=TeamPlanUpdateData(plan_uuid=plan.uuid),
    )


@router.delete("/{plan_id}/delete", response_model=ApiResponse[TeamPlanDeleteData])
def delete_team_plan(
    uuid: UUID, plan_id: UUID, db: DatabaseSession, account: LoggedInAccount
):
    check_permissions(db, account, uuid, leader_or_co_leader_only=True)
    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    db.delete(plan)
    db.commit()
    return ApiResponse(
        message="Plan deleted successfully.", data=TeamPlanDeleteData(plan_uuid=plan_id)
    )


@router.get("/{plan_id}/activities", response_model=ApiResponse[list[PlanActivityRead]])
def get_plan_activities(
    uuid: UUID, plan_id: UUID, db: DatabaseSession, account: LoggedInAccount
):
    check_permissions(db, account, uuid)
    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )
    return ApiResponse(
        message="Plan activities retrieved successfully", data=plan.activities
    )


@router.post(
    "/{plan_id}/activities/new",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[PlanActivityCreateData],
)
def create_plan_activity(
    uuid: UUID,
    plan_id: UUID,
    payload: PlanActivityCreate,
    db: DatabaseSession,
    account: LoggedInAccount,
):
    check_permissions(db, account, uuid, True)
    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    activity = PlanActivity(**payload.model_dump(), plan_uuid=plan_id)
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return ApiResponse(
        message="Activity logged successfully.",
        data=PlanActivityCreateData(activity_uuid=activity.uuid),
    )


@router.patch(
    "/{plan_id}/activities/{activity_id}/update",
    response_model=ApiResponse[PlanActivityUpdateData],
)
def update_plan_activity(
    uuid: UUID,
    plan_id: UUID,
    activity_id: UUID,
    payload: PlanActivityUpdate,
    db: DatabaseSession,
    account: LoggedInAccount,
):
    check_permissions(db, account, uuid, leader_or_co_leader_only=True)
    activity = db.get(PlanActivity, activity_id)
    if not activity or activity.plan_uuid != plan_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )

    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(activity, key, value)

    db.add(activity)
    db.commit()
    db.refresh(activity)
    return ApiResponse(
        message="Activity updated successfully.",
        data=PlanActivityUpdateData(activity_uuid=activity.uuid),
    )


@router.delete(
    "/{plan_id}/activities/{activity_id}/delete",
    response_model=ApiResponse[PlanActivityDeleteData],
)
def delete_plan_activity(
    uuid: UUID,
    plan_id: UUID,
    activity_id: UUID,
    db: DatabaseSession,
    account: LoggedInAccount,
):
    check_permissions(db, account, uuid, leader_or_co_leader_only=True)
    activity = db.get(PlanActivity, activity_id)
    if not activity or activity.plan_uuid != plan_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )

    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    db.delete(activity)
    db.commit()
    return ApiResponse(
        message="Activity deleted successfully.",
        data=PlanActivityDeleteData(activity_uuid=activity_id),
    )


@router.get(
    "/{plan_id}/activities/{activity_id}/activity-updates",
    response_model=ApiResponse[list[ActivityUpdateRead]],
)
def get_activity_updates(
    uuid: UUID,
    plan_id: UUID,
    activity_id: UUID,
    db: DatabaseSession,
    account: LoggedInAccount,
):
    check_permissions(db, account, uuid)
    activity = db.get(PlanActivity, activity_id)
    if not activity or activity.plan_uuid != plan_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )

    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    return ApiResponse(
        message="Activity updates retrieved successfully", data=activity.updates
    )


@router.post(
    "/{plan_id}/activities/{activity_id}/activity-updates/add",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[ActivityUpdateCreateData],
)
def create_activity_update(
    uuid: UUID,
    plan_id: UUID,
    activity_id: UUID,
    payload: ActivityUpdateCreate,
    db: DatabaseSession,
    account: LoggedInAccount,
):
    check_permissions(db, account, uuid)
    activity = db.get(PlanActivity, activity_id)
    if not activity or activity.plan_uuid != plan_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )

    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    if payload.volunteer_uuid != account.uuid:
        check_permissions(db, account, uuid, leader_or_co_leader_only=True)

    update = ActivityUpdate(**payload.model_dump(), activity_uuid=activity_id)
    db.add(update)
    db.commit()
    db.refresh(update)
    return ApiResponse(
        message="Activity update added successfully.",
        data=ActivityUpdateCreateData(update_uuid=update.uuid),
    )


@router.patch(
    "/{plan_id}/activities/{activity_id}/activity-updates/{update_id}/update",
    response_model=ApiResponse[ActivityUpdateUpdateData],
)
def update_activity_update(
    uuid: UUID,
    plan_id: UUID,
    activity_id: UUID,
    update_id: UUID,
    payload: ActivityUpdateUpdate,
    db: DatabaseSession,
    account: LoggedInAccount,
):
    check_permissions(db, account, uuid)
    update = db.get(ActivityUpdate, update_id)
    if not update or update.activity_uuid != activity_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity update not found"
        )

    activity = db.get(PlanActivity, activity_id)
    if not activity or activity.plan_uuid != plan_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )

    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    if update.volunteer_uuid != account.uuid:
        check_permissions(db, account, uuid, leader_or_co_leader_only=True)

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(update, key, value)

    db.add(update)
    db.commit()
    db.refresh(update)
    return ApiResponse(
        message="Activity update updated successfully.",
        data=ActivityUpdateUpdateData(update_uuid=update.uuid),
    )


@router.get(
    "/{plan_id}/activities/{activity_id}/activity-updates/{update_id}",
    response_model=ApiResponse[ActivityUpdateRead],
)
def get_activity_update(
    uuid: UUID,
    plan_id: UUID,
    activity_id: UUID,
    update_id: UUID,
    db: DatabaseSession,
    account: LoggedInAccount,
):
    check_permissions(db, account, uuid)
    update = db.get(ActivityUpdate, update_id)
    if not update or update.activity_uuid != activity_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity update not found"
        )

    activity = db.get(PlanActivity, activity_id)
    if not activity or activity.plan_uuid != plan_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Activity not found"
        )

    plan = db.get(TeamPlan, plan_id)
    if not plan or plan.uuid != uuid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found"
        )

    return ApiResponse(message="Activity update retrieved successfully", data=update)
