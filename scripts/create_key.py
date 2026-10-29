"""
Script to generate and register a new API key.
Saves the SHA-256 hash in SQLite and displays the plain text key once.
Usage:
    python scripts/create_key.py [key_name] [rate_limit_per_min]
"""
import sys
import secrets
import os

# Add parent directory to sys.path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, engine, Base
from app.models import ApiKey
from app.auth import hash_key

# Ensure tables exist
Base.metadata.create_all(bind=engine)


def create_api_key(name: str = "default-client", rate_limit: int = 10) -> str:
    db = SessionLocal()
    try:
        # Generate a secure 32-character random key
        raw_key = f"sms_{secrets.token_urlsafe(24)}"
        hashed = hash_key(raw_key)

        new_key = ApiKey(
            key_hash=hashed,
            name=name,
            rate_limit_per_min=rate_limit
        )
        db.add(new_key)
        db.commit()
        db.refresh(new_key)

        print("\n" + "="*50)
        print("API Key Created Successfully!")
        print("="*50)
        print(f"Key ID:          {new_key.id}")
        print(f"Name:            {new_key.name}")
        print(f"Rate Limit:      {new_key.rate_limit_per_min} requests/min")
        print(f"Plain API Key:   {raw_key}")
        print("="*50)
        print("NOTE: Store this key safely. It cannot be retrieved again from the DB.")
        print("="*50 + "\n")
        return raw_key
    finally:
        db.close()


if __name__ == "__main__":
    key_name = sys.argv[1] if len(sys.argv) > 1 else "demo-user"
    rate = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    create_api_key(name=key_name, rate_limit=rate)
