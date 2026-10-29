"""
Replay engine for Safe Model Switch.
Fetches recent prompts logged from Model A and re-runs them through Model B (Groq).
Handles pacing delays, retries for rate limits, and failure resilience.
"""
import asyncio
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.config import settings, calculate_cost
from app.models import RequestLog, Replay
from app.providers import call_groq

logger = logging.getLogger("replay_engine")


async def run_replay(db: Session, n: int = 20) -> List[Replay]:
    """
    Replays the last N prompts logged from Model A through Model B.
    - Limits to N requests.
    - Waits REPLAY_DELAY_SECONDS between calls.
    - Retries up to 2 times on rate limit errors.
    - Saves replay results to the SQLite replays table.
    """
    # Fetch last N logged requests ordered by newest first
    recent_requests = (
        db.query(RequestLog)
        .filter(RequestLog.status == "ok")
        .order_by(RequestLog.id.desc())
        .limit(n)
        .all()
    )

    replays_created: List[Replay] = []

    for req in recent_requests:
        candidate_response = None
        input_tokens = 0
        output_tokens = 0
        latency_ms = 0
        est_cost = 0.0
        status = "ok"

        # Retry logic: up to 2 retries
        for attempt in range(3):
            try:
                candidate_response, input_tokens, output_tokens, latency_ms = await call_groq(
                    prompt=req.prompt,
                    model_name=settings.MODEL_B,
                    api_key=settings.GROQ_API_KEY
                )
                est_cost = calculate_cost(settings.MODEL_B, input_tokens, output_tokens)
                status = "ok"
                break
            except Exception as e:
                logger.warning(f"Groq call failed on attempt {attempt + 1}: {e}")
                if attempt < 2:
                    await asyncio.sleep(2.0 * (attempt + 1))  # exponential backoff
                else:
                    status = "error"
                    candidate_response = f"Provider error: {str(e)}"

        # Save replay record
        replay_record = Replay(
            request_id=req.id,
            candidate_model=settings.MODEL_B,
            candidate_response=candidate_response,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            est_cost_usd=est_cost,
            status=status
        )
        db.add(replay_record)
        db.commit()
        db.refresh(replay_record)
        replays_created.append(replay_record)

        # Free tier safety delay
        if settings.REPLAY_DELAY_SECONDS > 0:
            await asyncio.sleep(settings.REPLAY_DELAY_SECONDS)

    return replays_created
