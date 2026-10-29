"""
Pydantic schemas for request validation and response formatting.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# Schemas for /chat
class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Prompt to send to Model A")


class ChatResponse(BaseModel):
    answer: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    est_cost_usd: float


# Schemas for /logs
class RequestLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    prompt: str
    response: Optional[str] = None
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    est_cost_usd: float
    status: str
    created_at: datetime


# Schemas for /replay
class ReplayRequest(BaseModel):
    n: int = Field(default=20, ge=1, le=100, description="Number of recent prompts to replay")


class ReplayItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    candidate_model: str
    candidate_response: Optional[str] = None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    est_cost_usd: float
    status: str
    created_at: datetime


# Schemas for /score
class ScoreItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    replay_id: int
    exact_match: bool
    judge_score: Optional[int] = None
    judge_reason: Optional[str] = None
    judge_parse_ok: bool
    created_at: datetime


# Schemas for /report
class ModelStats(BaseModel):
    avg_cost_usd: float
    avg_latency_ms: float
    avg_score: Optional[float] = None


class ReportResponse(BaseModel):
    requests_compared: int
    model_a: ModelStats
    model_b: ModelStats
    cost_saving_pct: float
    quality_retained_pct: float
    uncertain_count: int
    verdict: str
