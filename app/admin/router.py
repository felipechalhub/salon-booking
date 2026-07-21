# app/admin/router.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta, date as date_type
from typing import Optional
import asyncio
import httpx

from app.database import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.staff import Staff
from app.models.service import Service
from app.models.location import Location
from app.admin.auth import require_admin_session
from app.services.availability import is_slot_available
from app.services.email import send_booking_confirmation, send_reschedule_notification

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_session)])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end   = today_start + timedelta(days=1)
    week_end    = today_start + timedelta(days=7)

    # Auto-complete past appointments (end_time > 1 hour ago, still confirmed)
    stale_cutoff = now - timedelta(hours=1)
    stale_result = await db.execute(
        select(Appointment).where(
            Appointment.status == AppointmentStatus.CONFIRMED,
            Appointment.end_time < stale_cutoff,
        )
    )
    stale = stale_result.scalars().all()
    for appt in stale:
        appt.status = AppointmentStatus.COMPLETED
    if stale:
        await db.flush()

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
    client: Optional[str] = None,
    sort: Optional[str] = "date",
    dir: Optional[str] = "desc",
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.staff),
        )
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
    if client:
        # join to filter by client name
        from app.models.client import Client as ClientModel
        query = query.join(ClientModel, Appointment.client_id == ClientModel.id).where(
            ClientModel.full_name.ilike(f"%{client}%")
        )

    # sorting
    if sort == "client":
        from app.models.client import Client as ClientModel
        if not client:  # avoid double join
            query = query.join(ClientModel, Appointment.client_id == ClientModel.id)
        order_col = ClientModel.full_name
    else:
        order_col = Appointment.start_time

    query = query.order_by(order_col.asc() if dir == "asc" else order_col.desc())

    result = await db.execute(query)
    appointments = result.scalars().all()

    return templates.TemplateResponse(
        request=request,
        name="appointments.html",
        context={
            "appointments": appointments,
            "filters": {
                "date": date or "",
                "status": status or "",
                "client": client or "",
                "sort": sort or "date",
                "dir": dir or "desc",
            },
        },
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


@router.patch("/appointments/{appointment_id}/confirm", response_class=HTMLResponse)
async def admin_confirm_appointment(
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

    appt.status = AppointmentStatus.CONFIRMED
    await db.flush()
    await db.refresh(appt)

    return templates.TemplateResponse(
        request=request,
        name="_appointment_row.html",
        context={"appt": appt},
    )


@router.patch("/appointments/{appointment_id}/complete", response_class=HTMLResponse)
async def admin_complete_appointment(
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

    appt.status = AppointmentStatus.COMPLETED
    await db.flush()
    await db.refresh(appt)

    return templates.TemplateResponse(
        request=request,
        name="_appointment_row.html",
        context={"appt": appt},
    )
from sqlalchemy import func as sqlfunc
from app.models.client import Client

@router.get("/clients", response_class=HTMLResponse)
async def list_clients(
    request: Request,
    search: Optional[str] = None,
    sort: Optional[str] = "name",
    dir: Optional[str] = "asc",
    db: AsyncSession = Depends(get_db),
):
    query = select(Client)
    if search:
        query = query.where(
            or_(Client.full_name.ilike(f"%{search}%"), Client.phone.ilike(f"%{search}%"))
        )
    result = await db.execute(query)
    all_clients = result.scalars().all()

    rows = []
    for c in all_clients:
        appt_result = await db.execute(
            select(sqlfunc.count(Appointment.id), sqlfunc.max(Appointment.start_time))
            .where(Appointment.client_id == c.id)
        )
        total, last_visit = appt_result.one()
        rows.append({"client": c, "total": total or 0, "last_visit": last_visit})

    # sort
    reverse = dir == "desc"
    if sort == "total":
        rows.sort(key=lambda r: r["total"], reverse=reverse)
    elif sort == "last_visit":
        rows.sort(key=lambda r: r["last_visit"] or datetime.min.replace(tzinfo=timezone.utc), reverse=reverse)
    else:
        rows.sort(key=lambda r: r["client"].full_name.lower(), reverse=reverse)

    return templates.TemplateResponse(
        request=request,
        name="clients.html",
        context={"clients": rows, "search": search or "", "sort": sort, "dir": dir},
    )


@router.get("/clients/{client_id}", response_class=HTMLResponse)
async def client_profile(
    client_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    appt_result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.staff))
        .where(Appointment.client_id == client_id)
        .order_by(Appointment.start_time.desc())
    )
    appointments = appt_result.scalars().all()

    completed = [a for a in appointments if a.status.value == "completed"]
    cancelled = [a for a in appointments if a.status.value == "cancelled"]
    total_spent = sum(a.service.price or 0 for a in completed if a.service.price)

    stats = {
        "total": len(appointments),
        "completed": len(completed),
        "cancelled": len(cancelled),
        "last_visit": completed[0].start_time if completed else None,
        "last_service": completed[0].service.name if completed else None,
        "total_spent": total_spent,
    }

    return templates.TemplateResponse(
        request=request,
        name="client_profile.html",
        context={"client": client, "appointments": appointments, "stats": stats},
    )


@router.get("/clients/{client_id}/edit-form", response_class=HTMLResponse)
async def client_edit_form(client_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Not found")
    return templates.TemplateResponse(
        request=request, name="_client_edit_form.html", context={"client": client}
    )


@router.get("/clients/{client_id}/contact-card", response_class=HTMLResponse)
async def client_contact_card(client_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Not found")
    return templates.TemplateResponse(
        request=request, name="_client_contact_card.html", context={"client": client}
    )


@router.patch("/clients/{client_id}", response_class=HTMLResponse)
async def update_client(
    client_id: int,
    request: Request,
    full_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    client = await db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Not found")

    client.full_name = full_name
    client.phone = phone
    client.email = email or None
    await db.commit()
    await db.refresh(client)

    return templates.TemplateResponse(
        request=request, name="_client_contact_card.html", context={"client": client}
    )


@router.get("/appointments/{appointment_id}/reschedule-form", response_class=HTMLResponse)
async def reschedule_form(
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
    return templates.TemplateResponse(
        request=request,
        name="_appointment_reschedule.html",
        context={"appt": appt, "today": date_type.today().isoformat()},
    )


@router.get("/appointments/{appointment_id}/cancel-reschedule", response_class=HTMLResponse)
async def cancel_reschedule(
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
    return templates.TemplateResponse(
        request=request,
        name="_appointment_row.html",
        context={"appt": appt},
    )


@router.get("/appointments/{appointment_id}/slots", response_class=HTMLResponse)
async def reschedule_slots(
    appointment_id: int,
    request: Request,
    service_id: int,
    staff_id: int,
    date: str,
):
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        resp = await client.get(
            "/availability/",
            params={"staff_id": staff_id, "service_id": service_id, "date": date},
        )
    slots = resp.json().get("slots", []) if resp.status_code == 200 else []
    return templates.TemplateResponse(
        request=request,
        name="_reschedule_slots.html",
        context={"slots": slots, "appointment_id": appointment_id},
    )


@router.post("/appointments/{appointment_id}/reschedule", response_class=HTMLResponse)
async def reschedule_appointment(
    appointment_id: int,
    request: Request,
    new_start_time: str = Form(...),
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

    new_start = datetime.fromisoformat(new_start_time)
    if new_start.tzinfo is None:
        new_start = new_start.replace(tzinfo=timezone.utc)

    total_minutes = appt.service.duration_minutes + (appt.service.buffer_minutes or 0)
    new_end = new_start + timedelta(minutes=total_minutes)

    available = await is_slot_available(
        db, appt.staff_id, new_start, new_end,
        exclude_appointment_id=appointment_id,
    )
    if not available:
        raise HTTPException(status_code=409, detail="Slot no longer available")

    old_display = appt.start_time.strftime("%A, %B %d at %H:%M")
    new_display = new_start.strftime("%A, %B %d at %H:%M")

    appt.start_time = new_start
    appt.end_time = new_end
    appt.status = AppointmentStatus.CONFIRMED
    await db.commit()
    await db.refresh(appt)

    if appt.client.email:
        asyncio.create_task(
            send_reschedule_notification(
                to_email=appt.client.email,
                client_name=appt.client.full_name,
                service_name=appt.service.name,
                staff_name=appt.staff.full_name,
                old_slot_display=old_display,
                new_slot_display=new_display,
                appointment_id=appt.id,
            )
        )

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
    price: Optional[float] = Form(None),
    location_id: int = Form(...),
    db: AsyncSession = Depends(get_db),
):
    svc = Service(
        name=name,
        duration_minutes=duration_minutes,
        buffer_minutes=buffer_minutes,
        price=int(price * 100) if price is not None else None,
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