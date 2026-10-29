"""
Tests for request logging into SQLite.
Verifies that calls to POST /chat persist correctly in the requests table.
"""
import uuid
import pytest
from starlette.testclient import TestClient
from unittest.mock import patch
from app.main import app
from app.database import SessionLocal
from app.models import ApiKey, RequestLog
from app.auth import hash_key
from app.rate_limit import clear_rate_limits

client = TestClient(app)


def test_request_logged_in_database():
    clear_rate_limits()
    db = SessionLocal()
    raw_key = f"sms_log_{uuid.uuid4().hex[:12]}"
    db_key = ApiKey(key_hash=hash_key(raw_key), name="log-test", rate_limit_per_min=20)
    db.add(db_key)
    db.commit()

    prompt_text = "What is safe model switch?"
    with patch("app.main.call_gemini", return_value=("An evaluation proxy", 8, 4, 150)):
        res = client.post(
            "/chat",
            json={"prompt": prompt_text},
            headers={"X-API-Key": raw_key}
        )
        assert res.status_code == 200

    # Verify directly in SQLite
    logged_req = (
        db.query(RequestLog)
        .filter(RequestLog.prompt == prompt_text)
        .order_by(RequestLog.id.desc())
        .first()
    )
    assert logged_req is not None
    assert logged_req.response == "An evaluation proxy"
    assert logged_req.input_tokens == 8
    assert logged_req.output_tokens == 4
    assert logged_req.latency_ms == 150
    assert logged_req.status == "ok"
    assert logged_req.est_cost_usd > 0
    db.close()
