from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel

from ...utils.time import get_utc_time

if TYPE_CHECKING:
    from .identifier import BRN, NID
    from .token import RefreshToken


class AccountStatus(str, Enum):
    active = "active"
    banned = "banned"
    disabled = "disabled"
    terminated = "terminated"


class AdminRole(str, Enum):
    super_admin = "super_admin"
    admin = "admin"


class Account(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    phone_number: str = Field(index=True, unique=True)
    email_address: str = Field(index=True, unique=True)
    password_hash: str
    last_login: datetime | None = Field(default=None)
    status: AccountStatus = Field(default=AccountStatus.active, index=True)
    created_at: datetime = Field(default_factory=get_utc_time)

    refresh_tokens: list["RefreshToken"] = Relationship(
        back_populates="account", cascade_delete=True
    )
    nid: "NID" = Relationship(back_populates="account", cascade_delete=True)
    brn: "BRN" = Relationship(back_populates="account", cascade_delete=True)


class User(SQLModel, table=True):
    uuid: UUID = Field(
        foreign_key="account.uuid", primary_key=True, index=True, ondelete="CASCADE"
    )
    full_name: str
    birth_date_cipher: bytes | None = Field(default=None)
    birth_date_nonce: bytes | None = Field(default=None)
    status: AccountStatus = Field(default=AccountStatus.active, index=True)
    created_at: datetime = Field(default_factory=get_utc_time)

    account: "Account" = Relationship()


class Admin(SQLModel, table=True):
    uuid: UUID = Field(
        foreign_key="account.uuid", primary_key=True, index=True, ondelete="CASCADE"
    )
    full_name: str
    role: AdminRole = Field(index=True)
    status: AccountStatus = Field(default=AccountStatus.active, index=True)
    created_at: datetime = Field(default_factory=get_utc_time)

    account: "Account" = Relationship()
