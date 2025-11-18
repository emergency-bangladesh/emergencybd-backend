from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from snowflake import SnowflakeGenerator  # type:ignore
from sqlmodel import BigInteger, Column, Field, Relationship, SQLModel

from ...types.datetime_utc import SADateTimeUTC
from ...utils.time import get_utc_time

gen = SnowflakeGenerator(1)


class PaymentType(str, Enum):
    incoming = "incoming"
    expense = "expense"


class PaymentRecord(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    payment_id: int = Field(
        sa_column=Column(BigInteger, index=True, unique=True),
        default_factory=lambda: next(gen),
    )
    amount: int
    transaction_id: str
    payment_type: PaymentType = Field(index=True)
    payment_time: datetime = Field(
        default_factory=get_utc_time,
        sa_column=Column(SADateTimeUTC, index=True),
    )

    created_at: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )
    last_updated: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )


class IncomingRecordSource(str, Enum):
    grant = "grant"
    prize = "prize"
    donation = "donation"
    sponsorship = "sponsorship"


class IncomingRecord(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    payment_id: int = Field(
        foreign_key="paymentrecord.payment_id", index=True, ondelete="CASCADE"
    )
    details: str
    source: IncomingRecordSource = Field(index=True)
    paid_by: str
    note: str | None = Field(None)

    created_at: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )
    last_updated: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )

    payment_record: PaymentRecord = Relationship()


class ExpenseRecord(SQLModel, table=True):
    uuid: UUID = Field(default_factory=uuid4, primary_key=True, index=True)
    payment_id: int = Field(
        foreign_key="paymentrecord.payment_id", index=True, ondelete="CASCADE"
    )
    category: str = Field(index=True)
    details: str
    paid_to: str
    note: str | None = Field(None)

    created_at: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )
    last_updated: datetime = Field(
        default_factory=get_utc_time, sa_column=Column(SADateTimeUTC)
    )
    payment_record: PaymentRecord = Relationship()
