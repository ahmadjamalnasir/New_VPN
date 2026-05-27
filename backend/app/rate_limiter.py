import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RateLimitStore:
    def __init__(self):
        self.requests = defaultdict(list)

    def is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        self.requests[key] = [
            t for t in self.requests[key] if t > now - window_seconds
        ]
        if len(self.requests[key]) >= max_requests:
            return True
        self.requests[key].append(now)
        return False


rate_store = RateLimitStore()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, per_minute: int = 30, per_hour: int = 500):
        super().__init__(app)
        self.per_minute = per_minute
        self.per_hour = per_hour

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"

        if rate_store.is_rate_limited(client_ip, self.per_minute, 60):
            logger.warning(f"Rate limit exceeded (per-minute) for {client_ip}")
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in 60 seconds.")

        if rate_store.is_rate_limited(client_ip, self.per_hour, 3600):
            logger.warning(f"Rate limit exceeded (per-hour) for {client_ip}")
            raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again in an hour.")

        response = await call_next(request)
        response.headers["X-RateLimit-Limit-Minute"] = str(self.per_minute)
        response.headers["X-RateLimit-Limit-Hour"] = str(self.per_hour)
        return response
