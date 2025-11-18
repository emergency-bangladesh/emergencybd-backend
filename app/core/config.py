from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class AppConfig(BaseSettings):
    # Development mode
    dev_mode: bool = Field(False, validation_alias="DEV_MODE")

    # Database configuration
    database_uri: str = Field(..., validation_alias="DATABASE_URI")

    # app secret key
    app_key: str = Field(..., validation_alias="APP_KEY")

    # JWT configuration
    jwt_private_key: str = Field(..., validation_alias="JWT_PRIVATE_KEY")
    jwt_public_key: str = Field(..., validation_alias="JWT_PUBLIC_KEY")
    jwt_algorithm: str = Field(..., validation_alias="JWT_ALGORITHM")
    jwt_access_key: str = Field(..., validation_alias="JWT_ACCESS_KEY")
    jwt_refresh_key: str = Field(..., validation_alias="JWT_REFRESH_KEY")
    jwt_otp_key: str = Field(..., validation_alias="JWT_OTP_KEY")
    jwt_password_reset_key: str = Field(..., validation_alias="JWT_PASSWORD_RESET_KEY")
    jwt_access_token_expiration: int = Field(
        ..., validation_alias="JWT_ACCESS_TOKEN_EXPIRATION"
    )
    jwt_refresh_token_expiration: int = Field(
        ..., validation_alias="JWT_REFRESH_TOKEN_EXPIRATION"
    )
    jwt_otp_token_expiration: int = Field(
        ..., validation_alias="JWT_OTP_TOKEN_EXPIRATION"
    )
    jwt_password_reset_token_expiration: int = Field(
        ..., validation_alias="JWT_PASSWORD_RESET_TOKEN_EXPIRATION"
    )
    ## jwt admin token options
    jwt_admin_access_key: str = Field(..., validation_alias="ADMIN_JWT_ACCESS_KEY")
    jwt_admin_refresh_key: str = Field(..., validation_alias="ADMIN_JWT_REFRESH_KEY")

    # smtp configuration
    smtp_server: str = Field(..., validation_alias="SMTP_SERVER")
    smtp_port: Literal[465, 587] = Field(..., validation_alias="SMTP_PORT")
    smtp_mailfrom: str = Field(..., validation_alias="SMTP_MAILFROM")
    smtp_mailfrom_password: str = Field(..., validation_alias="SMTP_MAILFROM_PASSWORD")

    # File storage configuration
    project_root: Path = Path(__file__).resolve().parent.parent.parent
    upload_dir: Path = project_root / "uploads"
    nid_dir: Path = upload_dir / "nid_images"
    profile_pic_dir: Path = upload_dir / "profile_pics"
    lost_and_found_dir: Path = upload_dir / "lost_and_found_images"

    # password settings
    password_min_len: int = 8

    # image settings
    image_max_size_kb: int = 25
    image_initial_quality: int = 80

    # issue settings
    issue_pin_length: int = 6
    issue_update_min_volunteer_responses: int = 3

    @model_validator(mode="after")
    def _create_upload_dirs(self) -> "AppConfig":
        self.nid_dir.mkdir(parents=True, exist_ok=True)
        self.profile_pic_dir.mkdir(parents=True, exist_ok=True)
        self.lost_and_found_dir.mkdir(parents=True, exist_ok=True)
        return self

    @property
    def _cookie_settings(self) -> dict[str, Any]:
        return dict(
            httponly=True,
            samesite="none",
            secure=True,
        )

    def access_token_cookie_options(self, access_token: str) -> dict[str, Any]:
        return dict(
            key=self.jwt_access_key,
            value=access_token,
            max_age=self.jwt_access_token_expiration,
            expires=(
                datetime.now(timezone.utc)
                + timedelta(seconds=self.jwt_access_token_expiration)
            ),
            **self._cookie_settings,
        )

    def admin_access_token_cookie_options(self, access_token: str) -> dict[str, Any]:
        return dict(
            key=self.jwt_admin_access_key,
            value=access_token,
            max_age=self.jwt_access_token_expiration,
            expires=(
                datetime.now(timezone.utc)
                + timedelta(seconds=self.jwt_access_token_expiration)
            ),
            **self._cookie_settings,
        )

    def refresh_token_cookie_options(self, refresh_token: str) -> dict[str, Any]:
        return dict(
            key=self.jwt_refresh_key,
            value=refresh_token,
            max_age=self.jwt_refresh_token_expiration,
            expires=(
                datetime.now(timezone.utc)
                + timedelta(seconds=self.jwt_refresh_token_expiration)
            ),
            **self._cookie_settings,
        )

    def admin_refresh_token_cookie_options(self, refresh_token: str) -> dict[str, Any]:
        return dict(
            key=self.jwt_admin_refresh_key,
            value=refresh_token,
            max_age=self.jwt_access_token_expiration * 2,
            expires=(
                datetime.now(timezone.utc)
                + timedelta(seconds=self.jwt_access_token_expiration * 2)
            ),
            **self._cookie_settings,
        )

    def otp_token_cookie_options(self, otp_token: str) -> dict[str, Any]:
        return dict(
            key=self.jwt_otp_key,
            value=otp_token,
            max_age=self.jwt_otp_token_expiration,
            expires=(
                datetime.now(timezone.utc)
                + timedelta(seconds=self.jwt_otp_token_expiration)
            ),
            **self._cookie_settings,
        )

    def password_reset_token_cookie_options(
        self, password_reset_token: str
    ) -> dict[str, Any]:
        return dict(
            key=self.jwt_password_reset_key,
            value=password_reset_token,
            max_age=self.jwt_password_reset_token_expiration,
            expires=(
                datetime.now(timezone.utc)
                + timedelta(seconds=self.jwt_password_reset_token_expiration)
            ),
            **self._cookie_settings,
        )

    def construct_nid_first_image_path(self, volunteer_uuid: UUID) -> Path:
        return self.nid_dir / f"{volunteer_uuid}_nid_first.webp"

    def construct_nid_second_image_path(self, volunteer_uuid: UUID) -> Path:
        return self.nid_dir / f"{volunteer_uuid}_nid_second.webp"

    def construct_profile_pic_path(self, volunteer_uuid: UUID) -> Path:
        return self.profile_pic_dir / f"{volunteer_uuid}.webp"

    def construct_lost_and_found_image_path(
        self, issue_uuid: UUID, image_number: int
    ) -> Path:
        return self.lost_and_found_dir / f"{issue_uuid}_image_{image_number}.webp"

    @field_validator(
        "jwt_access_token_expiration",
        "jwt_refresh_token_expiration",
        "jwt_otp_token_expiration",
        "jwt_password_reset_token_expiration",
        mode="before",
    )
    @classmethod
    def parse_expiration(cls, v: Any) -> int:
        return int(v)

    @field_validator("smtp_port", mode="before")
    @classmethod
    def parse_smtp_port(cls, v: Any) -> int:
        if int(v) not in [465, 587]:
            raise ValueError("SMTP port must be 465, or 587")
        return int(v)

    model_config = {
        "env_file": Path(__file__).resolve().parent.parent.parent / ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


config = AppConfig()  # type:ignore
