import time
import redis
from fastapi import HTTPException, status
from .config import settings

# Initialize Redis client
try:
    r = redis.from_url(settings.redis_url, decode_responses=True)
except Exception:
    r = None

def check_rate_limit(user_id: str):
    """
    Sliding window rate limiter using Redis.
    Limits requests per user_id based on settings.rate_limit_per_minute.
    """
    if not r:
        # Fallback if Redis is unavailable (could also fail hard if production)
        return

    now = time.time()
    key = f"rl:{user_id}"
    
    # Use a pipeline for atomic operations
    pipe = r.pipeline()
    # Remove old requests (outside the 60s window)
    pipe.zremrangebyscore(key, 0, now - 60)
    # Get current request count in window
    pipe.zcard(key)
    # Add current request
    pipe.zadd(key, {str(now): now})
    # Set expiration on the key to cleanup
    pipe.expire(key, 60)
    
    _, current_count, _, _ = pipe.execute()
    
    if current_count >= settings.rate_limit_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {settings.rate_limit_per_minute} requests per minute.",
            headers={"Retry-After": "60"}
        )