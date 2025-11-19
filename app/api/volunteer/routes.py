from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlmodel import desc, select

from ...core.config import config
from ...core.security import hash_password
from ...database.models.account import Account, AccountStatus, User
from ...database.models.identifier import BRN, NID
from ...database.models.volunteer import (
    Volunteer,
    VolunteerIdentifierType,
    VolunteerStatus,
)
from ...services.brn import encrypt_brn, generate_brn_hmac
from ...services.dob import encrypt_dob
from ...services.email import send_email
from ...services.nid import encrypt_nid, generate_nid_hmac
from ...utils.time import get_utc_time
from ..dependencies import CurrentAdmin, CurrentVolunteer, DatabaseSession
from ..global_schema import ApiResponse
from .get_volunteer_recent_activities import (
    VolunteerActivity,
    get_volunteer_recent_activities,
)
from .schema import (
    TeamInformation,
    VolunteerCreate,
    VolunteerCreateData,
    VolunteerDetailResponse,
    VolunteerUpdate,
    VolunteerUUID,
)

router = APIRouter(prefix="/volunteers", tags=["volunteers"])


# Get all volunteers
@router.get("/", response_model=ApiResponse[list[VolunteerDetailResponse]])
def get_volunteers(
    db: DatabaseSession,
    _: CurrentAdmin,
    skip: int = 0,
    limit: int = 100,
):
    stmt = (
        select(Volunteer).order_by(desc(Volunteer.created_at)).offset(skip).limit(limit)
    )
    volunteers = db.exec(stmt).all()
    now = get_utc_time()

    volunteer_details: list[VolunteerDetailResponse] = []
    for v in volunteers:
        active_team_memberships = [
            t for t in v.team_memberships if t.team.expiration_date >= now.date()
        ]
        volunteer_details.append(
            VolunteerDetailResponse(
                volunteer_uuid=v.uuid,
                full_name=v.full_name,
                email_address=v.account.email_address,
                phone_number=v.account.phone_number,
                permanent_district=v.permanent_district,
                permanent_upazila=v.permanent_upazila,
                current_district=v.current_district,
                current_upazila=v.current_upazila,
                blood_group=v.blood_group,
                status=v.status.value,
                created_at=v.created_at,
                last_updated=v.last_updated,
                issue_responses=len(v.issue_responses),
                identifier_type=v.identifier_type.value,
                current_team_information=TeamInformation(
                    team_name=active_team_memberships[0].team.name,
                    role=active_team_memberships[0].role,
                    team_uuid=active_team_memberships[0].team.uuid,
                )
                if active_team_memberships
                else None,
                unique_id=v.unique_id,
            )
        )

    return ApiResponse(
        message="Volunteers retrieved successfully",
        data=volunteer_details,
    )


## helper function
def _send_email_about_volunteer_data_received(volunteer: Volunteer) -> None:
    send_email(
        volunteer.account.email_address,
        "Your Volunteer Registration is Received",
        f"""Hello {volunteer.full_name},

Thank you for registering as a volunteer. We have successfully received your information.

ACCOUND STATUS: PENDING
VOLUNTEER UNIQUE ID : {volunteer.unique_id}

An admin will review and validate your details shortly.

Once the verification is complete, you will receive a confirmation email, and your account will be marked as Verified.

We truly appreciate your patience and your willingness to support our mission.

Best regards,
Team Emergency Bangladesh
{config.smtp_mailfrom}
""",
        "plain",
    )


# Create a volunteer
@router.post(
    "/new",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[VolunteerCreateData],
)
def create_volunteer(payload: VolunteerCreate, db: DatabaseSession):
    # Check if an account with the given phone number or email already exists
    account = db.scalar(
        select(Account).where(
            (Account.phone_number == payload.phone_number)
            | (Account.email_address == payload.email_address)
        )
    )
    if not account:  # Create a new account if no existing account
        account = Account(
            phone_number=payload.phone_number,
            email_address=payload.email_address,
            password_hash=hash_password(payload.password),
        )
    else:  # account is present, update password
        account.password_hash = hash_password(payload.password)

    db.add(account)
    db.commit()
    db.refresh(account)

    id_type = (
        VolunteerIdentifierType.nid
        if payload.identifier_type == "nid"
        else VolunteerIdentifierType.brn
    )
    encrypted_dob = encrypt_dob(payload.birth_date)

    volunteer = Volunteer(
        uuid=account.uuid,
        full_name=payload.full_name,
        blood_group=payload.blood_group,
        identifier_type=id_type,
        permanent_upazila=payload.permanent_upazila,
        permanent_district=payload.permanent_district,
        current_upazila=payload.current_upazila,
        current_district=payload.current_district,
        birth_date_cipher=encrypted_dob.cipher,
        birth_date_nonce=encrypted_dob.nonce,
        gender=payload.gender,
    )

    db.add(volunteer)

    encrypted_identifier = (
        encrypt_nid(payload.identifier_value)
        if payload.identifier_type == "nid"
        else encrypt_brn(payload.identifier_value)
    )
    identifier = (
        NID(
            nid_cipher=encrypted_identifier.cipher,
            nid_nonce=encrypted_identifier.nonce,
            account_uuid=account.uuid,
            nid_hmac=generate_nid_hmac(payload.identifier_value),
        )
        if payload.identifier_type == "nid"
        else BRN(
            brn_cipher=encrypted_identifier.cipher,
            brn_nonce=encrypted_identifier.nonce,
            account_uuid=account.uuid,
            brn_hmac=generate_brn_hmac(payload.identifier_value),
        )
    )

    db.add(identifier)
    db.commit()
    db.refresh(volunteer)

    # delete the user data if account is an user object
    user = db.get(User, account.uuid)
    if user:
        db.delete(user)
        db.commit()

    _send_email_about_volunteer_data_received(volunteer)

    return ApiResponse(
        message="Volunteer registration submitted. Awaiting manual validation.",
        data=VolunteerCreateData(
            volunteer_uuid=volunteer.uuid, status=volunteer.status.value
        ),
    )


# Get a single volunteer by ID
@router.get("/{volunteer_uuid}", response_model=ApiResponse[VolunteerDetailResponse])
def get_volunteer_by_uuid(volunteer_uuid: UUID, db: DatabaseSession):
    v = db.scalar(select(Volunteer).where(Volunteer.uuid == volunteer_uuid))
    now = get_utc_time()
    if not v:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No volunteer verified or pending verification found",
        )
    if v.status in [VolunteerStatus.rejected, VolunteerStatus.terminated]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The volunteer account is either terminated or rejected",
        )

    active_team_memberships = [
        t for t in v.team_memberships if t.team.expiration_date >= now.date()
    ]

    return ApiResponse(
        message="Volunteer details retrieved successfully",
        data=VolunteerDetailResponse(
            volunteer_uuid=v.uuid,
            full_name=v.full_name,
            phone_number=v.account.phone_number,
            email_address=v.account.email_address,
            permanent_upazila=v.permanent_upazila,
            permanent_district=v.permanent_district,
            current_upazila=v.current_upazila,
            current_district=v.current_district,
            blood_group=v.blood_group,
            identifier_type=v.identifier_type.value,
            status=v.status.value,
            created_at=v.created_at,
            last_updated=v.last_updated,
            issue_responses=len(v.issue_responses),
            current_team_information=TeamInformation(
                team_name=active_team_memberships[0].team.name,
                role=active_team_memberships[0].role,
                team_uuid=active_team_memberships[0].team.uuid,
            )
            if active_team_memberships
            else None,
            unique_id=v.unique_id,
        ),
    )


@router.get(
    "/{volunteer_uuid}/recent-activities",
    summary="Get a volunteer's recent activities",
    response_model=ApiResponse[list[VolunteerActivity]],
)
def recent_volunteer_activities(
    volunteer_uuid: UUID, db: DatabaseSession
) -> ApiResponse[list[VolunteerActivity]]:
    volunteer = db.get(Volunteer, volunteer_uuid)
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No volunteer found",
        )
    recent_activities = get_volunteer_recent_activities(db, volunteer)

    return ApiResponse(
        message="Volunteer details retrieved successfully", data=recent_activities
    )


# Update a logged in volunteer
@router.patch("/update", response_model=ApiResponse[VolunteerUUID])
def update_volunteer(
    payload: VolunteerUpdate,
    db: DatabaseSession,
    volunteer: CurrentVolunteer,
):
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(volunteer, key, value)

    volunteer.last_updated = get_utc_time()

    db.add(volunteer)

    db.commit()
    db.refresh(volunteer)
    return ApiResponse(
        message="Volunteer profile updated successfully.",
        data=VolunteerUUID(volunteer_uuid=volunteer.uuid),
    )


# Update a volunteer with volunteer_uuid
@router.patch(
    "/{volunteer_uuid}/update/current-location",
    response_model=ApiResponse[VolunteerUUID],
)
def update_volunteer_by_uuid(
    volunteer_uuid: UUID, payload: VolunteerUpdate, db: DatabaseSession, _: CurrentAdmin
):
    volunteer = db.get(Volunteer, volunteer_uuid)
    if not volunteer:
        raise HTTPException(404, detail="Volunteer not found")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(volunteer, key, value)

    volunteer.last_updated = get_utc_time()

    db.add(volunteer)

    db.commit()
    db.refresh(volunteer)
    return ApiResponse(
        message="Volunteer profile updated successfully.",
        data=VolunteerUUID(volunteer_uuid=volunteer.uuid),
    )


def _send_pending_status_email(volunteer: Volunteer) -> None:
    send_email(
        volunteer.account.email_address,
        "Your Emergency Bangladesh Profile Status – Pending",
        f"""Dear {volunteer.full_name},

Your profile has been received and is currently under initial assessment again.
Please note your current account status below:

ACCOUNT STATUS: PENDING
VOLUNTEER UNIQUE ID : {volunteer.unique_id}

Possible Reasons:
- A high volume of submissions may be causing processing delays & mistakes.
- Verification is pending cross-check with NID/BRN records.
- Additional manual review is required due to unclear information.
- Your profile is waiting in the system queue.

You can find your profile here: https://emergencybd.com/volunteer/{volunteer.uuid}

We will notify you once verification is complete.
Kind regards,
Emergency Bangladesh Support Team
""",
        "plain",
    )


def _send_verified_status_email(volunteer: Volunteer) -> None:
    send_email(
        volunteer.account.email_address,
        "Your Emergency Bangladesh Profile Has Been Verified",
        f"""Dear {volunteer.full_name},

We are pleased to inform you that your profile has successfully passed all verification checks.

ACCOUNT STATUS: VERIFIED
VOLUNTEER UNIQUE ID : {volunteer.unique_id}

This means:
- All submitted details match official NID/BRN records.
- Identification documents were valid and clearly readable.
- Your profile picture meets platform requirements.
- Your email address and phone number were successfully verified.
- No inconsistencies were found during the review.

You can find your profile here: https://emergencybd.com/volunteer/{volunteer.uuid}

Please help raise awareness about Emergency Bangladesh within your network and encourage them to register. Together, we can drive meaningful and recognizable changes for the people of Bangladesh.

Your ID is now fully active and marked as verified by a verified tick beside your name on your profile. We are glad to get you within our network.

Warm regards,
Emergency Bangladesh Verification Unit""",
        "plain",
    )


def _send_rejected_status_email(volunteer: Volunteer) -> None:
    send_email(
        volunteer.account.email_address,
        "Your Emergency Bangladesh Verification Attempt Was Unsuccessful",
        f"""Dear {volunteer.full_name},

We regret to inform you that your profile could not be verified.

ACCOUNT STATUS: REJECTED
VOLUNTEER UNIQUE ID : {volunteer.unique_id}

Possible Reasons:
- NID/BRN number does not match the official record.
- Identification document photo is unclear or invalid.
- Personal details (name, birth date, blood group, etc.) do not match the document.
- Required information is missing or incorrect.
- Multiple inconsistent submissions were detected.
- Potential suspicion of fraudulent or duplicate identity.

Respectfully,
Emergency Bangladesh Verification Unit""",
        "plain",
    )


def _send_terminated_status_email(volunteer: Volunteer) -> None:
    send_email(
        volunteer.account.email_address,
        "Important Notice – Profile Terminated",
        f"""Dear {volunteer.full_name},

This message is to notify you that your Emergency Bangladesh profile has been permanently deactivated.

ACCOUNT STATUS: TERMINATED
VOLUNTEER UNIQUE ID : {volunteer.unique_id}

Possible Reasons:
- Submission of false or fraudulent documents.
- Violation of Emergency Bangladesh rules or misuse of services.
- Multiple rejections without correction or cooperation.
- Request from the account holder to close the profile.
- Involvement in suspicious or prohibited activities.

You can find your profile here: https://emergencybd.com/volunteer/{volunteer.uuid}

If you believe this action is an error, please contact support.

Sincerely,
Emergency Bangladesh Administration""",
        "plain",
    )


@router.patch(
    "/{volunteer_uuid}/update/status/{status}",
    response_model=ApiResponse[VolunteerUUID],
)
def update_volunteer_status(
    volunteer_uuid: UUID, status: VolunteerStatus, db: DatabaseSession, _: CurrentAdmin
):
    volunteer = db.get(Volunteer, volunteer_uuid)
    if not volunteer:
        raise HTTPException(404, detail="Volunteer not found")

    volunteer.status = status
    volunteer.last_updated = get_utc_time()

    db.add(volunteer)

    db.commit()
    db.refresh(volunteer)

    match status:
        case VolunteerStatus.pending:
            _send_pending_status_email(volunteer)
        case VolunteerStatus.verified:
            _send_verified_status_email(volunteer)
        case VolunteerStatus.rejected:
            _send_rejected_status_email(volunteer)
        case VolunteerStatus.terminated:
            _send_terminated_status_email(volunteer)
        case VolunteerStatus.picture_missing:
            pass  # TODO: send email about the status

    # if status == VolunteerStatus.verified:
    #     os.remove(config.construct_nid_first_image_path(volunteer_uuid))
    #     os.remove(config.construct_nid_second_image_path(volunteer_uuid))

    return ApiResponse(
        message="Volunteer status updated successfully.",
        data=VolunteerUUID(volunteer_uuid=volunteer.uuid),
    )


# Delete a volunteer that is currently logged in
@router.delete("/delete", response_model=ApiResponse[VolunteerUUID])
def delete_logged_in_volunteer(volunteer: CurrentVolunteer, db: DatabaseSession):
    volunteer.status = VolunteerStatus.terminated
    volunteer.last_updated = get_utc_time()
    volunteer.account.status = AccountStatus.terminated
    volunteer.account.last_updated = get_utc_time()

    db.add(volunteer)
    db.add(volunteer.account)
    db.commit()
    db.refresh(volunteer)
    return ApiResponse(
        message="Volunteer account deleted.",
        data=VolunteerUUID(volunteer_uuid=volunteer.uuid),
    )


# Delete a volunteer with volunteer_uuid : Only admin can perform this action
@router.delete(
    "/{volunteer_uuid}/delete-record", response_model=ApiResponse[VolunteerUUID]
)
def delete_volunteer_by_uuid(
    volunteer_uuid: UUID, db: DatabaseSession, _: CurrentAdmin
):
    volunteer = db.get(Volunteer, volunteer_uuid)
    account = db.get(Account, volunteer_uuid)

    if not account:
        raise HTTPException(404, detail="Account not found")
    if not volunteer:
        raise HTTPException(404, detail="Volunteer not found")

    db.delete(volunteer)
    db.delete(account)
    db.commit()

    return ApiResponse(
        message="Volunteer account deleted.",
        data=VolunteerUUID(volunteer_uuid=volunteer_uuid),
    )
