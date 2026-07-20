# app/models/__init__.py
# Importing here ensures Alembic sees all models during autogenerate
from app.models.location import Location
from app.models.client import Client
from app.models.service import Service
from app.models.staff import Staff, StaffWorkingHours
from app.models.appointment import Appointment, AppointmentStatus