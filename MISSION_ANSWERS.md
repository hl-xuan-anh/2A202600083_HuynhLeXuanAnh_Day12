# Day 12 Lab - Mission Answers

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. **Hardcoded Secrets**: API keys (e.g., `OPENAI_API_KEY`) and database URLs are storage directly in the source code, posing a major security risk if pushed to version control.
2. **Missing Config Management**: Application settings like `DEBUG`, `MAX_TOKENS`, and environment-specific parameters are hardcoded instead of being loaded from environment variables or config files.
3. **Improper Logging**: Using `print()` instead of a structured logging library. Additionally, logging sensitive information like API keys to standard output.
4. **No Health Checks**: There are no specialized endpoints (`/health`, `/ready`) for monitoring tools or orchestrators to verify the application's status.
5. **Fixed Port and Bindings**: The application is hardcoded to listen on `localhost` and a fixed port (`8000`), which prevents it from running correctly in containerized or cloud environments that inject their own `PORT` variable.
6. **Debug Mode Enabled**: `reload=True` is active, which should only be used in development as it can degrade performance and expose internal details in production.

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config  | Hardcoded in `app.py` | Loaded via Pydantic `BaseSettings`/`.env` | Enables security (no secrets in code) and environment-specific portability. |
| Health check | None | `/health` (Liveness) and `/ready` (Readiness) | Allows orchestrators like Docker/K8s to monitor status and restart failing instances. |
| Logging | `print()` (Non-structured) | Structured JSON Logging | Facilitates automated log parsing and monitoring in distributed production systems. |
| Shutdown | Abrupt | Graceful (handles `SIGTERM`) | Ensures current requests complete and resources are safely released before exit. |

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. **Base image**: `python:3.11` (Full distribution, approximately 1GB).
2. **Working directory**: `/app` (Set via `WORKDIR /app`).
3. **Copying requirements first**: This utilizes Docker's layer caching. If the dependencies haven't changed, Docker reuses the cached layer containing installed packages, significantly speeding up subsequent builds.
4. **CMD vs ENTRYPOINT**: `CMD` sets a default command that can be overridden during `docker run`. `ENTRYPOINT` defines the executable to be run, making the container feel like a standalone binary.

### Exercise 2.3: Image size comparison
- **Develop**: ~1.02 GB (using `python:3.11` full image)
- **Production**: ~150 MB (using `python:3.11-slim` + multi-stage build)
- **Difference**: ~85% reduction

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- **URL**: [https://railway-service-production-86a1.up.railway.app](https://railway-service-production-86a1.up.railway.app)
- **Public URL Test**: Successfully verified health and agent endpoints via Railway public domain.

## Part 4: API Security

### Exercise 4.1-4.3: Test results
The implementation supports:
- **API Key Auth**: Requests require an `X-API-Key` header; missing or invalid keys return 401 Unauthorized.
- **JWT Auth**: Advanced version uses Bearer tokens for temporary, secure access.
- **Rate Limiting**: Implemented a sliding window limit (e.g., 10 req/min) to prevent abuse and manage costs.

### Exercise 4.4: Cost guard implementation
The implementation uses a `CostGuard` class that:
- Tracks total token usage (input and output) per user.
- Calculates costs in USD based on model-specific pricing (e.g., $0.15/1M tokens).
- Blocks requests (HTTP 402) if the daily budget is exceeded.
- Implements a global daily budget cap to prevent catastrophic billing errors.

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
1. **Health Checks**: Implemented `/health` (Liveness) to signal process status and `/ready` (Readiness) to confirm backend service connectivity (Redis/DB).
2. **Stateless Design**: Refactored the agent to store conversation history in **Redis** instead of local memory. This ensures that any instance can serve any request as long as they all point to the same Redis store.
3. **Load Balancing**: Tested using Nginx to distribute traffic across 3 agent instances.
4. **Graceful Shutdown**: Added handlers for `SIGTERM` to allow the agent to finish in-flight requests before exiting during a deploy or scale-down event.