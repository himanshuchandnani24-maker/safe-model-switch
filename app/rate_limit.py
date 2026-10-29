"""
In-memory sliding window rate limiter.
Tracks request timestamps within a 60-second window per API key.
Returns 429 with Retry-After header when the limit is exceeded.
No Redis required (as specified in Section 2 & 8).
"""
import time
from typing import Dict, List
from fastapi import HTTPException
from app.models import ApiKey

# In-memory storage: api_key_id -> list of float timestamps
_rate_limit_records: Dict[int, List[float]] = {}


def check_rate_limit(api_key: ApiKey, window_seconds: float = 60.0):
    """
    Enforces sliding-window rate limiting per API key.
    Raises HTTPException 429 if the request count exceeds api_key.rate_limit_per_min.
    """
    now = time.time()
    cutoff = now - window_seconds
    key_id = api_key.id

    if key_id not in _rate_limit_records:
        _rate_limit_records[key_id] = []

    # Keep only timestamps within the last 60 seconds
    timestamps = [ts for ts in _rate_limit_records[key_id] if ts > cutoff]
    _rate_limit_records[key_id] = timestamps

    limit = api_key.rate_limit_per_min

    if len(timestamps) >= limit:
        # Calculate when the oldest request exits the window
        oldest_ts = timestamps[0]
        retry_after = max(1, int((oldest_ts + window_seconds) - now))
        
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({limit} requests/minute). Please retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)}
        )

    # Record current request timestamp
    _rate_limit_records[key_id].append(now)


def clear_rate_limits():
    """Helper used during tests to reset all rate limit counters."""
    _rate_limit_records.clear()
