"""
Tests for API key authentication.
Verifies missing keys, invalid keys, and valid key authentication.
"""
import uuid
import pytest
from starlette.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.database import SessionLocal
from app.models import ApiKey
from app.auth import hash_key

client = TestClient(app)


def test_missing_api_key_returns_401():
    response = client.post("/chat", json={"prompt": "Hello"})
    assert response.status_code == 401
    assert "Missing API Key" in response.json()["detail"]


def test_invalid_api_key_returns_401():
    response = client.post(
        "/chat",
        json={"prompt": "Hello"},
        headers={"X-API-Key": "completely_invalid_key"}
    )
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]


def test_valid_api_key_authorized():
    db = SessionLocal()
    raw_key = f"sms_test_{uuid.uuid4().hex[:12]}"
    db_key = ApiKey(key_hash=hash_key(raw_key), name="auth-test", rate_limit_per_min=10)
    db.add(db_key)
    db.commit()
    db.close()

    with patch("app.main.call_gemini", return_value=("Test Answer", 5, 10, 50)):
        response = client.post(
            "/chat",
            json={"prompt": "Hello"},
            headers={"X-API-Key": raw_key}
        )
        assert response.status_code == 200
        assert response.json()["answer"] == "Test Answer"
