# app/schemas/availability.py
from pydantic import BaseModel
from datetime import datetime

class AvailabilityRequest(BaseModel):
    staff_id: int
    service_id: int
    date: str   # "YYYY-MM-DD"

class TimeSlot(BaseModel):
    start: datetime
    end: datetime

class AvailabilityResponse(BaseModel):
    staff_id: int
    service_id: int
    date: str
    slots: list[TimeSlot]