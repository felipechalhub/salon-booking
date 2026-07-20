"""One-off utility: generates a bcrypt hash for ADMIN_PASSWORD_HASH in .env.

Usage: poetry run python scripts/hash_password.py <plain_password>
"""
import sys
import bcrypt
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: poetry run python scripts/hash_password.py <plain_password>")
        sys.exit(1)
    hashed = bcrypt.hashpw(sys.argv[1].encode(), bcrypt.gensalt())
    print(hashed.decode())