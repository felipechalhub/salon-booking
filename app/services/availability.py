from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.appointment import Appointment, AppointmentStatus
from app.models.staff import StaffWorkingHours


async def is_slot_available(
    db: AsyncSession,
    staff_id: int,
    start: datetime,
    end: datetime,
    exclude_appointment_id: Optional[int] = None,
) -> bool:
    query = select(Appointment).where(
        and_(
            Appointment.staff_id == staff_id,
            Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING]),
            Appointment.start_time < end,
            Appointment.end_time > start,
        )
    )
    if exclude_appointment_id:
        query = query.where(Appointment.id != exclude_appointment_id)

    result = await db.execute(query)
    return result.scalar_one_or_none() is None


async def get_available_slots(
    db: AsyncSession,
    staff_id: int,
    service_duration_minutes: int,
    buffer_minutes: int,
    target_date: date,
    slot_interval_minutes: int = 30,
) -> list[dict]:
    day_of_week = target_date.weekday()

    wh_result = await db.execute(
        select(StaffWorkingHours).where(
            and_(
                StaffWorkingHours.staff_id == staff_id,
                StaffWorkingHours.day_of_week == day_of_week,
                StaffWorkingHours.is_day_off == False,
            )
        )
    )
    working_hours = wh_result.scalar_one_or_none()
    if not working_hours:
        return []

    day_start = datetime.combine(target_date, time.min).replace(tzinfo=timezone.utc)
    day_end = datetime.combine(target_date, time.max).replace(tzinfo=timezone.utc)

    appt_result = await db.execute(
        select(Appointment).where(
            and_(
                Appointment.staff_id == staff_id,
                Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING]),
                Appointment.start_time >= day_start,
                Appointment.start_time <= day_end,
            )
        )
    )
    existing_appointments = appt_result.scalars().all()
    booked_ranges = [(a.start_time, a.end_time) for a in existing_appointments]

    total_duration = timedelta(minutes=service_duration_minutes + buffer_minutes)
    interval = timedelta(minutes=slot_interval_minutes)

    # Generate slots as UTC-aware datetimes so comparison with DB values works
    work_start = datetime.combine(target_date, working_hours.start_time).replace(tzinfo=timezone.utc)
    work_end = datetime.combine(target_date, working_hours.end_time).replace(tzinfo=timezone.utc)

    slots = []
    cursor = work_start

    while cursor + total_duration <= work_end:
        candidate_end = cursor + total_duration

        overlaps = any(
            existing_start < candidate_end and existing_end > cursor
            for existing_start, existing_end in booked_ranges
        )

        if not overlaps:
            slots.append({"start": cursor, "end": candidate_end})

        cursor += interval

    return slots