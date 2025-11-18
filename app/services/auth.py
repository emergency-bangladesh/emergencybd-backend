from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from ..core.config import config
from ..database.models.account import Account, AccountStatus, Admin, User
from ..database.models.volunteer import Volunteer, VolunteerStatus
from ..database.session import get_database_session
from .token import decode_token


def _get_jwt_access_token_from_request(request: Request):
    token = request.cookies.get(config.jwt_access_key)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login Token was not provided",
        )
    return token


def _get_jwt_admin_access_token_from_request(request: Request):
    token = request.cookies.get(config.jwt_admin_access_key)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login Token was not provided",
        )
    return token


def _get_uuid_from_token(token: str) -> UUID:
    try:
        payload = decode_token(token)
        uuid_str: str | None = payload.get("uuid")
        if not uuid_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to get UUID from token.",
            )

        return UUID(uuid_str)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


def get_logged_in_account(
    request: Request, database_session: Session = Depends(get_database_session)
):
    token = _get_jwt_access_token_from_request(request)
    uuid = _get_uuid_from_token(token)
    account = database_session.scalar(
        select(Account).where(
            Account.uuid == uuid, Account.status == AccountStatus.active
        )
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return account


def get_current_user(
    request: Request,
    database_session: Session = Depends(get_database_session),
) -> User:
    token = _get_jwt_access_token_from_request(request)
    uuid = _get_uuid_from_token(token)
    user = database_session.scalar(
        select(User).where(User.uuid == uuid, User.status == AccountStatus.active)
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


def get_current_volunteer(
    request: Request,
    database_session: Session = Depends(get_database_session),
) -> Volunteer:
    token = _get_jwt_access_token_from_request(request)
    uuid = _get_uuid_from_token(token)
    volunteer = database_session.scalar(
        select(Volunteer).where(
            Volunteer.uuid == uuid, Volunteer.status == VolunteerStatus.verified
        )
    )
    if not volunteer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You need to get verified to proceed",
        )

    return volunteer


def get_current_admin(
    request: Request,
    database_session: Session = Depends(get_database_session),
) -> Admin:
    token = _get_jwt_admin_access_token_from_request(request)
    uuid = _get_uuid_from_token(token)
    admin = database_session.scalar(
        select(Admin).where(Admin.uuid == uuid, Admin.status == AccountStatus.active)
    )
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return admin


def get_requesting_actor(
    request: Request, db: Session = Depends(get_database_session)
) -> Account | Admin:
    admin_token = request.cookies.get(config.jwt_admin_access_key)
    if admin_token:
        try:
            payload = decode_token(admin_token)
            uuid_str = payload.get("uuid")
            if uuid_str:
                uuid = UUID(uuid_str)
                admin = db.scalar(
                    select(Admin).where(
                        Admin.uuid == uuid, Admin.status == AccountStatus.active
                    )
                )
                if admin:
                    return admin
        except Exception:
            pass

    access_token = request.cookies.get(config.jwt_access_key)
    if access_token:
        try:
            payload = decode_token(access_token)
            uuid_str: str | None = payload.get("uuid")
            if uuid_str:
                uuid = UUID(uuid_str)
                account = db.scalar(
                    select(Account).where(
                        Account.uuid == uuid, Account.status == AccountStatus.active
                    )
                )
                if account:
                    return account
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
