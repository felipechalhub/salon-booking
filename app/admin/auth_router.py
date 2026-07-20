from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.admin.auth import verify_credentials


# Intentionally NOT protected by require_admin_session, this is the router
# that lets you become authenticated in the first place.
router = APIRouter(prefix="/admin", tags=["admin-auth"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/login-test")
async def login_test(request: Request):
    from app.config import settings
    import bcrypt
    stored = settings.admin_password_hash
    return {
        "stored_hash": stored,
        "stored_length": len(stored),
        "expected_length": 60,
    }

@router.get("/login")
async def login_form(request: Request):
    return templates.TemplateResponse(
        request=request, name="login.html", context={"error": None}
    )


@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not verify_credentials(username, password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Invalid username or password"},
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    request.session["admin_authenticated"] = True
    return RedirectResponse(url="/admin/", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)