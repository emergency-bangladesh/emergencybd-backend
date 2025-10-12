from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import select

from ...database.models import (
    ActivityUpdate,
    Issue,
    PlanActivity,
    Team,
    TeamMember,
    TeamPlan,
    Volunteer,
    VolunteerIssueResponse,
)
from ...utils.time import get_utc_time
from ..dependencies import DatabaseSession


# Data classes for type safety
class VolunteerActivity(BaseModel):
    title: str
    description: str
    time: datetime


class TeamJoinActivity(VolunteerActivity):
    team_name: str
    role: str


class IssueResponseActivity(VolunteerActivity):
    issue_uuid: UUID
    issue_status: str
    response_status: Optional[str]


class ActivityUpdateActivity(VolunteerActivity):
    activity_title: str
    activity_details: str
    plan_title: str


class LeadershipActivity(VolunteerActivity):
    team_name: str
    role: str


class ProfileUpdateActivity(VolunteerActivity):
    update_type: str


# Factory functions to create activity instances
def create_team_join_activity(team_member: TeamMember, team: Team) -> TeamJoinActivity:
    return TeamJoinActivity(
        title=f"Joined {team.name} team",
        description=f"Joined as {team_member.role.value}",
        time=team_member.joined_at,
        team_name=team.name,
        role=team_member.role.value,
    )


def create_issue_response_activity(
    response: VolunteerIssueResponse, issue: Issue
) -> IssueResponseActivity:
    status_text = f" and marked it as {response.status_mark.value}" if response.status_mark else ""
    return IssueResponseActivity(
        title="Responded to emergency issue",
        description=f"Responded to issue #{issue.uuid} ({issue.status.value}){status_text}",
        time=response.created_at,
        issue_uuid=issue.uuid,
        issue_status=issue.status.value,
        response_status=response.status_mark.value if response.status_mark else None,
    )


def create_activity_update_activity(
    update: ActivityUpdate, activity: PlanActivity, plan: TeamPlan
) -> ActivityUpdateActivity:
    return ActivityUpdateActivity(
        title=f"Updated activity: {update.title}",
        description=f"Provided update for '{activity.details}' in {plan.title} plan",
        time=update.created_at,
        activity_title=update.title,
        activity_details=activity.details,
        plan_title=plan.title,
    )


def create_leadership_activity(team: Team, volunteer_uuid: UUID) -> LeadershipActivity:
    role = "leader" if team.leader_uuid == volunteer_uuid else "co-leader"
    return LeadershipActivity(
        title=f"Became {role} of {team.name}",
        description=f"Started as {role} of team {team.name}",
        time=team.created_at,
        team_name=team.name,
        role=role,
    )


def create_profile_update_activity(volunteer: Volunteer) -> ProfileUpdateActivity:
    return ProfileUpdateActivity(
        title="Updated profile information",
        description="Made changes to volunteer profile",
        time=volunteer.last_updated,
        update_type="profile_update",
    )


def get_volunteer_recent_activities(
    db: DatabaseSession, volunteer: Volunteer, months_back: int = 3
) -> List[VolunteerActivity]:
    """
    Get a volunteer's recent activities from the last N months.

    Args:
        session: Database session
        volunteer_uuid: UUID of the volunteer
        months_back: Number of months to look back (default: 3)

    Returns:
        List of type-safe activity objects
    """
    volunteer_uuid = volunteer.uuid
    cutoff_date = get_utc_time() - timedelta(days=30 * months_back)
    activities: List[VolunteerActivity] = []

    # 1. Team joining activities
    team_member_stmt = (
        select(TeamMember, Team)
        .select_from(TeamMember)
        .join(Team)
        .where(
            TeamMember.volunteer_uuid == volunteer_uuid,
            TeamMember.joined_at >= cutoff_date,
        )
    )
    team_member_results = db.exec(team_member_stmt).all()

    for team_member, team in team_member_results:
        activities.append(create_team_join_activity(team_member, team))

    # 2. Issue response activities
    issue_response_stmt = (
        select(VolunteerIssueResponse, Issue)
        .select_from(VolunteerIssueResponse)
        .join(Issue)
        .where(
            VolunteerIssueResponse.volunteer_uuid == volunteer_uuid,
            VolunteerIssueResponse.created_at >= cutoff_date,
        )
    )
    issue_response_results = db.exec(issue_response_stmt).all()

    for response, issue in issue_response_results:
        activities.append(create_issue_response_activity(response, issue))

    # 3. Activity update contributions
    activity_update_stmt = (
        select(ActivityUpdate, PlanActivity, TeamPlan)
        .select_from(ActivityUpdate)
        .join(PlanActivity)
        .join(TeamPlan)
        .where(
            ActivityUpdate.volunteer_uuid == volunteer_uuid,
            ActivityUpdate.created_at >= cutoff_date,
        )
    )
    activity_update_results = db.exec(activity_update_stmt).all()

    for update, activity, plan in activity_update_results:
        activities.append(create_activity_update_activity(update, activity, plan))

    # 4. Team leadership activities
    team_leadership_stmt = select(Team).where(
        ((Team.leader_uuid == volunteer_uuid) | (Team.co_leader_uuid == volunteer_uuid))
        & (Team.created_at >= cutoff_date)
    )
    leadership_teams = db.exec(team_leadership_stmt).all()

    for team in leadership_teams:
        activities.append(create_leadership_activity(team, volunteer_uuid))

    # 5. Volunteer profile updates
    volunteer_updates_stmt = select(Volunteer).where(
        Volunteer.uuid == volunteer_uuid,
        Volunteer.last_updated >= cutoff_date,
        Volunteer.last_updated
        > Volunteer.created_at + timedelta(minutes=1),  # Not initial creation
    )
    volunteer_updates = db.exec(volunteer_updates_stmt).all()

    for volunteer in volunteer_updates:
        activities.append(create_profile_update_activity(volunteer))

    # Sort all activities by time (newest first)
    activities.sort(key=lambda x: x.time, reverse=True)

    return activities
