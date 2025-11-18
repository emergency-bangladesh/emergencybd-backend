from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlmodel import Column, Field, Relationship, SQLModel

from ...types.datetime_utc import SADateTimeUTC
from ...utils.time import get_utc_time

if TYPE_CHECKING:
    from .account import Account


class RefreshToken(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    account_uuid: UUID = Field(
        foreign_key="account.uuid", index=True, ondelete="CASCADE"
    )
    refresh_token_jti: str
    created_at: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )
    expires_at: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )
    revoked: bool = Field(default=False)

    account: "Account" = Relationship(back_populates="refresh_tokens")
