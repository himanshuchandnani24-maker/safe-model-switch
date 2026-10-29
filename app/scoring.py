"""
Scoring engine for Safe Model Switch.
Follows Section 8 of the project guide:
1. Exact Match check (case-insensitive, trimmed) -> score 5, saves free quota.
2. LLM Judge via Gemini using strict prompt rubric -> 1 to 5 score + reason.
Safe JSON parsing with fallback to uncertain if LLM response is unparseable.
"""
import json
import re
import logging
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Replay, Score
from app.providers import call_gemini

logger = logging.getLogger("scoring_engine")

JUDGE_PROMPT_TEMPLATE = """You are a strict evaluator. Compare two answers to the same question.

Question: {prompt}
Answer A: {answer_a}
Answer B: {answer_b}

Score Answer B from 1 to 5 using Answer A as the reference for the task:
5 = same quality or better, fully correct and complete
4 = minor differences, still correct
3 = partly correct or missing something important
2 = mostly wrong or unhelpful
1 = wrong or irrelevant

Judge correctness, completeness, and clarity. Ignore answer length and style.
Reply with ONLY valid JSON, no other text:
{{"score": <1-5>, "reason": "<one short sentence>"}}"""


def check_exact_match(answer_a: str, answer_b: str) -> bool:
    """Check if answers are identical after stripping whitespace and lowercasing."""
    if not answer_a or not answer_b:
        return False
    return answer_a.strip().lower() == answer_b.strip().lower()


def parse_judge_json(raw_text: str) -> Tuple[Optional[int], Optional[str], bool]:
    """
    Safely parse the LLM judge's output to extract score (1-5) and reason.
    If parsing fails, returns (None, reason, False) to mark as 'uncertain'.
    """
    if not raw_text:
        return None, "Empty response from judge", False

    # Extract JSON substring if wrapped in markdown codeblocks (e.g. ```json ... ```)
    cleaned = raw_text.strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        data = json.loads(cleaned)
        score = int(data.get("score"))
        reason = str(data.get("reason", "")).strip()

        # Validate score range 1-5
        if 1 <= score <= 5:
            return score, reason, True
        else:
            return None, f"Score out of range: {score}", False
    except Exception as e:
        logger.warning(f"Failed to parse judge JSON: {e} | Raw: {raw_text[:100]}")
        return None, f"Parse error: {raw_text[:120]}", False


async def score_replay(db: Session, replay: Replay) -> Score:
    """
    Scores a single replay record:
    1. Checks for exact match.
    2. If not exact match, calls LLM judge using Gemini.
    3. Saves and returns the Score record.
    """
    prompt = replay.request.prompt
    answer_a = replay.request.response or ""
    answer_b = replay.candidate_response or ""

    # Step 1: Exact match check
    if check_exact_match(answer_a, answer_b):
        score_record = Score(
            replay_id=replay.id,
            exact_match=True,
            judge_score=5,
            judge_reason="Exact match with Answer A (case-insensitive).",
            judge_parse_ok=True
        )
        db.add(score_record)
        db.commit()
        db.refresh(score_record)
        return score_record

    # Step 2: LLM Judge evaluation
    judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
        prompt=prompt,
        answer_a=answer_a,
        answer_b=answer_b
    )

    try:
        raw_judge_reply, _, _, _ = await call_gemini(
            prompt=judge_prompt,
            model_name=settings.JUDGE_MODEL,
            api_key=settings.GEMINI_API_KEY
        )
        score_val, reason_val, parse_ok = parse_judge_json(raw_judge_reply)
    except Exception as e:
        logger.error(f"Error calling judge model: {e}")
        score_val = None
        reason_val = f"Judge API error: {str(e)}"
        parse_ok = False

    score_record = Score(
        replay_id=replay.id,
        exact_match=False,
        judge_score=score_val,
        judge_reason=reason_val,
        judge_parse_ok=parse_ok
    )
    db.add(score_record)
    db.commit()
    db.refresh(score_record)
    return score_record


async def score_unscored_replays(db: Session) -> list[Score]:
    """Finds all replays that do not have a score yet and evaluates them."""
    # Find all replay IDs that already have a score
    scored_replay_ids = [s.replay_id for s in db.query(Score.replay_id).all()]
    
    # Query unscored replays
    unscored = (
        db.query(Replay)
        .filter(Replay.id.notin_(scored_replay_ids) if scored_replay_ids else True)
        .filter(Replay.status == "ok")
        .all()
    )

    results = []
    for replay in unscored:
        score_rec = await score_replay(db, replay)
        results.append(score_rec)

    return results
