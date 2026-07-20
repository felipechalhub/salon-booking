from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.routers import locations, services, staff, appointments, availability
from app.admin import router as admin_router
from app.admin.auth import NotAuthenticated
from app.admin.auth_router import router as admin_auth_router
from app.booking.router import router as booking_router  # correct path
from app.config import settings

app = FastAPI(
    title="Salon Booking API",
    version="0.1.0",
    docs_url="/docs",
)

app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, https_only=False)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(locations.router, prefix="/locations", tags=["Locations"])
app.include_router(services.router, prefix="/services", tags=["Services"])
app.include_router(staff.router, prefix="/staff", tags=["Staff"])
app.include_router(availability.router, prefix="/availability", tags=["Availability"])
app.include_router(appointments.router, prefix="/appointments", tags=["Appointments"])

app.include_router(admin_router.router, tags=["Admin"])
app.include_router(admin_auth_router, tags=["Admin Auth"])
app.include_router(booking_router, tags=["Booking"])


@app.exception_handler(NotAuthenticated)
async def not_authenticated_handler(request, exc):
    return RedirectResponse(url="/admin/login", status_code=303)


@app.get("/health")
async def health():
    return {"status": "ok"}