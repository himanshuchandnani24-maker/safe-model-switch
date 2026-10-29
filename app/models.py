"""
Database models (tables) for Safe Model Switch.
Follows Section 6 of the project guide:
- api_keys
- requests
- replays
- scores
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    rate_limit_per_min = Column(Integer, default=10, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to requests
    requests = relationship("RequestLog", back_populates="api_key")


class RequestLog(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"), nullable=True)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    model = Column(String(100), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    est_cost_usd = Column(Float, default=0.0)
    status = Column(String(20), default="ok")  # "ok" or "error"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    api_key = relationship("ApiKey", back_populates="requests")
    replays = relationship("Replay", back_populates="request")


class Replay(Base):
    __tablename__ = "replays"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("requests.id"), nullable=False)
    candidate_model = Column(String(100), nullable=False)
    candidate_response = Column(Text, nullable=True)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    est_cost_usd = Column(Float, default=0.0)
    status = Column(String(20), default="ok")  # "ok" or "error"
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    request = relationship("RequestLog", back_populates="replays")
    scores = relationship("Score", back_populates="replay")


class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    replay_id = Column(Integer, ForeignKey("replays.id"), nullable=False)
    exact_match = Column(Boolean, default=False)
    judge_score = Column(Integer, nullable=True)  # 1 to 5, or None if parse failed
    judge_reason = Column(Text, nullable=True)
    judge_parse_ok = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    replay = relationship("Replay", back_populates="scores")
