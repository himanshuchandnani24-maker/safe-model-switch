"""
Report generation logic for Safe Model Switch.
Calculates cost savings %, quality retained %, latency comparisons, and final verdict.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.config import settings
from app.models import RequestLog, Replay, Score
from app.schemas import ReportResponse, ModelStats


def calculate_report_data(db: Session) -> Dict[str, Any]:
    """
    Computes comparative statistics between Model A and Model B:
    - Requests compared count
    - Model A avg cost, avg latency, avg score (5.0 reference)
    - Model B avg cost, avg latency, avg score
    - Cost savings %
    - Quality retained %
    - Uncertain count
    - Verdict string: 'Safe to switch', 'Review needed', or 'Not safe'
    """
    # Fetch all scores with their related replay and original request
    scores = db.query(Score).all()

    if not scores:
        return {
            "requests_compared": 0,
            "model_a": {"avg_cost_usd": 0.0, "avg_latency_ms": 0.0, "avg_score": 5.0},
            "model_b": {"avg_cost_usd": 0.0, "avg_latency_ms": 0.0, "avg_score": 0.0},
            "cost_saving_pct": 0.0,
            "quality_retained_pct": 0.0,
            "uncertain_count": 0,
            "verdict": "Review needed (No data)"
        }

    valid_judge_scores = []
    uncertain_count = 0

    costs_a = []
    latencies_a = []
    costs_b = []
    latencies_b = []

    for s in scores:
        replay = s.replay
        req = replay.request if replay else None

        if req:
            costs_a.append(req.est_cost_usd or 0.0)
            latencies_a.append(req.latency_ms or 0)

        if replay:
            costs_b.append(replay.est_cost_usd or 0.0)
            latencies_b.append(replay.latency_ms or 0)

        # Quality scoring
        if s.exact_match:
            valid_judge_scores.append(5)
        elif s.judge_score is not None and s.judge_parse_ok:
            valid_judge_scores.append(s.judge_score)
        else:
            uncertain_count += 1

    total_compared = len(scores)

    # Averages for Model A
    avg_cost_a = sum(costs_a) / len(costs_a) if costs_a else 0.0
    avg_lat_a = sum(latencies_a) / len(latencies_a) if latencies_a else 0.0

    # Averages for Model B
    avg_cost_b = sum(costs_b) / len(costs_b) if costs_b else 0.0
    avg_lat_b = sum(latencies_b) / len(latencies_b) if latencies_b else 0.0
    avg_score_b = sum(valid_judge_scores) / len(valid_judge_scores) if valid_judge_scores else 0.0

    # Quality retained % formula: (average score of B / 5) * 100
    quality_retained_pct = (avg_score_b / 5.0) * 100.0 if valid_judge_scores else 0.0

    # Cost savings %
    if avg_cost_a > 0:
        cost_saving_pct = ((avg_cost_a - avg_cost_b) / avg_cost_a) * 100.0
    else:
        cost_saving_pct = 0.0

    # Verdict thresholds (Section 8)
    if quality_retained_pct >= settings.VERDICT_SAFE_THRESHOLD:
        verdict = "Safe to switch"
    elif quality_retained_pct >= settings.VERDICT_REVIEW_THRESHOLD:
        verdict = "Review needed"
    else:
        verdict = "Not safe"

    return {
        "requests_compared": total_compared,
        "model_a": {
            "avg_cost_usd": round(avg_cost_a, 6),
            "avg_latency_ms": round(avg_lat_a, 1),
            "avg_score": 5.0
        },
        "model_b": {
            "avg_cost_usd": round(avg_cost_b, 6),
            "avg_latency_ms": round(avg_lat_b, 1),
            "avg_score": round(avg_score_b, 2)
        },
        "cost_saving_pct": round(cost_saving_pct, 1),
        "quality_retained_pct": round(quality_retained_pct, 1),
        "uncertain_count": uncertain_count,
        "verdict": verdict
    }
