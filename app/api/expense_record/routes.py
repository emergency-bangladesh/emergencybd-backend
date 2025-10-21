from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.dependencies import CurrentAdmin, DatabaseSession
from app.api.expense_record.schema import (
    ExpenseRecordCreate,
    ExpenseRecordRead,
    ExpenseRecordUpdate,
)
from app.api.global_schema import ApiResponse
from app.database.models.payment import ExpenseRecord, PaymentRecord, PaymentType

router = APIRouter(
    prefix="/expense-record", tags=["Expense Record Routes (Admin Only)"]
)


@router.post("/new", response_model=ApiResponse[ExpenseRecordRead])
def create_expense_record(
    _: CurrentAdmin, record: ExpenseRecordCreate, db: DatabaseSession
):
    payment_record = PaymentRecord(
        amount=record.amount,
        transaction_id=record.transaction_id,
        payment_type=PaymentType.expense,
        payment_time=record.payment_time,
    )
    db.add(payment_record)
    db.flush()

    expense_record = ExpenseRecord(
        payment_id=payment_record.payment_id,
        details=record.details,
        paid_to=record.paid_to,
        note=record.note,
    )
    db.add(expense_record)
    db.commit()
    db.refresh(expense_record)
    return ApiResponse(
        message="Expense record created successfully", data=expense_record
    )


@router.get("/", response_model=ApiResponse[List[ExpenseRecordRead]])
def get_all_expense_records(_: CurrentAdmin, db: DatabaseSession):
    records = db.exec(select(ExpenseRecord)).all()
    return ApiResponse(message="Expense records retrieved successfully", data=records)


@router.get("/{record_id}", response_model=ApiResponse[ExpenseRecordRead])
def get_expense_record(_: CurrentAdmin, record_id: UUID, db: DatabaseSession):
    record = db.get(ExpenseRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Expense record not found")
    return ApiResponse(message="Expense record retrieved successfully", data=record)


@router.put("/update/{record_id}", response_model=ApiResponse[ExpenseRecordRead])
def update_expense_record(
    _: CurrentAdmin,
    record_id: UUID,
    record_data: ExpenseRecordUpdate,
    db: DatabaseSession,
):
    record = db.get(ExpenseRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Expense record not found")

    payment_record = db.exec(
        select(PaymentRecord).where(PaymentRecord.payment_id == record.payment_id)
    ).first()
    if not payment_record:
        raise HTTPException(status_code=404, detail="Payment record not found")

    update_data = record_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(record, key):
            setattr(record, key, value)
        if hasattr(payment_record, key):
            setattr(payment_record, key, value)

    db.add(record)
    db.add(payment_record)
    db.commit()
    db.refresh(record)
    return ApiResponse(message="Expense record updated successfully", data=record)


@router.delete("/delete/{record_id}", status_code=204)
def delete_expense_record(
    _: CurrentAdmin, record_id: UUID, db: DatabaseSession
) -> ApiResponse[None]:
    record = db.get(ExpenseRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Expense record not found")

    payment_record = db.exec(
        select(PaymentRecord).where(PaymentRecord.payment_id == record.payment_id)
    ).first()
    if payment_record:
        db.delete(payment_record)

    db.delete(record)
    db.commit()
    return ApiResponse(message="Expense record deleted successfully")
