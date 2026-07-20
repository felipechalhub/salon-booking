"""
Generates a bcrypt hash and writes it directly to .env.
No copy-paste, no truncation risk.

Usage: poetry run python scripts/setup_admin.py <password>
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt

if len(sys.argv) != 2:
    print("Usage: poetry run python scripts/setup_admin.py <password>")
    sys.exit(1)

password = sys.argv[1]
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

env_path = Path(__file__).resolve().parent.parent / ".env"
content = env_path.read_text(encoding="utf-8")

if "ADMIN_PASSWORD_HASH" in content:
    content = re.sub(r'ADMIN_PASSWORD_HASH=.*', f'ADMIN_PASSWORD_HASH={hashed}', content)
else:
    content += f'\nADMIN_PASSWORD_HASH={hashed}'

env_path.write_text(content, encoding="utf-8")
print(f"Done. Hash written to .env ({len(hashed)} chars)")
print(f"Hash: {hashed}")