# app/schemas/appointment.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.appointment import AppointmentStatus

class AppointmentCreate(BaseModel):
    client_phone: str           # look up or create client by phone
    client_name: str
    staff_id: int
    service_id: int
    location_id: int
    start_time: datetime
    notes: Optional[str] = None

class AppointmentOut(BaseModel):
    id: int
    status: AppointmentStatus
    start_time: datetime
    end_time: datetime
    notes: Optional[str]

    class Config:
        from_attributes = True

class AppointmentCancel(BaseModel):
    reason: Optional[str] = None

class AppointmentReschedule(BaseModel):
    new_start_time: datetime