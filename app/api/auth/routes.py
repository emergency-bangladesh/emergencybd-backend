from datetime import timedelta, timezone
from uuid import UUID, uuid4

import jwt
import pyotp
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlmodel import select

from ...core.config import config
from ...core.security import hash_password, verify_password
from ...database.models.account import Account, AccountStatus, Admin, User
from ...database.models.token import RefreshToken
from ...database.models.volunteer import Volunteer
from ...services.email import send_email
from ...services.token import decode_token, encode_token
from ...utils.time import get_utc_time
from ..dependencies import CurrentAdmin, DatabaseSession, LoggedInAccount
from ..global_schema import ApiResponse
from .schema import (
    AdminLoginInformation,
    LoginCredentials,
    LoginInformation,
    OTPSendRequest,
    OTPSentResponseData,
    OTPVerifiedResponseData,
    OTPVerifyRequest,
    PasswordResetRequest,
    PasswordResetResponseData,
    PasswordUpdate,
)

router = APIRouter(prefix="/auth", tags=["Authentication Routes"])


@router.get(
    "/me",
    summary="Get current user's information",
    response_model=ApiResponse[LoginInformation],
)
def get_user_information(
    account: LoggedInAccount, db: DatabaseSession
) -> ApiResponse[LoginInformation]:
    volunteer = db.get(Volunteer, account.uuid)
    user = db.get(User, account.uuid)

    if volunteer:
        return ApiResponse(
            message="User information retrieved successfully",
            data=LoginInformation(
                name=volunteer.full_name,
                phone_number=account.phone_number,
                email=account.email_address,
                account_type="volunteer",
                uuid=account.uuid,
            ),
        )
    elif user:
        return ApiResponse(
            message="User information retrieved successfully",
            data=LoginInformation(
                name=user.full_name,
                phone_number=account.phone_number,
                email=account.email_address,
                account_type="general_user",
                uuid=account.uuid,
            ),
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found",
        )


@router.get(
    "/admin/me",
    summary="Get current admin's information",
    response_model=ApiResponse[AdminLoginInformation],
)
def get_admin_information(admin: CurrentAdmin) -> ApiResponse[AdminLoginInformation]:
    return ApiResponse(
        message="Admin information retrieved successfully",
        data=AdminLoginInformation(
            name=admin.full_name,
            email=admin.account.email_address,
            phone_number=admin.account.phone_number,
            uuid=admin.uuid,
            role=admin.role,
        ),
    )


@router.post(
    "/login",
    summary="Authenticate a user and issue an access token",
    response_model=ApiResponse,
)
def login(cred: LoginCredentials, db: DatabaseSession):
    account = db.scalar(
        select(Account).where(
            Account.email_address == cred.email
            and Account.status == AccountStatus.active
        )
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    if not verify_password(cred.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials"
        )
    access_token = encode_token({"uuid": str(account.uuid), "type": "access"})
    jti = str(uuid4())
    refresh_token = encode_token(
        {"uuid": str(account.uuid), "jti": jti, "type": "refresh"},
        expiry_timedelta=timedelta(seconds=config.jwt_refresh_token_expiration),
    )

    db_refresh_token = RefreshToken(
        account_uuid=account.uuid,
        refresh_token_jti=jti,
        created_at=get_utc_time(),
        expires_at=(
            get_utc_time() + timedelta(seconds=config.jwt_refresh_token_expiration)
        ),
    )
    db.add(db_refresh_token)

    account.last_login = get_utc_time()
    db.add(account)
    db.commit()
    db.refresh(account)

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ApiResponse(message="Login successful").model_dump(),
    )

    response.set_cookie(**config.access_token_cookie_options(access_token))
    response.set_cookie(**config.refresh_token_cookie_options(refresh_token))

    return response


@router.post(
    "/admin/login",
    summary="Authenticate an admin and issue an access token",
    response_model=ApiResponse,
)
def admin_login(cred: LoginCredentials, db: DatabaseSession):
    account = db.scalar(
        select(Account).where(
            Account.email_address == cred.email
            and Account.status == AccountStatus.active
        )
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    if not verify_password(cred.password, account.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials"
        )
    admin = db.get(Admin, account.uuid)
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid credentials"
        )
    access_token = encode_token({"uuid": str(account.uuid), "type": "access"})
    jti = str(uuid4())
    refresh_token = encode_token(
        {"uuid": str(account.uuid), "jti": jti, "type": "refresh"},
        expiry_timedelta=timedelta(seconds=config.jwt_refresh_token_expiration),
    )

    db_refresh_token = RefreshToken(
        account_uuid=account.uuid,
        refresh_token_jti=jti,
        created_at=get_utc_time(),
        expires_at=(
            get_utc_time() + timedelta(seconds=config.jwt_refresh_token_expiration)
        ),
    )
    db.add(db_refresh_token)

    account.last_login = get_utc_time()
    admin.account.last_login = get_utc_time()
    db.add(account)
    db.add(admin)
    db.commit()

    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ApiResponse(message="Login successful").model_dump(),
    )

    response.set_cookie(**config.access_token_cookie_options(access_token))
    response.set_cookie(**config.admin_refresh_token_cookie_options(refresh_token))

    return response


@router.post("/logout", summary="Log out the current user", response_model=ApiResponse)
def logout() -> JSONResponse:
    response = JSONResponse(
        status_code=status.HTTP_200_OK,
        content=ApiResponse(message="Logged out successfully").model_dump(),
    )
    response.delete_cookie(config.jwt_access_key)
    response.delete_cookie(config.jwt_refresh_key)
    return response


@router.post(
    "/refresh-token",
    summary="Refresh a user's access token",
    response_model=ApiResponse,
)
def refresh_user_access_token(request: Request, db: DatabaseSession) -> JSONResponse:
    refresh_token = request.cookies.get(config.jwt_refresh_key)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided"
        )

    try:
        # Decode refresh token
        payload = decode_token(refresh_token, verify_exp=True)
        # print(f'{payload=}')
        uuid_str: str | None = payload.get("uuid")
        jti: str | None = payload.get("jti")
        token_type: str | None = payload.get("type")

        if not uuid_str or not jti or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token payload",
            )

        # Validate user exists
        account = db.get(Account, UUID(uuid_str))
        if not account:
            raise HTTPException(
                # just bored to send robotic messages!
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Are you sure?",
            )

        # Validate refresh token in DB
        db_refresh_token = db.scalar(
            select(RefreshToken).where(
                RefreshToken.account_uuid == account.uuid,
                RefreshToken.refresh_token_jti == jti,
            )
        )
        if not db_refresh_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Refresh token not found",
            )

        if db_refresh_token.revoked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Refresh token revoked",
            )

        # Check expiry
        now = get_utc_time()
        if db_refresh_token.expires_at.tzinfo is None:
            expires_at = db_refresh_token.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at = db_refresh_token.expires_at
        if expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Refresh token expired"
            )

        #  Revoke old token
        db_refresh_token.revoked = True
        db.add(db_refresh_token)

        #  Issue new access + refresh tokens
        new_access_token = encode_token({"uuid": uuid_str, "type": "access"})

        new_jti = str(uuid4())
        new_refresh_token = encode_token(
            {"uuid": uuid_str, "jti": new_jti, "type": "refresh"},
            expiry_timedelta=timedelta(seconds=config.jwt_refresh_token_expiration),
        )

        new_db_token = RefreshToken(
            account_uuid=account.uuid,
            refresh_token_jti=new_jti,
            created_at=now,
            expires_at=now + timedelta(seconds=config.jwt_refresh_token_expiration),
            revoked=False,
        )
        db.add(new_db_token)
        db.commit()

        #  Prepare response
        response = JSONResponse(
            status_code=status.HTTP_200_OK,
            content=ApiResponse(message="Token refreshed successfully").model_dump(),
        )

        response.set_cookie(**config.access_token_cookie_options(new_access_token))
        response.set_cookie(**config.refresh_token_cookie_options(new_refresh_token))

        return response

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.post(
    "/verify-access-token",
    summary="Verify the validity of an access token",
    response_model=ApiResponse,
)
def verify_access_token(request: Request, db: DatabaseSession) -> ApiResponse[None]:
    access_token = request.cookies.get(config.jwt_access_key)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )

    try:
        # Decode and verify access token
        payload = decode_token(access_token)
        uuid_str: str | None = payload.get("uuid")
        token_type: str | None = payload.get("type")

        if not uuid_str or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
            )

        return ApiResponse(message="Token is valid")

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )


@router.patch(
    "/update-password",
    summary="Update the password for the current user",
    response_model=ApiResponse,
)
def update_user_password(
    cred: PasswordUpdate, account: LoggedInAccount, db: DatabaseSession
) -> ApiResponse[None]:
    if not verify_password(cred.current_password, account.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, detail="Invalid current password"
        )
    account.password_hash = hash_password(cred.new_password)
    db.add(account)
    db.commit()
    return ApiResponse(message="Password updated successfully")


@router.post(
    "/password-reset/send-otp",
    summary="Generate and send OTP for password reset",
    response_model=ApiResponse[OTPSentResponseData],
)
async def send_otp_for_password_reset(
    payload: OTPSendRequest,
    db: DatabaseSession,
    background_tasks: BackgroundTasks,
) -> JSONResponse:
    account = db.scalar(select(Account).where(Account.email_address == payload.email))
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )

    # Generate OTP secret
    otp_secret = pyotp.random_base32()
    totp = pyotp.TOTP(otp_secret)
    otp_code = totp.now()

    # Encode otp_secret and account_uuid into a JWT
    otp_token_payload = {
        "sub": str(account.uuid),
        "otp_secret": otp_secret,
        "type": "otp_reset",
    }
    otp_jwt = encode_token(
        otp_token_payload,
        expiry_timedelta=timedelta(seconds=config.jwt_otp_token_expiration),
    )

    # Send OTP via email in background
    email_body = (
        f"Your OTP for password reset is: {otp_code}. It is valid for 5 minutes."
    )
    background_tasks.add_task(
        send_email,
        mailto=payload.email,
        subject="Password Reset OTP",
        body=email_body,
        content_type="plain",
    )

    response_content = ApiResponse(
        message="OTP sent to email", data=OTPSentResponseData(otp_sent=True)
    ).model_dump()
    json_response = JSONResponse(
        content=response_content, status_code=status.HTTP_200_OK
    )
    json_response.set_cookie(**config.otp_token_cookie_options(otp_jwt))
    return json_response


@router.post(
    "/password-reset/verify-otp",
    summary="Verify OTP and issue password reset token",
    response_model=ApiResponse[OTPVerifiedResponseData],
)
async def verify_otp_for_password_reset(
    payload: OTPVerifyRequest,
    request: Request,
    response: Response,
) -> JSONResponse:
    otp_jwt = request.cookies.get(config.jwt_otp_key)
    if not otp_jwt:
        response_content = ApiResponse(
            message="OTP token missing or expired",
            data=OTPVerifiedResponseData(otp_verified=False),
        ).model_dump()
        json_response = JSONResponse(
            content=response_content, status_code=status.HTTP_400_BAD_REQUEST
        )
        json_response.delete_cookie(config.jwt_otp_key)
        return json_response

    # Clear OTP cookie regardless of verification success
    response.delete_cookie(config.jwt_otp_key)

    try:
        otp_token_payload = decode_token(otp_jwt, verify_exp=True)
        account_uuid_str = otp_token_payload.get("sub")
        otp_secret = otp_token_payload.get("otp_secret")
        token_type = otp_token_payload.get("type")

        if not (account_uuid_str and otp_secret and token_type == "otp_reset"):
            response_content = ApiResponse(
                message="Invalid OTP token",
                data=OTPVerifiedResponseData(otp_verified=False),
            ).model_dump()
            return JSONResponse(
                content=response_content, status_code=status.HTTP_401_UNAUTHORIZED
            )

        totp = pyotp.TOTP(otp_secret)
        if not totp.verify(str(payload.otp)):
            response_content = ApiResponse(
                message="Invalid OTP", data=OTPVerifiedResponseData(otp_verified=False)
            ).model_dump()
            return JSONResponse(
                content=response_content, status_code=status.HTTP_401_UNAUTHORIZED
            )

        # OTP verified, issue password reset token
        password_reset_jwt = encode_token(
            data={
                "sub": account_uuid_str,
                "type": "password_reset",
            },
            expiry_timedelta=timedelta(
                seconds=config.jwt_password_reset_token_expiration
            ),
        )

        response_content = ApiResponse(
            message="OTP verified successfully",
            data=OTPVerifiedResponseData(otp_verified=True),
        ).model_dump()
        json_response = JSONResponse(
            content=response_content, status_code=status.HTTP_200_OK
        )
        json_response.set_cookie(
            **config.password_reset_token_cookie_options(password_reset_jwt)
        )
        return json_response

    except Exception:
        response_content = ApiResponse(
            message="Invalid or expired OTP token",
            data=OTPVerifiedResponseData(otp_verified=False),
        ).model_dump()
        return JSONResponse(
            content=response_content, status_code=status.HTTP_401_UNAUTHORIZED
        )


@router.post(
    "/password-reset",
    summary="Reset user password",
    response_model=ApiResponse[PasswordResetResponseData],
)
async def reset_password(
    payload: PasswordResetRequest,
    request: Request,
    response: Response,
    db: DatabaseSession,
) -> JSONResponse:
    password_reset_jwt = request.cookies.get(config.jwt_password_reset_key)
    if not password_reset_jwt:
        response_content = ApiResponse(
            message="Password reset token missing or expired",
            data=PasswordResetResponseData(message="Password reset failed."),
        ).model_dump()
        json_response = JSONResponse(
            content=response_content, status_code=status.HTTP_400_BAD_REQUEST
        )
        json_response.delete_cookie(config.jwt_password_reset_key)
        return json_response

    # Clear password reset cookie regardless of success
    response.delete_cookie(config.jwt_password_reset_key)

    try:
        password_reset_token_payload = decode_token(password_reset_jwt, verify_exp=True)
        account_uuid_str = password_reset_token_payload.get("sub")
        token_type = password_reset_token_payload.get("type")

        if not (account_uuid_str and token_type == "password_reset"):
            response_content = ApiResponse(
                message="Invalid password reset token",
                data=PasswordResetResponseData(message="Password reset failed."),
            ).model_dump()
            return JSONResponse(
                content=response_content, status_code=status.HTTP_401_UNAUTHORIZED
            )

        account_uuid = UUID(account_uuid_str)
        account = db.scalar(select(Account).where(Account.uuid == account_uuid))

        if not account:
            response_content = ApiResponse(
                message="Account not found",
                data=PasswordResetResponseData(message="Password reset failed."),
            ).model_dump()
            return JSONResponse(
                content=response_content, status_code=status.HTTP_404_NOT_FOUND
            )

        account.password_hash = hash_password(payload.new_password)
        db.add(account)
        db.commit()

        response_content = ApiResponse(
            message="Password Reset",
            data=PasswordResetResponseData(
                message="Password has been successfully reset."
            ),
        ).model_dump()
        json_response = JSONResponse(
            content=response_content, status_code=status.HTTP_200_OK
        )
        return json_response

    except Exception as e:
        response_content = ApiResponse(
            message=f"Invalid or expired password reset token: {e}",
            data=PasswordResetResponseData(message="Password reset failed."),
        ).model_dump()
        return JSONResponse(
            content=response_content, status_code=status.HTTP_401_UNAUTHORIZED
        )
