from typing import Sequence
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
) -> ApiResponse[ExpenseRecordRead]:
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
        category=record.category,
    )
    db.add(expense_record)
    db.commit()
    db.refresh(expense_record)
    return ApiResponse(
        message="Expense record created successfully",
        data=ExpenseRecordRead(
            amount=expense_record.payment_record.amount,
            payment_id=expense_record.payment_id,
            transaction_id=expense_record.payment_record.transaction_id,
            payment_type=PaymentType.expense,
            payment_time=expense_record.payment_record.payment_time,
            details=expense_record.details,
            note=expense_record.note,
            paid_to=expense_record.paid_to,
            uuid=expense_record.uuid,
            category=expense_record.category,
        ),
    )


@router.get("/", response_model=ApiResponse[Sequence[ExpenseRecordRead]])
def get_all_expense_records(
    _: CurrentAdmin, db: DatabaseSession
) -> ApiResponse[Sequence[ExpenseRecordRead]]:
    expense_records = db.exec(select(ExpenseRecord)).all()[::-1]
    return ApiResponse(
        message="Expense records retrieved successfully",
        data=[
            ExpenseRecordRead(
                amount=expense_record.payment_record.amount,
                payment_id=expense_record.payment_id,
                transaction_id=expense_record.payment_record.transaction_id,
                payment_type=PaymentType.expense,
                payment_time=expense_record.payment_record.payment_time,
                details=expense_record.details,
                note=expense_record.note,
                paid_to=expense_record.paid_to,
                uuid=expense_record.uuid,
                category=expense_record.category,
            )
            for expense_record in expense_records
        ],
    )


@router.get("/{record_uuid}", response_model=ApiResponse[ExpenseRecordRead])
def get_expense_record(_: CurrentAdmin, record_uuid: UUID, db: DatabaseSession):
    expense_record = db.get(ExpenseRecord, record_uuid)
    if not expense_record:
        raise HTTPException(status_code=404, detail="Expense record not found")
    return ApiResponse(
        message="Expense record retrieved successfully",
        data=ExpenseRecordRead(
            amount=expense_record.payment_record.amount,
            payment_id=expense_record.payment_id,
            transaction_id=expense_record.payment_record.transaction_id,
            payment_type=PaymentType.expense,
            payment_time=expense_record.payment_record.payment_time,
            details=expense_record.details,
            note=expense_record.note,
            paid_to=expense_record.paid_to,
            uuid=expense_record.uuid,
            category=expense_record.category,
        ),
    )


@router.put("/update/{record_uuid}", response_model=ApiResponse[ExpenseRecordRead])
def update_expense_record(
    _: CurrentAdmin,
    record_uuid: UUID,
    record_data: ExpenseRecordUpdate,
    db: DatabaseSession,
):
    expense_record = db.get(ExpenseRecord, record_uuid)
    if not expense_record:
        raise HTTPException(status_code=404, detail="Expense record not found")

    payment_record = expense_record.payment_record
    update_data = record_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(expense_record, key):
            setattr(expense_record, key, value)
        if hasattr(payment_record, key):
            setattr(payment_record, key, value)

    db.add(expense_record)
    db.add(payment_record)
    db.commit()
    db.refresh(expense_record)
    return ApiResponse(
        message="Expense record updated successfully",
        data=ExpenseRecordRead(
            amount=expense_record.payment_record.amount,
            payment_id=expense_record.payment_id,
            transaction_id=expense_record.payment_record.transaction_id,
            payment_type=PaymentType.expense,
            payment_time=expense_record.payment_record.payment_time,
            details=expense_record.details,
            note=expense_record.note,
            paid_to=expense_record.paid_to,
            uuid=expense_record.uuid,
            category=expense_record.category,
        ),
    )


@router.delete("/delete/{record_uuid}", response_model=ApiResponse[None])
def delete_expense_record_by_uuid(
    _: CurrentAdmin, record_uuid: UUID, db: DatabaseSession
) -> ApiResponse[None]:
    record = db.get(ExpenseRecord, record_uuid)
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
