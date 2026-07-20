from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, datetime, timezone
import asyncio
import httpx

from app.database import get_db
from app.models.service import Service
from app.models.staff import Staff
from app.services.email import send_booking_confirmation

router = APIRouter(prefix="/book", tags=["booking"])
templates = Jinja2Templates(directory="app/templates/booking")


@router.get("/", response_class=HTMLResponse)
async def booking_home(request: Request, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.is_active == True))
    services = result.scalars().all()
    return templates.TemplateResponse(
        request=request, name="step1_service.html", context={"services": services}
    )


@router.get("/staff", response_class=HTMLResponse)
async def booking_staff(
    request: Request, service_id: int, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Staff).where(Staff.is_active == True))
    staff_list = result.scalars().all()
    service = await db.get(Service, service_id)
    return templates.TemplateResponse(
        request=request,
        name="step2_staff.html",
        context={"staff_list": staff_list, "service": service},
    )


@router.get("/datetime", response_class=HTMLResponse)
async def booking_datetime(
    request: Request, service_id: int, staff_id: int, db: AsyncSession = Depends(get_db)
):
    service = await db.get(Service, service_id)
    staff = await db.get(Staff, staff_id)
    today = date.today().isoformat()
    return templates.TemplateResponse(
        request=request,
        name="step3_datetime.html",
        context={"service": service, "staff": staff, "today": today},
    )


@router.get("/slots", response_class=HTMLResponse)
async def booking_slots(
    request: Request, service_id: int, staff_id: int, date: str
):
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        resp = await client.get(
            "/availability/",
            params={"staff_id": staff_id, "service_id": service_id, "date": date},
        )
    slots = resp.json().get("slots", []) if resp.status_code == 200 else []
    return templates.TemplateResponse(
        request=request,
        name="_slots.html",
        context={"slots": slots, "service_id": service_id, "staff_id": staff_id, "date": date},
    )


@router.get("/details", response_class=HTMLResponse)
async def booking_details(
    request: Request, service_id: int, staff_id: int, slot: str,
    db: AsyncSession = Depends(get_db)
):
    service = await db.get(Service, service_id)
    staff = await db.get(Staff, staff_id)
    slot_dt = datetime.fromisoformat(slot)
    return templates.TemplateResponse(
        request=request,
        name="step4_details.html",
        context={
            "service": service,
            "staff": staff,
            "slot": slot,
            "slot_display": slot_dt.strftime("%A, %B %d at %H:%M"),
        },
    )


@router.post("/confirm", response_class=HTMLResponse)
async def booking_confirm(
    request: Request,
    service_id: int = Form(...),
    staff_id: int = Form(...),
    slot: str = Form(...),
    client_name: str = Form(...),
    client_phone: str = Form(...),
    client_email: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    staff = await db.get(Staff, staff_id)
    service = await db.get(Service, service_id)
    slot_dt = datetime.fromisoformat(slot)
    if slot_dt.tzinfo is None:
        slot_dt = slot_dt.replace(tzinfo=timezone.utc)

    payload = {
        "staff_id": staff_id,
        "service_id": service_id,
        "location_id": staff.location_id,
        "client_name": client_name,
        "client_phone": client_phone,
        "client_email": client_email,
        "start_time": slot_dt.isoformat(),
    }

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        resp = await client.post("/appointments/", json=payload)

    if resp.status_code in (200, 201):
        appt = resp.json()
        appointment_id = appt.get("id")
        slot_display = slot_dt.strftime("%A, %B %d at %H:%M")

        # Fire and forget - never blocks the response
        asyncio.create_task(
            send_booking_confirmation(
                to_email=client_email,
                client_name=client_name,
                service_name=service.name,
                staff_name=staff.full_name,
                slot_display=slot_display,
                appointment_id=appointment_id,
            )
        )

        return templates.TemplateResponse(
            request=request,
            name="step5_confirmation.html",
            context={
                "client_name": client_name,
                "service": service,
                "staff": staff,
                "slot_display": slot_display,
                "appointment_id": appointment_id,
                "error": None,
            },
        )

    return templates.TemplateResponse(
        request=request,
        name="step5_confirmation.html",
        context={
            "error": resp.json().get("detail", "Something went wrong. Please try again."),
            "client_name": client_name,
            "service": service,
            "staff": staff,
            "slot_display": slot_dt.strftime("%A, %B %d at %H:%M"),
            "appointment_id": None,
        },
        status_code=400,
    )