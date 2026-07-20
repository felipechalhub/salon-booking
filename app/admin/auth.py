import bcrypt
from starlette.requests import Request
from app.config import settings


class NotAuthenticated(Exception):
    """Raised when a protected admin route is hit without a valid session."""


def verify_credentials(username: str, password: str) -> bool:
    if username != settings.admin_username:
        return False
    return bcrypt.checkpw(password.encode(), settings.admin_password_hash.encode())


def require_admin_session(request: Request) -> None:
    if not request.session.get("admin_authenticated"):
        raise NotAuthenticated()