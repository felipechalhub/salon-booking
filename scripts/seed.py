# scripts/seed.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from app.database import AsyncSessionLocal
from app.models.location import Location
from app.models.staff import Staff, StaffWorkingHours
from app.models.service import Service
from datetime import time

async def seed():
    async with AsyncSessionLocal() as db:
        # Guard: skip if already seeded
        from sqlalchemy import select
        existing = await db.execute(select(Location))
        if existing.scalar_one_or_none():
            print("Already seeded, skipping.")
            return

        # ... rest of seed unchanged
        loc = Location(name="Salon Central", address="Rua das Flores 100", city="São Paulo")
        db.add(loc)
        await db.flush()
        await db.refresh(loc)

        staff = Staff(location_id=loc.id, full_name="Ana Lima", role="Colorist")
        db.add(staff)
        await db.flush()
        await db.refresh(staff)

        for day in range(5):
            db.add(StaffWorkingHours(
                staff_id=staff.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(18, 0),
            ))

        svc = Service(
            location_id=loc.id,
            name="Full Color",
            duration_minutes=120,
            buffer_minutes=15,
            price=25000,
        )
        db.add(svc)
        await db.commit()
        print(f"Seeded: location={loc.id}, staff={staff.id}, service={svc.id}")

asyncio.run(seed())