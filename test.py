
import asyncio
from app.database import AsyncSessionLocal
from app.models.staff import StaffWorkingHours
from datetime import time

async def seed():
    async with AsyncSessionLocal() as db:
        for day in range(0, 5):  # 0=Mon, 4=Fri
            db.add(StaffWorkingHours(
                staff_id=2,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(18, 0),
                is_day_off=False,
            ))
        await db.commit()
        print('Done')

asyncio.run(seed())
