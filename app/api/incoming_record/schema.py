from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ...database.models.payment import IncomingRecordSource, PaymentType


class IncomingRecordBase(BaseModel):
    amount: int
    transaction_id: str
    payment_type: PaymentType = PaymentType.incoming
    payment_time: datetime
    details: str
    source: IncomingRecordSource
    paid_by: str
    note: str | None = None


class IncomingRecordCreate(IncomingRecordBase):
    pass


class IncomingRecordRead(IncomingRecordBase):
    uuid: UUID
    payment_id: int


class IncomingRecordUpdate(BaseModel):
    amount: int | None = None
    transaction_id: str | None = None
    payment_time: datetime | None = None
    details: str | None = None
    source: IncomingRecordSource | None = None
    paid_by: str | None = None
    note: str | None = None
