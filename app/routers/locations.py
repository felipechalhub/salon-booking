# app/routers/locations.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.location import Location

router = APIRouter()

@router.get("/")
async def list_locations(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Location).where(Location.is_active == True))
    return result.scalars().all()