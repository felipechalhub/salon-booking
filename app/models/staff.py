# app/models/staff.py
from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, Time
from sqlalchemy.orm import relationship
from app.database import Base

class Staff(Base):
    __tablename__ = "staff"

    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(50))                          # e.g. "Colorist", "Stylist"
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)

    location = relationship("Location")
    working_hours = relationship("StaffWorkingHours", back_populates="staff")


class StaffWorkingHours(Base):
    """
    Defines what hours a staff member works on each day of the week.
    day_of_week: 0=Monday, 6=Sunday (Python's weekday() standard)
    """
    __tablename__ = "staff_working_hours"

    id = Column(Integer, primary_key=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)      # 0-6
    start_time = Column(Time, nullable=False)           # e.g. 09:00
    end_time = Column(Time, nullable=False)             # e.g. 18:00
    is_day_off = Column(Boolean, default=False)

    staff = relationship("Staff", back_populates="working_hours")