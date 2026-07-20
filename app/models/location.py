# app/models/location.py
from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    address = Column(String(255))
    city = Column(String(100))
    phone = Column(String(20))
    instagram_handle = Column(String(50))
    is_active = Column(Boolean, default=True)