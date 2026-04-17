import time
import redis
from fastapi import HTTPException, status
from .config import settings

try:
    r = redis.from_url(settings.redis_url, decode_responses=True)
except Exception:
    r = None

def check_budget(user_id: str):
    """
    Checks if the user has exceeded their daily budget stored in Redis.
    In a real app, this would estimate tokens and decrement budget.
    For this lab, we use a simple counter per user per day.
    """
    if not r:
        return

    today = time.strftime("%Y-%m-%d")
    key = f"cost:{user_id}:{today}"
    
    current_cost = float(r.get(key) or 0)
    
    if current_cost >= settings.daily_budget_usd:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Daily budget of ${settings.daily_budget_usd} exceeded. Try again tomorrow."
        )

def record_cost(user_id: str, cost: float):
    """
    Increments the user's daily cost in Redis.
    """
    if not r:
        return
        
    today = time.strftime("%Y-%m-%d")
    key = f"cost:{user_id}:{today}"
    
    r.incrbyfloat(key, cost)
    r.expire(key, 86400 * 2)  # Expire after 2 days