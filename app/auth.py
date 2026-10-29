"""
API Key authentication using SHA-256 hashing.
Validates the X-API-Key header against hashed keys in the database.
"""
import hashlib
from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ApiKey


def hash_key(raw_key: str) -> str:
    """Hash an API key using SHA-256 for secure database storage."""
    return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()


def get_current_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> ApiKey:
    """
    Dependency that enforces API key authentication.
    - Returns 401 if key is missing or invalid.
    - Returns the ApiKey database record on success.
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API Key. Please provide the 'X-API-Key' header."
        )

    hashed = hash_key(x_api_key)
    api_key_record = db.query(ApiKey).filter(ApiKey.key_hash == hashed).first()

    if not api_key_record:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key."
        )

    return api_key_record
