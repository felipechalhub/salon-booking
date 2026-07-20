# app/admin/router.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.database import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.staff import Staff
from app.models.service import Service
from app.models.location import Location
from app.admin.auth import require_admin_session


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_session)])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end   = today_start + timedelta(days=1)
    week_end    = today_start + timedelta(days=7)

    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.staff),
        )
        .where(
            Appointment.start_time >= today_start,
            Appointment.start_time < today_end,
        )
        .order_by(Appointment.start_time)
    )
    today_appointments = result.scalars().all()

    week_result = await db.execute(
        select(func.count(Appointment.id)).where(
            Appointment.start_time >= today_start,
            Appointment.start_time < week_end,
        )
    )

    stats = {
        "today_total": len(today_appointments),
        "today_confirmed": sum(1 for a in today_appointments if a.status == AppointmentStatus.CONFIRMED),
        "upcoming_week": week_result.scalar(),
    }

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"today_appointments": today_appointments, "stats": stats},
    )


@router.get("/appointments", response_class=HTMLResponse)
async def list_appointments(
    request: Request,
    date: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.staff),
        )
        .order_by(Appointment.start_time.desc())
    )

    if date:
        day_start = datetime.fromisoformat(date).replace(tzinfo=timezone.utc)
        day_end   = day_start + timedelta(days=1)
        query = query.where(
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
        )

    if status:
        query = query.where(Appointment.status == AppointmentStatus(status))

    result = await db.execute(query)
    appointments = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="appointments.html",
        context={"appointments": appointments, "filters": {"date": date or "", "status": status or ""}},
    )


@router.patch("/appointments/{appointment_id}/cancel", response_class=HTMLResponse)
async def admin_cancel_appointment(
    appointment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.staff),
        )
        .where(Appointment.id == appointment_id)
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Not found")

    appt.status = AppointmentStatus.CANCELLED
    await db.flush()
    await db.refresh(appt)

    return templates.TemplateResponse(
        request=request,
        name="_appointment_row.html",
        context={"appt": appt},
    )


@router.get("/staff", response_class=HTMLResponse)
async def list_staff(request: Request, db: AsyncSession = Depends(get_db)):
    staff_result = await db.execute(
        select(Staff).options(selectinload(Staff.location)).order_by(Staff.full_name)
    )
    staff = staff_result.scalars().all()

    loc_result = await db.execute(select(Location).where(Location.is_active == True))
    locations = loc_result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="staff.html",
        context={"staff": staff, "locations": locations},
    )


@router.post("/staff", response_class=HTMLResponse)
async def create_staff(
    request: Request,
    full_name: str = Form(...),
    role: str = Form(""),
    phone: str = Form(""),
    location_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    member = Staff(
        full_name=full_name,
        role=role or None,
        phone=phone or None,
        location_id=location_id,
    )
    db.add(member)
    await db.flush()

    result = await db.execute(
        select(Staff)
        .options(selectinload(Staff.location))
        .where(Staff.id == member.id)
    )
    member = result.scalar_one()

    return templates.TemplateResponse(
        request=request,
        name="_staff_row.html",
        context={"member": member},
    )


@router.patch("/staff/{staff_id}/deactivate", response_class=HTMLResponse)
async def deactivate_staff(
    staff_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Staff).options(selectinload(Staff.location)).where(Staff.id == staff_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Not found")

    member.is_active = False
    await db.flush()
    await db.refresh(member)

    return templates.TemplateResponse(
        request=request,
        name="_staff_row.html",
        context={"member": member},
    )


@router.get("/services", response_class=HTMLResponse)
async def list_services(request: Request, db: AsyncSession = Depends(get_db)):
    svc_result = await db.execute(
        select(Service).options(selectinload(Service.location)).order_by(Service.name)
    )
    services = svc_result.scalars().all()

    loc_result = await db.execute(select(Location).where(Location.is_active == True))
    locations = loc_result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="services.html",
        context={"services": services, "locations": locations},
    )


@router.post("/services", response_class=HTMLResponse)
async def create_service(
    request: Request,
    name: str = Form(...),
    duration_minutes: int = Form(...),
    buffer_minutes: int = Form(15),
    price: Optional[int] = Form(None),
    location_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    svc = Service(
        name=name,
        duration_minutes=duration_minutes,
        buffer_minutes=buffer_minutes,
        price=price,
        location_id=location_id,
    )
    db.add(svc)
    await db.flush()

    result = await db.execute(
        select(Service)
        .options(selectinload(Service.location))
        .where(Service.id == svc.id)
    )
    svc = result.scalar_one()

    return templates.TemplateResponse(
        request=request,
        name="_service_row.html",
        context={"svc": svc},
    )


@router.patch("/services/{service_id}/deactivate", response_class=HTMLResponse)
async def deactivate_service(
    service_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Service)
        .options(selectinload(Service.location))
        .where(Service.id == service_id)
    )
    svc = result.scalar_one_or_none()
    if not svc:
        raise HTTPException(status_code=404, detail="Not found")

    svc.is_active = False
    await db.flush()
    await db.refresh(svc)

    return templates.TemplateResponse(
        request=request,
        name="_service_row.html",
        context={"svc": svc},
    )