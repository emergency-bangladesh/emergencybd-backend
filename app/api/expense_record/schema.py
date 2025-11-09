from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from ...database.models.payment import PaymentType


class ExpenseRecordBase(BaseModel):
    amount: int
    transaction_id: str
    payment_type: PaymentType = PaymentType.expense
    payment_time: datetime
    details: str
    paid_to: str
    note: str | None = None
    category: str


class ExpenseRecordCreate(ExpenseRecordBase):
    pass


class ExpenseRecordRead(ExpenseRecordBase):
    uuid: UUID
    payment_id: int


class ExpenseRecordUpdate(BaseModel):
    amount: int | None = None
    transaction_id: str | None = None
    payment_time: datetime | None = None
    details: str | None = None
    paid_to: str | None = None
    note: str | None = None
