# app/models/service.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    name = Column(String(100), nullable=False)         # e.g. "Full Color"
    description = Column(String(255), nullable=True)
    duration_minutes = Column(Integer, nullable=False)  # e.g. 120
    buffer_minutes = Column(Integer, default=15)        # cleanup time after
    price = Column(Integer, nullable=True)              # in cents, avoids float issues
    is_active = Column(Boolean, default=True)

    location = relationship("Location")