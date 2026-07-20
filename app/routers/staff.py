# app/routers/staff.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.database import get_db
from app.models.staff import Staff

router = APIRouter()

@router.get("/")
async def list_staff(
    location_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    query = select(Staff).where(Staff.is_active == True)
    if location_id:
        query = query.where(Staff.location_id == location_id)
    result = await db.execute(query)
    return result.scalars().all()