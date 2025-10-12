from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4
from sqlmodel import Field, Relationship, SQLModel

from ...utils.time import get_utc_time

if TYPE_CHECKING:
    from .account import Account


class NID(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    account_uuid: UUID = Field(
        foreign_key="account.uuid", index=True, ondelete="CASCADE"
    )
    nid_hmac: bytes = Field(index=True)
    nid_cipher: bytes
    nid_nonce: bytes
    created_at: datetime = Field(default_factory=get_utc_time)

    account: "Account" = Relationship(back_populates="nid")


class BRN(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    account_uuid: UUID = Field(
        foreign_key="account.uuid", index=True, ondelete="CASCADE"
    )
    brn_hmac: bytes = Field(index=True)
    brn_cipher: bytes
    brn_nonce: bytes
    created_at: datetime = Field(default_factory=get_utc_time)

    account: "Account" = Relationship(back_populates="brn")
