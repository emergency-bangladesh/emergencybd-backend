from fastapi import APIRouter
from pydantic import EmailStr
from sqlmodel import select

from ...database.models.account import Account
from ...database.models.team import Team
from ...database.models.volunteer import Volunteer
from ...utils.time import get_utc_time
from ..dependencies import DatabaseSession
from ..global_schema import ApiResponse
from .schema import ValidationResponse

router = APIRouter(prefix="/validate", tags=["Validation Routes"])


@router.get(
    "/account/phone-number/{phone_number}",
    summary="Validate if an account exists by phone number",
    response_model=ApiResponse[ValidationResponse],
)
async def validate_account_by_phone_number(
    phone_number: str,
    db: DatabaseSession,
):
    account = db.scalar(select(Account).where(Account.phone_number == phone_number))
    return ApiResponse(
        message="Account validation by phone number successful",
        data=ValidationResponse(valid=bool(account)),
    )


@router.get(
    "/account/email/{email}",
    summary="Validate if an account exists by email address",
    response_model=ApiResponse[ValidationResponse],
)
async def validate_account_by_email(
    email: EmailStr,
    db: DatabaseSession,
):
    account = db.scalar(select(Account).where(Account.email_address == email))
    return ApiResponse(
        message="Account validation by email successful",
        data=ValidationResponse(valid=bool(account)),
    )


@router.get(
    "/volunteer/phone-number/{phone_number}",
    summary="Validate if a volunteer exists by phone number",
    response_model=ApiResponse[ValidationResponse],
)
async def validate_volunteer_by_phone_number(
    phone_number: str,
    db: DatabaseSession,
):
    account = db.scalar(select(Account).where(Account.phone_number == phone_number))
    if not account:
        return ApiResponse(
            message="Volunteer validation by phone number failed",
            data=ValidationResponse(valid=False),
        )
    volunteer = db.scalar(select(Volunteer).where(Volunteer.uuid == account.uuid))
    return ApiResponse(
        message="Volunteer validation by phone number successful",
        data=ValidationResponse(valid=bool(volunteer)),
    )


@router.get(
    "/volunteer/email/{email_address}",
    summary="Validate if a volunteer exists by phone number",
    response_model=ApiResponse[ValidationResponse],
)
async def validate_volunteer_by_email_address(
    email_address: EmailStr,
    db: DatabaseSession,
):
    account = db.scalar(select(Account).where(Account.email_address == email_address))
    if not account:
        return ApiResponse(
            message="Volunteer validation by phone number failed",
            data=ValidationResponse(valid=False),
        )
    volunteer = db.scalar(select(Volunteer).where(Volunteer.uuid == account.uuid))
    return ApiResponse(
        message="Volunteer validation by phone number successful",
        data=ValidationResponse(valid=bool(volunteer)),
    )


@router.get(
    "/team/name/{team_name}",
    summary="Validate if a team exists by name",
    response_model=ApiResponse[ValidationResponse],
)
async def validate_team_name(team_name: str, db: DatabaseSession):
    team = db.scalar(
        select(Team).where(
            Team.name == team_name, Team.expiration_date >= get_utc_time()
        )
    )
    return ApiResponse(
        message="Team validation by name successful",
        data=ValidationResponse(valid=bool(team)),
    )
