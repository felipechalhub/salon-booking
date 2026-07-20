# app/routers/appointments.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.client import Client
from app.models.service import Service
from app.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentCancel, AppointmentReschedule
from app.services.availability import is_slot_available
from datetime import timedelta

router = APIRouter()

@router.post("/", response_model=AppointmentOut, status_code=201)
async def create_appointment(payload: AppointmentCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Client).where(Client.phone == payload.client_phone))
    client = result.scalar_one_or_none()
    if not client:
        client = Client(full_name=payload.client_name, phone=payload.client_phone)
        db.add(client)
        await db.flush()

    service = await db.get(Service, payload.service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    total_minutes = service.duration_minutes + service.buffer_minutes
    end_time = payload.start_time + timedelta(minutes=total_minutes)

    available = await is_slot_available(db, payload.staff_id, payload.start_time, end_time)
    if not available:
        raise HTTPException(status_code=409, detail="Time slot is not available")

    appointment = Appointment(
        client_id=client.id,
        staff_id=payload.staff_id,
        service_id=payload.service_id,
        location_id=payload.location_id,
        start_time=payload.start_time,
        end_time=end_time,
        status=AppointmentStatus.CONFIRMED,
        notes=payload.notes,
    )
    db.add(appointment)
    await db.flush()           # writes to DB within transaction, assigns the ID
    await db.refresh(appointment)  # pulls the DB-generated values back into the object
    return appointment


@router.patch("/{appointment_id}/cancel", response_model=AppointmentOut)
async def cancel_appointment(
    appointment_id: int,
    payload: AppointmentCancel,
    db: AsyncSession = Depends(get_db)
):
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Appointment already cancelled")

    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancellation_reason = payload.reason
    await db.flush()
    await db.refresh(appointment)
    return appointment


@router.patch("/{appointment_id}/reschedule", response_model=AppointmentOut)
async def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedule,
    db: AsyncSession = Depends(get_db)
):
    appointment = await db.get(Appointment, appointment_id)
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.status == AppointmentStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot reschedule a cancelled appointment")

    service = await db.get(Service, appointment.service_id)
    total_minutes = service.duration_minutes + service.buffer_minutes
    new_end = payload.new_start_time + timedelta(minutes=total_minutes)

    # Check availability, excluding the current appointment
    available = await is_slot_available(
        db, appointment.staff_id, payload.new_start_time, new_end,
        exclude_appointment_id=appointment_id
    )
    if not available:
        raise HTTPException(status_code=409, detail="New time slot is not available")

    appointment.start_time = payload.new_start_time
    appointment.end_time = new_end
    await db.flush()
    await db.refresh(appointment)
    return appointment