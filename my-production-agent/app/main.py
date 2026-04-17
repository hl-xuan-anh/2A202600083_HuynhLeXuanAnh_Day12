import time
import json
import logging
import signal
import redis
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .config import settings
from .auth import verify_api_key
from .rate_limiter import check_rate_limit
from .cost_guard import check_budget, record_cost

# Mock LLM from the provided utils
# Assuming utils/mock_llm.py is accessible via sys.path or relative
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from app.utils.mock_llm import ask as llm_ask

# ─────────────────────────────────────────────────────────
# Logging — Structured JSON
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# Global State
# ─────────────────────────────────────────────────────────
START_TIME = time.time()
_is_ready = False
_redis_client = None

try:
    _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
except Exception as e:
    logger.error(json.dumps({"event": "redis_connection_failed", "error": str(e)}))

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
    }))
    # Simulate connectivity check
    if _redis_client:
        try:
            _redis_client.ping()
            _is_ready = True
            logger.info(json.dumps({"event": "ready", "redis": "connected"}))
        except Exception as e:
            logger.error(json.dumps({"event": "not_ready", "redis": "error", "error": str(e)}))
    
    yield
    
    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# App Initialize
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    
    logger.info(json.dumps({
        "event": "request",
        "method": request.method,
        "path": request.url.path,
        "status": response.status_code,
        "ms": duration,
    }))
    return response

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)

class AskResponse(BaseModel):
    question: str
    answer: str
    history_count: int
    model: str
    timestamp: str

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "uptime": round(time.time() - START_TIME, 2)}

@app.get("/ready")
def ready():
    if not _is_ready:
        raise HTTPException(status_code=503, detail="Service not ready")
    return {"status": "ready"}

@app.post("/ask", response_model=AskResponse)
async def ask(
    body: AskRequest,
    user_id: str = Depends(verify_api_key),
):
    # 1. Rate Limiting Check
    check_rate_limit(user_id)
    
    # 2. Budget Check
    check_budget(user_id)
    
    # 3. Get Conversation History from Redis
    history_key = f"hist:{user_id}"
    history = []
    if _redis_client:
        history = _redis_client.lrange(history_key, -10, -1) # Last 10 exchanges
    
    # 4. Call LLM (In development, this uses Mock LLM)
    # We could inject history here if the mock/real LLM supports it
    answer = llm_ask(body.question)
    
    # 5. Record Cost (Mock calculation: $0.002 per request)
    record_cost(user_id, 0.002)
    
    # 6. Save to Redis History
    if _redis_client:
        _redis_client.rpush(history_key, json.dumps({
            "q": body.question, 
            "a": answer, 
            "ts": datetime.now(timezone.utc).isoformat()
        }))
        _redis_client.ltrim(history_key, -50, -1) # Keep last 50 only
        _redis_client.expire(history_key, 3600 * 24) # Expire history after 24h
        
    return AskResponse(
        question=body.question,
        answer=answer,
        history_count=len(history),
        model=settings.llm_model,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

# ─────────────────────────────────────────────────────────
# Signal Handling for Graceful Shutdown
# ─────────────────────────────────────────────────────────
def handle_exit(sig, frame):
    global _is_ready
    _is_ready = False
    logger.info(json.dumps({"event": "signal_received", "signal": sig}))
    # In a real app, you'd allow current requests to finish
    time.sleep(1) 
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_exit)
signal.signal(signal.SIGINT, handle_exit)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)