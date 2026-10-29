"""
Safe Model Switch - FastAPI Gateway Entry Point.
Implements the 6 endpoints required by Section 7:
- GET /health
- POST /chat
- GET /logs
- POST /replay
- POST /score
- GET /report
"""
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import ApiKey, RequestLog, Replay, Score
from app.schemas import (
    ChatRequest, ChatResponse, RequestLogResponse,
    ReplayRequest, ReplayItemResponse, ScoreItemResponse,
    ReportResponse
)
from app.config import settings, calculate_cost
from app.auth import get_current_api_key
from app.rate_limit import check_rate_limit
from app.providers import call_gemini
from app.replay import run_replay
from app.scoring import score_unscored_replays
from app.report import calculate_report_data

# Ensure all database tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Safe Model Switch Gateway",
    description="Cost and quality evaluation proxy for migrating LLM workloads safely.",
    version="1.0.0"
)


@app.get("/health")
def get_health():
    """Returns {'status': 'ok'}."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    api_key: ApiKey = Depends(get_current_api_key),
    db: Session = Depends(get_db)
):
    """
    Needs header X-API-Key.
    1. Checks API key validity (401 on failure).
    2. Checks in-memory sliding window rate limiter (429 on failure).
    3. Sends prompt to Model A (Gemini).
    4. Logs prompt, response, tokens, latency, cost to SQLite.
    5. Returns answer + metrics (502 if provider call fails).
    """
    # Check rate limit
    check_rate_limit(api_key)

    # Call Model A (Gemini)
    try:
        answer, in_tok, out_tok, latency = await call_gemini(
            prompt=body.prompt,
            model_name=settings.MODEL_A,
            api_key=settings.GEMINI_API_KEY
        )
        est_cost = calculate_cost(settings.MODEL_A, in_tok, out_tok)
        status = "ok"
    except Exception as e:
        # Log failure with status="error" before raising 502
        error_log = RequestLog(
            api_key_id=api_key.id,
            prompt=body.prompt,
            response=f"Error: {str(e)}",
            model=settings.MODEL_A,
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
            est_cost_usd=0.0,
            status="error"
        )
        db.add(error_log)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Model A provider failed: {str(e)}")

    # Log successful request
    req_log = RequestLog(
        api_key_id=api_key.id,
        prompt=body.prompt,
        response=answer,
        model=settings.MODEL_A,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=latency,
        est_cost_usd=est_cost,
        status=status
    )
    db.add(req_log)
    db.commit()
    db.refresh(req_log)

    return ChatResponse(
        answer=answer,
        model=settings.MODEL_A,
        input_tokens=in_tok,
        output_tokens=out_tok,
        latency_ms=latency,
        est_cost_usd=est_cost
    )


@app.get("/logs", response_model=List[RequestLogResponse])
def get_logs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Returns recent logged requests."""
    logs = (
        db.query(RequestLog)
        .order_by(RequestLog.id.desc())
        .limit(limit)
        .all()
    )
    return logs


@app.post("/replay", response_model=List[ReplayItemResponse])
async def replay_endpoint(
    body: Optional[ReplayRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Re-runs the last N logged prompts on Model B (Groq).
    Waits REPLAY_DELAY_SECONDS between calls.
    """
    n_count = body.n if body else 20
    replays = await run_replay(db=db, n=n_count)
    return replays


@app.post("/score", response_model=List[ScoreItemResponse])
async def score_endpoint(db: Session = Depends(get_db)):
    """
    Scores all unscored replays:
    1. Exact match first (5/5).
    2. LLM judge via Gemini for non-exact matches.
    """
    scores = await score_unscored_replays(db=db)
    return scores


@app.get("/report", response_model=ReportResponse)
def get_report(db: Session = Depends(get_db)):
    """Returns averages for Model A vs Model B and the final verdict."""
    data = calculate_report_data(db=db)
    return data
