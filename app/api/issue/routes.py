from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import Session, and_, func, or_, select

from ...core.config import config
from ...core.security import hash_password
from ...database.models.account import Account, Admin, User
from ...database.models.issue import (
    BloodDonationIssue,
    Issue,
    IssueCategory,
    IssueResponseStatus,
    IssueStatus,
    LostAndFoundIssue,
    VolunteerIssueResponse,
)
from ...database.models.volunteer import Volunteer, VolunteerStatus
from ...services.email import send_email
from ...utils.password import generate_random_password
from ..dependencies import (
    CurrentAdmin,
    CurrentVolunteer,
    DatabaseSession,
    RequestingActor,
)
from ..global_schema import ApiResponse
from .schema import (
    BloodDonationIssueCreate,
    BloodDonationIssueRead,
    GetIssuesData,
    IssueCreateData,
    IssueDeleteData,
    IssueResponseCreateData,
    IssueResponseRead,
    IssueUpdateData,
    LostAndFoundIssueCreate,
    LostAndFoundIssueRead,
)

router = APIRouter(prefix="/issues", tags=["Issues Management Routes"])


@router.get(
    "/",
    summary="Get a list of all issues",
    response_model=ApiResponse[GetIssuesData],
)
def get_all_issues(
    db: DatabaseSession, skip: int = 0, limit: int = 100
) -> ApiResponse[GetIssuesData]:
    # Fetch paginated issues
    issues = db.exec(select(Issue).offset(skip).limit(limit)).all()

    # Count total issues
    total_issues = db.exec(select(func.count()).select_from(Issue)).one()

    return ApiResponse(
        message="Issues retrieved successfully",
        data=GetIssuesData(
            issues=issues,
            has_more=((skip + len(issues)) < total_issues),
        ),
    )


@router.get(
    "/{uuid}",
    summary="Get details of a specific issue",
    response_model=ApiResponse[Issue],
)
def get_issue_details(uuid: UUID, db: DatabaseSession) -> ApiResponse[Issue]:
    issue = db.get(Issue, uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return ApiResponse(message="Issue retrieved successfully", data=issue)


@router.get(
    "/blood_donation/{uuid}",
    summary="Get details of a blood donation issue",
    response_model=ApiResponse[BloodDonationIssueRead],
)
def get_blood_donation_issue_details(
    uuid: UUID, db: DatabaseSession
) -> ApiResponse[BloodDonationIssueRead]:
    issue = db.get(Issue, uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issue_detail = db.get(BloodDonationIssue, uuid)
    if not issue_detail:
        raise HTTPException(
            status_code=404, detail="Blood donation issue details not found"
        )
    user = db.get(User, issue.account_uuid)
    volunteer = db.get(Volunteer, issue.account_uuid)

    if user:
        contact_person_name = user.full_name
    else:
        assert volunteer
        contact_person_name = volunteer.full_name

    data = BloodDonationIssueRead(
        issue_uuid=issue.uuid,
        status=issue.status,
        created_at=issue.created_at,
        last_updated=issue.last_updated,
        account_uuid=issue.account_uuid,
        phone_number=issue.account.phone_number,
        email_address=issue.account.email_address,
        patient_name=issue_detail.patient_name,
        blood_group=issue_detail.blood_group,
        amount_bag=issue_detail.amount_bag,
        hospital_name=issue_detail.hospital_name,
        district=issue_detail.district,
        upazila=issue_detail.upazila,
        instructions=issue_detail.instructions,
        contact_person_name=contact_person_name,
        emergency_phone_number=issue.emergency_phone_number,
    )

    return ApiResponse(
        message="Blood donation issue details retrieved successfully", data=data
    )


@router.get(
    "/lost_and_found/{uuid}",
    summary="Get details of a lost and found issue",
    response_model=ApiResponse[LostAndFoundIssueRead],
)
def get_lost_and_found_issue_details(
    uuid: UUID, db: DatabaseSession
) -> ApiResponse[LostAndFoundIssueRead]:
    issue = db.get(Issue, uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issue_detail = db.get(LostAndFoundIssue, uuid)
    if not issue_detail:
        raise HTTPException(
            status_code=404, detail="Lost and found issue details not found"
        )

    user = db.get(User, issue.account_uuid)
    volunteer = db.get(Volunteer, issue.account_uuid)

    if user:
        contact_person_name = user.full_name
    else:
        assert volunteer
        contact_person_name = volunteer.full_name

    data = LostAndFoundIssueRead(
        issue_uuid=issue.uuid,
        status=issue.status,
        created_at=issue.created_at,
        last_updated=issue.last_updated,
        account_uuid=issue.account_uuid,
        phone_number=issue.account.phone_number,
        email_address=issue.account.email_address,
        name_of_person=issue_detail.name_of_person,
        age_of_person=issue_detail.age_of_person,
        last_seen_location=issue_detail.last_seen_location,
        details=issue_detail.details,
        district=issue_detail.district,
        upazila=issue_detail.upazila,
        blood_group=issue_detail.blood_group,
        occupation=issue_detail.occupation,
        contact_person_name=contact_person_name,
        emergency_phone_number=issue.emergency_phone_number,
    )

    return ApiResponse(
        message="Lost and found issue details retrieved successfully", data=data
    )


@router.get(
    "/{uuid}/responses",
    summary="Get volunteer responses for a specific issue",
    response_model=ApiResponse[list[IssueResponseRead]],
)
def get_volunteer_responses_of_issue(uuid: UUID, db: DatabaseSession):
    issue = db.get(Issue, uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return ApiResponse(
        message="Volunteer responses retrieved successfully",
        data=[
            IssueResponseRead.model_validate(response)
            for response in issue.volunteer_responses
        ],
    )


def _create_user_account(
    db: Session, full_name: str, phone_number: str, email_address: str
) -> Account:
    pin = generate_random_password(config.issue_pin_length)
    account = Account(
        phone_number=phone_number,
        email_address=email_address,
        password_hash=hash_password(pin),
    )
    db.add(account)
    db.flush()

    user = User(uuid=account.uuid, full_name=full_name)
    db.add(user)

    db.commit()
    db.refresh(account)
    db.refresh(user)

    send_email(
        mailto=email_address,
        subject="Your Temporary Password for Emergency BD Account",
        body=f"""Hello {full_name},

We’ve generated a temporary password for your Emergency BD account. You can use it to log in and then set a new, secure password.

Temporary Password: {pin}

For your security, please change this password immediately after logging in.

How to reset your password:

1. Log in with the temporary password.
2. Go to Settings > Change Password.
3. Enter your new password and save.

If you did not request this password reset, please contact our team immediately.

Stay safe,
Team Emergency Bangladesh
project.emergencybd@gmail.com | https://emergencybd.com
""",
        content_type="plain",
    )
    return account


@router.post(
    "/blood_donation/new",
    summary="Create a new blood donation issue",
    response_model=ApiResponse[IssueCreateData],
)
def create_blood_donation_issue(payload: BloodDonationIssueCreate, db: DatabaseSession):
    account = db.scalar(
        select(Account).where(
            Account.email_address == payload.email_address,
            Account.phone_number == payload.phone_number,
        )
    )
    if not account:
        account = _create_user_account(
            db, payload.full_name, payload.phone_number, payload.email_address
        )

    issue = Issue(
        account_uuid=account.uuid,
        emergency_phone_number=payload.emergency_phone_number,
        category=IssueCategory.blood_donation,
    )
    db.add(issue)
    db.flush()

    blood_donation_issue = BloodDonationIssue(
        uuid=issue.uuid,
        **payload.model_dump(
            exclude={
                "full_name",
                "emergency_phone_number",
                "phone_number",
                "email_address",
            }
        ),
    )
    db.add(blood_donation_issue)
    db.commit()
    db.refresh(issue)

    send_email(
        payload.email_address,
        "Your Issue Has Been Created on Emergency Bangladesh",
        f"""
Hello {payload.full_name},

Thank you for reaching out to Emergency BD. Your issue has been successfully created and our team (along with volunteers) will start looking into it right away.

Issue Details:
Issue UUID: {issue.uuid}
Category: {issue.category.value}
Status: {issue.status}
Created At: {issue.created_at}
Preview: https://emergencybd.com/issues/{issue.uuid}

We will keep you updated on the progress. If you need to provide more details, please reply to this email or contact our team.

If you believe this issue was created by mistake, please let us know immediately.

Stay safe,
Team Emergency Bangladesh
project.emergencybd@gmail.com | https://emergencybd.com
""",
        "plain",
    )

    matched_volunteers = db.exec(
        select(Volunteer).where(
            and_(
                or_(
                    Volunteer.current_district == payload.district,
                    Volunteer.permanent_district == payload.district,
                ),
                or_(
                    Volunteer.current_upazila == payload.upazila,
                    Volunteer.permanent_upazila == payload.upazila,
                ),
                Volunteer.status
                not in [VolunteerStatus.rejected, VolunteerStatus.terminated],
                Volunteer.blood_group == payload.blood_group,
            )
        )
    ).all()

    for volunteer in matched_volunteers:
        send_email(
            volunteer.account.email_address,
            f"New Blood Donation Issue at {payload.hospital_name} | Emergency Bangladesh",
            f"""
Hello {volunteer.full_name},

We have received a new blood donation issue at {payload.hospital_name} in {payload.district} district, {payload.upazila} upazila.

Details:
Patient Name: {payload.patient_name}
Blood Group: {payload.blood_group}
Amount of Bag: {payload.amount_bag}
Address: {payload.hospital_name}, {payload.district}, {payload.upazila}
Instructions: {payload.instructions}

Contact:
Name: {payload.full_name}
Phone Number: {payload.phone_number}
Emergency Phone Number: {payload.emergency_phone_number}
Email Address: {payload.email_address}

Please check the issue on Emergency Bangladesh: https://emergencybd.com/issues/{issue.uuid}

Stay safe,
Team Emergency Bangladesh
project.emergencybd@gmail.com | https://emergencybd.com
""",
            "plain",
        )

    return ApiResponse(
        message="Issue reported. A PIN has been sent to your email for future updates.",
        data=IssueCreateData(issue_uuid=issue.uuid),
    )


@router.post(
    "/lost_and_found/new",
    summary="Create a new lost and found issue",
    response_model=ApiResponse[IssueCreateData],
)
def create_lost_and_found_issue(payload: LostAndFoundIssueCreate, db: DatabaseSession):
    account = db.scalar(
        select(Account).where(
            Account.email_address == payload.email_address,
            Account.phone_number == payload.phone_number,
        )
    )

    if not account:
        account = _create_user_account(
            db, payload.full_name, payload.phone_number, payload.email_address
        )

    issue = Issue(
        account_uuid=account.uuid,
        emergency_phone_number=payload.emergency_phone_number,
        category=IssueCategory.lost_and_found,
    )
    db.add(issue)
    db.flush()

    lost_and_found_issue = LostAndFoundIssue(
        uuid=issue.uuid,
        **payload.model_dump(
            exclude={
                "full_name",
                "emergency_phone_number",
                "phone_number",
                "email_address",
            }
        ),
    )
    db.add(lost_and_found_issue)

    db.commit()
    db.refresh(issue)

    send_email(
        payload.email_address,
        "Your Issue Has Been Created on Emergency Bangladesh",
        f"""
Hello {payload.full_name},

Thank you for reaching out to Emergency BD. Your issue has been successfully created and our team (along with volunteers) will start looking into it right away.

Issue Details:
Issue UUID: {issue.uuid}
Category: {issue.category.value}
Status: {issue.status}
Created At: {issue.created_at}
Preview: https://emergencybd.com/issues/{issue.uuid}

We will keep you updated on the progress. If you need to provide more details, please reply to this email or contact our team.

If you believe this issue was created by mistake, please let us know immediately.

Stay safe,
Team Emergency Bangladesh
project.emergencybd@gmail.com | https://emergencybd.com
""",
        "plain",
    )

    matched_volunteers = db.exec(
        select(Volunteer).where(
            Volunteer.status
            not in [VolunteerStatus.rejected, VolunteerStatus.terminated],
        )
    )

    for volunteer in matched_volunteers:
        send_email(
            volunteer.account.email_address,
            "New Lost and Found Issue | Emergency Bangladesh",
            f"""
URGENT!!! A PERSON IS LOST!!!


Details:
Name: {payload.name_of_person}
Age: {payload.age_of_person}
Last Seen Location: {payload.last_seen_location}, {payload.district}, {payload.upazila}
Details: {payload.details}

Contact:
Name: {payload.full_name}
Phone Number: {payload.phone_number}
Emergency Phone Number: {payload.emergency_phone_number}
Email Address: {payload.email_address}

Please check the issue on Emergency Bangladesh: https://emergencybd.com/issues/{issue.uuid}

Stay safe,
Team Emergency Bangladesh
project.emergencybd@gmail.com | https://emergencybd.com
""",
            "plain",
        )

    return ApiResponse(
        message="Issue reported. A PIN has been sent to your email for future updates.",
        data=IssueCreateData(issue_uuid=issue.uuid),
    )


@router.post(
    "/{uuid}/respond",
    summary="Create or update a volunteer's response to an issue",
    response_model=ApiResponse[IssueResponseCreateData],
)
def create_or_update_issue_response(
    uuid: UUID,
    db: DatabaseSession,
    volunteer: CurrentVolunteer,
    status_mark: IssueResponseStatus | None = Query(
        None, description="The status mark for the volunteer's response"
    ),
):
    issue = db.get(Issue, uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issuer = db.get(User, issue.account_uuid)
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")

    existing_response = db.scalar(
        select(VolunteerIssueResponse).where(
            VolunteerIssueResponse.issue_uuid == uuid,
            VolunteerIssueResponse.volunteer_uuid == volunteer.uuid,
        )
    )

    if existing_response:
        existing_response.status_mark = status_mark
        db.add(existing_response)
        response_to_return = existing_response
    else:
        new_response = VolunteerIssueResponse(
            issue_uuid=uuid, volunteer_uuid=volunteer.uuid, status_mark=status_mark
        )
        db.add(new_response)
        response_to_return = new_response

    db.commit()
    db.refresh(response_to_return)

    if status_mark:
        responses = db.exec(
            select(VolunteerIssueResponse).where(
                VolunteerIssueResponse.issue_uuid == uuid,
                VolunteerIssueResponse.status_mark == status_mark,
            )
        ).all()

        if len(responses) >= config.issue_update_min_volunteer_responses:
            issue.status = IssueStatus(status_mark.value)
            db.add(issue)
            db.commit()
            db.refresh(issue)

            send_email(
                issue.account.email_address,
                "Your Issue Has Been Updated on Emergency Bangladesh",
                f"""
Hello {issuer.full_name},

Your issue has been updated to {issue.status.value}.

Issue Details:
Issue UUID: {issue.uuid}
Category: {issue.category.value}
Status: {issue.status}
Created At: {issue.created_at}
Preview: https://emergencybd.com/issues/{issue.uuid}

We will keep you updated on the progress. If you need to provide more details, please reply to this email or contact our team.

If you believe this issue was created by mistake, please let us know immediately.

Stay safe,
Team Emergency Bangladesh
project.emergencybd@gmail.com | https://emergencybd.com
""",
                "plain",
            )
        else:
            send_email(
                issue.account.email_address,
                f"Waiting for approval for your issue to be marked {status_mark.value}",
                f"""
Hello {issuer.full_name},

{volunteer.full_name} has responded to your issue.
Contact:
Name: {volunteer.full_name}
Phone Number: {volunteer.account.phone_number}
Email Address: {volunteer.account.email_address}
Volunteer Profile: https://emergencybd.com/volunteers/{volunteer.uuid}

Issue Details:
Issue UUID: {issue.uuid}
Category: {issue.category.value}
Status: {issue.status}
Created At: {issue.created_at}
Preview: https://emergencybd.com/issues/{issue.uuid}

We will keep you updated on the progress. If you need to provide more details, please reply to this email or contact our team.

If you believe this issue was created by mistake, please let us know immediately.

Stay safe,
Team Emergency Bangladesh
project.emergencybd@gmail.com | https://emergencybd.com
""",
                "plain",
            )
            pass
    else:
        send_email(
            issue.account.email_address,
            f"{volunteer.full_name} Has Responded to Your Issue on Emergency Bangladesh",
            f"""
Hello {issuer.full_name},

{volunteer.full_name} has responded to your issue.
Contact:
Name: {volunteer.full_name}
Phone Number: {volunteer.account.phone_number}
Email Address: {volunteer.account.email_address}
Volunteer Profile: https://emergencybd.com/volunteer/{volunteer.uuid}

Issue Details:
Issue UUID: {issue.uuid}
Category: {issue.category.value}
Status: {issue.status}
Created At: {issue.created_at}
Preview: https://emergencybd.com/issues/{issue.uuid}

We will keep you updated on the progress. If you need to provide more details, please reply to this email or contact our team.

If you believe this issue was created by mistake, please let us know immediately.

Stay safe,
Team Emergency Bangladesh
project.emergencybd@gmail.com | https://emergencybd.com
""",
            "plain",
        )
    return ApiResponse(
        message="Response recorded.",
        data=IssueResponseCreateData(
            issue=uuid,
            volunteer_uuid=volunteer.uuid,
            status_mark=status_mark,
        ),
    )


@router.patch(
    "/{uuid}/update/status/{issue_status}",
    summary="Update a issue's status",
    response_model=ApiResponse[IssueUpdateData],
)
def update_issue_status(
    uuid: UUID,
    db: DatabaseSession,
    actor: RequestingActor,
    issue_status: IssueStatus,
):
    issue = db.get(Issue, uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    is_admin = isinstance(actor, Admin)
    is_creator = not is_admin and issue.account_uuid == actor.uuid

    if not (is_admin or is_creator):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
        )

    issuer = db.get(User, issue.account_uuid)
    if not issuer:
        raise HTTPException(status_code=404, detail="Issuer not found")

    issue.status = issue_status
    db.add(issue)
    db.commit()
    db.refresh(issue)

    send_email(
        issue.account.email_address,
        "Your Issue Has Been Updated to "
        + issue.status.value
        + " on Emergency Bangladesh",
        f"""
Hi {issuer.full_name},

Your issue has been updated to {issue.status.value}.

Issue Details:
Issue UUID: {issue.uuid}
Category: {issue.category.value}
Status: {issue.status}
Created At: {issue.created_at}
Preview: https://emergencybd.com/issues/{issue.uuid}

If you need to provide more details, please reply to this email or contact our team.

If you believe this issue was created by mistake, please let us know immediately.

Stay safe,
Team Emergency Bangladesh
project.emergencybd@gmail.com | https://emergencybd.com
""",
        "plain",
    )
    return ApiResponse(
        message="Issue status updated.",
        data=IssueUpdateData(issue_uuid=issue.uuid, status=issue.status),
    )


@router.delete(
    "/{uuid}/delete",
    summary="Delete a issue report record from database",
    response_model=ApiResponse[IssueDeleteData],
)
def delete_issue(uuid: UUID, db: DatabaseSession, admin: CurrentAdmin):
    issue = db.get(Issue, uuid)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    db.delete(issue)
    db.commit()

    return ApiResponse(
        message="Issue deleted successfully.", data=IssueDeleteData(issue_uuid=uuid)
    )
