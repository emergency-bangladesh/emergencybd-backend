from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import select

from ...database.models.account import Admin
from ...database.models.team import TeamMember, TeamMemberRole
from ..dependencies import DatabaseSession, LoggedInAccount


def check_permissions(
    db: DatabaseSession,
    account: LoggedInAccount,
    team_uuid: UUID,
    leader_or_co_leader_only: bool = False,
):
    is_admin = db.get(Admin, account.uuid)
    if is_admin:
        return True

    team_member = db.scalar(
        select(TeamMember).where(
            TeamMember.team_uuid == team_uuid, TeamMember.volunteer_uuid == account.uuid
        )
    )

    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team.",
        )

    if leader_or_co_leader_only and team_member.role not in [
        TeamMemberRole.leader,
        TeamMemberRole.co_leader,
    ]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team leaders or co-leaders can perform this action.",
        )

    return True
