from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from sqlmodel import select

from ...core.config import config
from ...core.security import hash_password
from ...database.models.account import Account, AccountStatus
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
    VolunteerListResponse,
    VolunteerUpdate,
    VolunteerUpdateDeleteData,
)

router = APIRouter(prefix="/volunteers", tags=["volunteers"])


# Get all volunteers
@router.get("/", response_model=ApiResponse[list[VolunteerListResponse]])
def get_volunteers(
    db: DatabaseSession,
    _: CurrentAdmin,
    skip: int = 0,
    limit: int = 100,
):
    stmt = select(Volunteer).offset(skip).limit(limit)
    volunteers = db.exec(stmt).all()
    return ApiResponse(
        message="Volunteers retrieved successfully",
        data=[
            VolunteerListResponse(
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
            )
            for v in volunteers
        ],
    )


# Create a volunteer
@router.post(
    "/new",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[VolunteerCreateData],
)
def create_volunteer(
    payload: VolunteerCreate, db: DatabaseSession, background_tasks: BackgroundTasks
):
    # Check if an account with the given phone number or email already exists
    existing_account = db.scalar(
        select(Account).where(
            (Account.phone_number == payload.phone_number)
            | (Account.email_address == payload.email_address)
        )
    )

    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this phone number or email already exists.",
        )

    # Create a new account
    account = Account(
        phone_number=payload.phone_number,
        email_address=payload.email_address,
        password_hash=hash_password(payload.password),
    )
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

    background_tasks.add_task(
        send_email,
        mailto=payload.email_address,
        subject="Your Volunteer Registration is Received",
        body=f"""Hello {payload.full_name},

Thank you for registering as a volunteer. We have successfully received your information.

Account Status: Pending
An admin will review and validate your details shortly.

Once the verification is complete, you will receive a confirmation email, and your account will be marked as Verified.

We truly appreciate your patience and your willingness to support our mission.

Best regards,
Team Emergency Bangladesh
{config.smtp_mailfrom}
""",
        content_type="plain",
    )

    return ApiResponse(
        message="Volunteer registration submitted. Awaiting manual validation.",
        data=VolunteerCreateData(volunteer_uuid=volunteer.uuid, status=volunteer.status.value),
    )


# Get a single volunteer by ID
@router.get("/{volunteer_uuid}", response_model=ApiResponse[VolunteerDetailResponse])
def get_volunteer_by_uuid(volunteer_uuid: UUID, db: DatabaseSession):
    volunteer = db.scalar(select(Volunteer).where(Volunteer.uuid == volunteer_uuid))
    now = get_utc_time()
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No volunteer verified or pending verification found",
        )
    if volunteer.status in [VolunteerStatus.rejected, VolunteerStatus.terminated]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The volunteer account is either terminated or rejected",
        )

    active_team_memberships = [
        t for t in volunteer.team_memberships if t.team.expiration_date >= now.date()
    ]

    return ApiResponse(
        message="Volunteer details retrieved successfully",
        data=VolunteerDetailResponse(
            volunteer_uuid=volunteer.uuid,
            full_name=volunteer.full_name,
            phone_number=volunteer.account.phone_number,
            email_address=volunteer.account.email_address,
            permanent_upazila=volunteer.permanent_upazila,
            permanent_district=volunteer.permanent_district,
            current_upazila=volunteer.current_upazila,
            current_district=volunteer.current_district,
            blood_group=volunteer.blood_group,
            identifier_type=volunteer.identifier_type.value,
            status=volunteer.status.value,
            created_at=volunteer.created_at,
            last_updated=volunteer.last_updated,
            issue_responses=len(volunteer.issue_responses),
            current_team_information=TeamInformation(
                team_name=active_team_memberships[0].team.name,
                role=active_team_memberships[0].role,
                team_uuid=active_team_memberships[0].team.uuid,
            )
            if active_team_memberships
            else None,
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

    return ApiResponse(message="Volunteer details retrieved successfully", data=recent_activities)


# Update a logged in volunteer
@router.patch("/update", response_model=ApiResponse[VolunteerUpdateDeleteData])
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
        data=VolunteerUpdateDeleteData(volunteer_uuid=volunteer.uuid),
    )


# Update a volunteer with volunteer_uuid
@router.patch("/{volunteer_uuid}/update", response_model=ApiResponse[VolunteerUpdateDeleteData])
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
        data=VolunteerUpdateDeleteData(volunteer_uuid=volunteer.uuid),
    )


# Delete a volunteer that is currently logged in
@router.delete("/delete", response_model=ApiResponse[VolunteerUpdateDeleteData])
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
        data=VolunteerUpdateDeleteData(volunteer_uuid=volunteer.uuid),
    )


# Delete a volunteer with volunteer_uuid
@router.delete("/{volunteer_uuid}/delete", response_model=ApiResponse[VolunteerUpdateDeleteData])
def delete_volunteer_by_uuid(volunteer_uuid: UUID, db: DatabaseSession, _: CurrentAdmin):
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
        data=VolunteerUpdateDeleteData(volunteer_uuid=volunteer_uuid),
    )
