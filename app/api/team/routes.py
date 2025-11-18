from datetime import date
from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import desc, select

from ...database.models.account import Admin
from ...database.models.team import Team, TeamMember, TeamMemberRole
from ...database.models.volunteer import Volunteer
from ...utils.time import get_utc_time
from ..dependencies import (
    CurrentAdmin,
    CurrentVolunteer,
    DatabaseSession,
    RequestingActor,
)
from ..global_schema import ApiResponse
from .helper import check_permissions
from .schema import (
    TeamCreate,
    TeamCreateData,
    TeamMemberCreate,
    TeamMemberCreateData,
    TeamMemberDeleteData,
    TeamMemberRead,
    TeamRead,
    TeamUpdate,
    TeamUpdateData,
)
from .team_plan.routes import router as team_plan_router

router = APIRouter(prefix="/teams", tags=["Team Management"])


@router.get("/", response_model=ApiResponse[Sequence[Team]])
def get_all_teams(
    db: DatabaseSession, _: CurrentAdmin, skip: int = 0, limit: int = 100
):
    teams = db.exec(select(Team).offset(skip).limit(limit)).all()
    return ApiResponse(
        message="Teams retrieved successfully",
        data=teams,
    )


@router.post(
    "/new",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[TeamCreateData],
)
def create_team(payload: TeamCreate, db: DatabaseSession, volunteer: CurrentVolunteer):
    if db.scalar(
        select(Team).where(
            Team.name == payload.name, Team.expiration_date >= get_utc_time()
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A team with this name already exists.",
        )

    if payload.co_leader_uuid:
        co_leader = db.get(Volunteer, payload.co_leader_uuid)
        if not co_leader:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Co-leader volunteer not found.",
            )

        ## I can feal this weird variable naming!
        if _existing_member_ := db.scalar(
            select(TeamMember)
            .where(TeamMember.volunteer_uuid == co_leader.uuid)
            .order_by(desc(TeamMember.joined_at))
        ):
            if _existing_member_.team.expiration_date >= get_utc_time():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Co-leader is already a member of another team.",
                )

    team = Team(
        name=payload.name,
        expiration_date=payload.expiration_date,
        leader_uuid=volunteer.uuid,
        co_leader_uuid=payload.co_leader_uuid,
    )
    db.add(team)
    db.flush()

    # Add leader and co-leader as members
    db.add(
        TeamMember(
            team_uuid=team.uuid,
            volunteer_uuid=team.leader_uuid,
            role=TeamMemberRole.leader,
        )
    )
    if team.co_leader_uuid:
        db.add(
            TeamMember(
                team_uuid=team.uuid,
                volunteer_uuid=team.co_leader_uuid,
                role=TeamMemberRole.co_leader,
            )
        )

    db.commit()
    db.refresh(team)

    return ApiResponse(
        message="Team created successfully.", data=TeamCreateData(team_uuid=team.uuid)
    )


@router.get("/{uuid}", response_model=ApiResponse[TeamRead], summary="Get Team by uuid")
def get_team_by_uuid(uuid: UUID, db: DatabaseSession) -> ApiResponse[TeamRead]:
    team = db.get(Team, uuid)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found."
        )
    return ApiResponse(
        message="Team retrieved successfully",
        data=TeamRead(
            uuid=team.uuid,
            name=team.name,
            leader_uuid=team.leader_uuid,
            co_leader_uuid=team.co_leader_uuid,
            expiration_date=team.expiration_date,
            created_at=team.created_at,
            last_updated=team.last_updated,
            members_count=len(team.members),
        ),
    )


@router.patch("/{uuid}/update", response_model=ApiResponse[TeamUpdateData])
def update_team(
    uuid: UUID, payload: TeamUpdate, db: DatabaseSession, actor: RequestingActor
):
    team = db.get(Team, uuid)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found."
        )

    check_permissions(db, actor, uuid, False)

    if payload.name and payload.name != team.name:
        if db.scalar(select(Team).where(Team.name == payload.name)):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A team with this name already exists.",
            )
        team.name = payload.name

    if payload.expiration_date:
        team.expiration_date = payload.expiration_date

    if payload.leader_uuid and payload.leader_uuid != team.leader_uuid:
        new_leader_uuid = payload.leader_uuid
        if not db.get(Volunteer, new_leader_uuid):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New leader volunteer not found.",
            )

        # Update old leader's role to member
        old_leader_member = db.scalar(
            select(TeamMember).where(
                TeamMember.team_uuid == uuid,
                TeamMember.volunteer_uuid == team.leader_uuid,
            )
        )
        if old_leader_member:
            old_leader_member.role = TeamMemberRole.member
            db.add(old_leader_member)

        team.leader_uuid = new_leader_uuid

        # Update new leader's role
        new_leader_member = db.scalar(
            select(TeamMember).where(
                TeamMember.team_uuid == uuid,
                TeamMember.volunteer_uuid == new_leader_uuid,
            )
        )
        if new_leader_member:
            new_leader_member.role = TeamMemberRole.leader
            db.add(new_leader_member)
        else:
            db.add(
                TeamMember(
                    team_uuid=uuid,
                    volunteer_uuid=new_leader_uuid,
                    role=TeamMemberRole.leader,
                )
            )

    if payload.co_leader_uuid and payload.co_leader_uuid != team.co_leader_uuid:
        new_co_leader_uuid = payload.co_leader_uuid
        if not db.get(Volunteer, new_co_leader_uuid):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New co-leader volunteer not found.",
            )

        # Update old co-leader's role to member
        if team.co_leader_uuid:
            old_co_leader_member = db.scalar(
                select(TeamMember).where(
                    TeamMember.team_uuid == uuid,
                    TeamMember.volunteer_uuid == team.co_leader_uuid,
                )
            )
            if old_co_leader_member:
                old_co_leader_member.role = TeamMemberRole.member
                db.add(old_co_leader_member)

        team.co_leader_uuid = new_co_leader_uuid

        # Update new co-leader's role
        if new_co_leader_uuid:
            new_co_leader_member = db.scalar(
                select(TeamMember).where(
                    TeamMember.team_uuid == uuid,
                    TeamMember.volunteer_uuid == new_co_leader_uuid,
                )
            )
            if new_co_leader_member:
                new_co_leader_member.role = TeamMemberRole.co_leader
                db.add(new_co_leader_member)
            else:
                db.add(
                    TeamMember(
                        team_uuid=uuid,
                        volunteer_uuid=new_co_leader_uuid,
                        role=TeamMemberRole.co_leader,
                    )
                )

    db.add(team)
    db.commit()
    db.refresh(team)

    return ApiResponse(
        message="Team updated successfully.", data=TeamUpdateData(team_uuid=team.uuid)
    )


@router.get(
    "/{uuid}/members",
    summary="Get All Team Members",
    response_model=ApiResponse[Sequence[TeamMemberRead]],
)
def get_all_team_members(uuid: UUID, db: DatabaseSession, actor: RequestingActor):
    team = db.get(Team, uuid)
    if not team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Team Not Found")

    check_permissions(db, actor, uuid, False)

    return ApiResponse(
        message="Fetched members successfully",
        data=[TeamMemberRead.model_validate(member) for member in team.members],
    )


@router.get("/{uuid}/members/{member_uuid}", response_model=ApiResponse[TeamMemberRead])
def get_team_member(
    uuid: UUID, member_uuid: UUID, db: DatabaseSession, actor: RequestingActor
):
    team = db.get(Team, uuid)
    if not team:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Team Not Found")

    check_permissions(db, actor, uuid, False)

    member_to_get = db.scalar(
        select(TeamMember).where(
            TeamMember.team_uuid == uuid, TeamMember.volunteer_uuid == member_uuid
        )
    )
    if not member_to_get:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found."
        )
    return ApiResponse(
        message="Team member retrieved successfully",
        data=TeamMemberRead.model_validate(member_to_get),
    )


@router.post("/{uuid}/members/add", response_model=ApiResponse[TeamMemberCreateData])
def add_team_member(
    uuid: UUID, payload: TeamMemberCreate, db: DatabaseSession, actor: RequestingActor
):
    team = db.get(Team, uuid)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found."
        )

    check_permissions(db, actor, uuid, True)

    volunteer = db.get(Volunteer, payload.volunteer_uuid)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Volunteer not found."
        )

    existing_member = db.scalar(
        select(TeamMember)
        .join(Team)
        .where(
            TeamMember.team_uuid == uuid,
            TeamMember.volunteer_uuid == payload.volunteer_uuid,
            Team.expiration_date >= date.today(),
        )
        .order_by(desc(TeamMember.joined_at))
    )
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Volunteer is already a member of the team.",
        )

    new_team_member = TeamMember(
        team_uuid=uuid, volunteer_uuid=payload.volunteer_uuid, role=payload.role
    )
    db.add(new_team_member)
    db.commit()

    return ApiResponse(
        message="Volunteer added to team.",
        data=TeamMemberCreateData(
            team_uuid=uuid, volunteer_uuid=payload.volunteer_uuid
        ),
    )


@router.delete(
    "/{uuid}/members/{member_uuid}/remove",
    response_model=ApiResponse[TeamMemberDeleteData],
)
def remove_team_member(
    uuid: UUID, member_uuid: UUID, db: DatabaseSession, actor: RequestingActor
):
    team = db.get(Team, uuid)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Team not found."
        )

    # Authorization check
    is_admin = isinstance(actor, Admin)
    current_member = None
    if not is_admin:
        current_member = db.scalar(
            select(TeamMember).where(
                TeamMember.team_uuid == uuid, TeamMember.volunteer_uuid == actor.uuid
            )
        )

    if not (
        is_admin
        or (
            current_member
            and current_member.role in [TeamMemberRole.leader, TeamMemberRole.co_leader]
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User lacks permission to remove members.",
        )

    member_to_remove = db.scalar(
        select(TeamMember).where(
            TeamMember.team_uuid == uuid, TeamMember.volunteer_uuid == member_uuid
        )
    )
    if not member_to_remove:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found in the team.",
        )

    # if member to remove is the team leader and team has no co leader, raise a bad request
    if member_to_remove.role == TeamMemberRole.leader and not team.co_leader_uuid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team leader cannot be removed without a co-leader.",
        )

    # Co-leader cannot remove the leader
    if (
        current_member
        and current_member.role == TeamMemberRole.co_leader
        and member_to_remove.role == TeamMemberRole.leader
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Co-leader cannot remove the leader.",
        )

    # Leader can't be removed by anyone except an admin
    if member_to_remove.role == TeamMemberRole.leader and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Leader can only be removed by an admin.",
        )

    db.delete(member_to_remove)

    # if member to remove is the co-leader, then set co leader uuid to none
    if member_to_remove.role == TeamMemberRole.co_leader:
        team.co_leader_uuid = None
        db.add(team)

    # if leader is removed, co leader is the leader
    if member_to_remove.role == TeamMemberRole.leader:
        assert team.co_leader_uuid is not None
        team.leader_uuid = team.co_leader_uuid
        team.co_leader_uuid = None
        db.add(team)

    db.commit()

    return ApiResponse(
        message="Member removed from team.",
        data=TeamMemberDeleteData(team_uuid=uuid, volunteer_uuid=member_uuid),
    )


router.include_router(team_plan_router)
