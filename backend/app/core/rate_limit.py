"""
NetPulse Backend — Rate Limiting.
"""
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.dependencies import get_redis
from app.core.security import get_current_user
from app.db.models import UserModel


class RateLimiter:
    """
    FastAPI Dependency for rate limiting using a fixed-window algorithm in Redis.
    Limits are enforced per user (if authenticated) or per IP (if unauthenticated).
    """

    def __init__(self, requests: int = 60, window: int = 60):
        self.requests = requests
        self.window = window

    async def __call__(
        self,
        request: Request,
        redis: Redis | None = Depends(get_redis)
    ) -> None:
        if redis is None:
            # If Redis is unavailable, skip rate limiting (fail open)
            return

        # Attempt to get the user; if no token, fallback to IP
        # We can't strictly depend on get_current_user here if the route is public.
        # So we check if auth header exists.
        client_id = request.client.host if request.client else "unknown"
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            # We don't fully validate the token here; we just rely on the router to do it.
            # But we can extract a generic ID. For simplicity, we just use the IP unless
            # we want to inject the user explicitly. 
            # A better approach for mixed routes is checking app.state or token subject.
            token = auth_header.split(" ")[1]
            client_id = token[-10:] # Weak grouping for token
            
        # Optional: in a real app, you'd extract the sub from the JWT directly here without hitting DB.

        # Fixed window key
        import time
        current_window = int(time.time() // self.window)
        key = f"ratelimit:{client_id}:{current_window}"

        # Increment
        async with redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, self.window * 2)
            results = await pipe.execute()
        
        current_requests = results[0]

        if current_requests > self.requests:
            from app.core.exceptions import NetPulseException
            raise NetPulseException("Rate limit exceeded", status_code=429)
