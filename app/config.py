"""
Configuration and settings for Safe Model Switch.
Loads environment variables and holds pricing tables and verdict thresholds.
"""
import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()


class Settings:
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Models
    MODEL_A: str = os.getenv("MODEL_A", "gemini-1.5-flash")
    MODEL_B: str = os.getenv("MODEL_B", "llama-3.1-8b-instant")
    JUDGE_MODEL: str = os.getenv("JUDGE_MODEL", "gemini-1.5-pro")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./gateway.db")

    # Rate limiting & Replay
    DEFAULT_RATE_LIMIT_PER_MIN: int = int(os.getenv("DEFAULT_RATE_LIMIT_PER_MIN", "10"))
    REPLAY_DELAY_SECONDS: int = int(os.getenv("REPLAY_DELAY_SECONDS", "2"))

    # Published paid price per 1,000,000 tokens (USD)
    # Used to calculate estimated cost (Section 8)
    PRICING = {
        "gemini-1.5-flash": {"price_in": 0.075, "price_out": 0.30},
        "gemini-1.5-pro": {"price_in": 1.25, "price_out": 5.00},
        "llama-3.1-8b-instant": {"price_in": 0.05, "price_out": 0.08},
        "llama-3.3-70b-versatile": {"price_in": 0.59, "price_out": 0.79},
    }

    # Verdict thresholds (Section 8)
    VERDICT_SAFE_THRESHOLD: float = 90.0
    VERDICT_REVIEW_THRESHOLD: float = 75.0


settings = Settings()


def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate estimated cost in USD based on token counts and model pricing.
    Formula: (input_tokens / 1_000_000) * price_in + (output_tokens / 1_000_000) * price_out
    """
    pricing = settings.PRICING.get(
        model_name,
        {"price_in": 0.10, "price_out": 0.30}  # sensible default fallback
    )
    cost = (input_tokens / 1_000_000) * pricing["price_in"] + (output_tokens / 1_000_000) * pricing["price_out"]
    return round(cost, 7)
