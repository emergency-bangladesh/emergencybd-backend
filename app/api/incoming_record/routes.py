from typing import Sequence
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlmodel import select

from app.api.dependencies import CurrentAdmin, DatabaseSession
from app.api.global_schema import ApiResponse
from app.api.incoming_record.schema import (
    IncomingRecordCreate,
    IncomingRecordRead,
    IncomingRecordUpdate,
)

from ...database.models.payment import IncomingRecord, PaymentRecord, PaymentType

router = APIRouter(
    prefix="/incoming-record", tags=["Incoming Record Routes (Admin Only)"]
)


@router.post("/new", response_model=ApiResponse[IncomingRecordRead])
def create_incoming_record(
    _: CurrentAdmin, record: IncomingRecordCreate, db: DatabaseSession
):
    payment_record = PaymentRecord(
        amount=record.amount,
        transaction_id=record.transaction_id,
        payment_type=PaymentType.incoming,
        payment_time=record.payment_time,
    )
    db.add(payment_record)
    db.flush()

    incoming_record = IncomingRecord(
        payment_id=payment_record.payment_id,
        details=record.details,
        source=record.source,
        paid_by=record.paid_by,
        note=record.note,
    )
    db.add(incoming_record)
    db.commit()
    db.refresh(incoming_record)
    return ApiResponse(
        message="Incoming record created successfully", data=incoming_record
    )


@router.get("/", response_model=ApiResponse[Sequence[IncomingRecordRead]])
def get_all_incoming_records(_: CurrentAdmin, db: DatabaseSession):
    records = db.exec(select(IncomingRecord)).all()
    return ApiResponse(message="Incoming records retrieved successfully", data=records)


@router.get("/{record_id}", response_model=ApiResponse[IncomingRecordRead])
def get_incoming_record(_: CurrentAdmin, record_id: UUID, db: DatabaseSession):
    record = db.get(IncomingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Incoming record not found")
    return ApiResponse(message="Incoming record retrieved successfully", data=record)


@router.put("/update/{record_id}", response_model=ApiResponse[IncomingRecordRead])
def update_incoming_record(
    _: CurrentAdmin,
    record_id: UUID,
    record_data: IncomingRecordUpdate,
    db: DatabaseSession,
):
    record = db.get(IncomingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Incoming record not found")

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
    return ApiResponse(message="Incoming record updated successfully", data=record)


@router.delete("/delete/{record_id}", status_code=204)
def delete_incoming_record(
    _: CurrentAdmin, record_id: UUID, db: DatabaseSession
) -> ApiResponse[None]:
    record = db.get(IncomingRecord, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Incoming record not found")

    payment_record = db.exec(
        select(PaymentRecord).where(PaymentRecord.payment_id == record.payment_id)
    ).first()
    if payment_record:
        db.delete(payment_record)

    db.delete(record)
    db.commit()
    return ApiResponse(message="Incoming record deleted successfully")
