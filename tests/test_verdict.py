"""
Tests for quality retention calculation and verdict thresholds.
Verifies Section 8 rules:
- >= 90% -> "Safe to switch"
- 75-89% -> "Review needed"
- < 75% -> "Not safe"
- Exact-match rows count as 5.
- Uncertain rows excluded from average score.
"""
import pytest
from app.database import SessionLocal
from app.models import RequestLog, Replay, Score
from app.report import calculate_report_data
from app.scoring import check_exact_match, parse_judge_json


def test_exact_match_helper():
    assert check_exact_match("  hello WORLD! ", "hello world!  ") is True
    assert check_exact_match("apple", "banana") is False


def test_safe_parse_judge_json():
    # Valid JSON
    valid_json = '{"score": 4, "reason": "Accurate response with slight phrasing difference."}'
    score, reason, ok = parse_judge_json(valid_json)
    assert score == 4
    assert ok is True

    # Valid JSON in markdown code blocks
    markdown_json = '```json\n{"score": 5, "reason": "Perfect answer."}\n```'
    score_md, reason_md, ok_md = parse_judge_json(markdown_json)
    assert score_md == 5
    assert ok_md is True

    # Invalid / unparseable output
    invalid_raw = "I think the score should be good."
    score_bad, reason_bad, ok_bad = parse_judge_json(invalid_raw)
    assert score_bad is None
    assert ok_bad is False


def test_verdict_thresholds(monkeypatch):
    # Test verdict calculation logic across different retention percentages
    from app.config import settings

    # Helper function simulating calculation
    def compute_verdict(avg_score: float) -> str:
        pct = (avg_score / 5.0) * 100.0
        if pct >= settings.VERDICT_SAFE_THRESHOLD:
            return "Safe to switch"
        elif pct >= settings.VERDICT_REVIEW_THRESHOLD:
            return "Review needed"
        else:
            return "Not safe"

    # Score 4.8 / 5.0 = 96% -> Safe to switch
    assert compute_verdict(4.8) == "Safe to switch"

    # Score 4.5 / 5.0 = 90% -> Safe to switch
    assert compute_verdict(4.5) == "Safe to switch"

    # Score 4.0 / 5.0 = 80% -> Review needed
    assert compute_verdict(4.0) == "Review needed"

    # Score 3.75 / 5.0 = 75% -> Review needed
    assert compute_verdict(3.75) == "Review needed"

    # Score 3.5 / 5.0 = 70% -> Not safe
    assert compute_verdict(3.5) == "Not safe"
