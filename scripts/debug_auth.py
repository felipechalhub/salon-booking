import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from dotenv import load_dotenv
load_dotenv(override=True)

from app.config import settings

password = "mynewpassword123"

print("Stored hash:", repr(settings.admin_password_hash))
print("Stored hash length:", len(settings.admin_password_hash))
print("bcrypt result:", bcrypt.checkpw(password.encode(), settings.admin_password_hash.encode()))