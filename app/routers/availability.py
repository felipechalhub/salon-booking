# app/routers/availability.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date
from app.database import get_db
from app.models.service import Service
from app.schemas.availability import AvailabilityResponse
from app.services.availability import get_available_slots

router = APIRouter()

@router.get("/", response_model=AvailabilityResponse)
async def check_availability(
    staff_id: int,
    service_id: int,
    date: date,
    db: AsyncSession = Depends(get_db)
):
    service = await db.get(Service, service_id)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    slots = await get_available_slots(
        db=db,
        staff_id=staff_id,
        service_duration_minutes=service.duration_minutes,
        buffer_minutes=service.buffer_minutes,
        target_date=date,
    )

    return AvailabilityResponse(
        staff_id=staff_id,
        service_id=service_id,
        date=str(date),
        slots=slots,
    )