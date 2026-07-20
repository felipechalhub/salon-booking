# app/schemas/service.py
from pydantic import BaseModel
from typing import Optional

class ServiceOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    duration_minutes: int
    buffer_minutes: int
    price: Optional[int]   # in cents

    class Config:
        from_attributes = True