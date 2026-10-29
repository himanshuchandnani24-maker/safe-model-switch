"""
Tests for in-memory sliding window rate limiting.
Verifies that exceeding the per-key limit returns 429 with Retry-After header.
"""
import uuid
import pytest
from starlette.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.database import SessionLocal
from app.models import ApiKey
from app.auth import hash_key
from app.rate_limit import clear_rate_limits

client = TestClient(app)


def test_rate_limit_exceeded_returns_429():
    clear_rate_limits()

    # Create a key with a strict limit of 5 requests per minute
    db = SessionLocal()
    raw_key = f"sms_ratelimit_{uuid.uuid4().hex[:12]}"
    db_key = ApiKey(key_hash=hash_key(raw_key), name="rate-limit-test", rate_limit_per_min=5)
    db.add(db_key)
    db.commit()
    db.close()

    headers = {"X-API-Key": raw_key}

    with patch("app.main.call_gemini", return_value=("Mock reply", 5, 5, 20)):
        # First 5 calls must succeed (200 OK)
        for i in range(5):
            res = client.post("/chat", json={"prompt": f"Test {i}"}, headers=headers)
            assert res.status_code == 200

        # The 6th call must fail with 429 Too Many Requests
        res_overflow = client.post("/chat", json={"prompt": "Overflow test"}, headers=headers)
        assert res_overflow.status_code == 429
        assert "Retry-After" in res_overflow.headers
        assert int(res_overflow.headers["Retry-After"]) > 0
