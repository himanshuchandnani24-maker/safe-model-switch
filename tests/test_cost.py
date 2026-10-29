"""
Tests for token cost estimation logic.
Verifies calculations based on provider pricing tables (Section 8).
"""
import pytest
from app.config import calculate_cost, settings


def test_gemini_cost_calculation():
    # Model: gemini-1.5-flash (in: 0.075 / 1M, out: 0.30 / 1M)
    input_tokens = 1_000_000
    output_tokens = 1_000_000
    cost = calculate_cost("gemini-1.5-flash", input_tokens, output_tokens)
    assert cost == pytest.approx(0.375, rel=1e-3)


def test_llama_cost_calculation():
    # Model: llama-3.1-8b-instant (in: 0.05 / 1M, out: 0.08 / 1M)
    input_tokens = 500_000
    output_tokens = 250_000
    # Expected: (0.5 * 0.05) + (0.25 * 0.08) = 0.025 + 0.02 = 0.045
    cost = calculate_cost("llama-3.1-8b-instant", input_tokens, output_tokens)
    assert cost == pytest.approx(0.045, rel=1e-3)


def test_zero_tokens_cost_zero():
    cost = calculate_cost("gemini-1.5-flash", 0, 0)
    assert cost == 0.0
