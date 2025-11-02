"""Rate limiting middleware using token bucket algorithm."""

import time
import logging
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from ..utils.auth_utils import decode_token

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for rate limiting."""
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self._refill()
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def remaining(self) -> int:
        """Get remaining tokens."""
        self._refill()
        return int(self.tokens)
    
    def reset_time(self) -> float:
        """Get time until full refill in seconds."""
        self._refill()
        if self.tokens >= self.capacity:
            return 0.0
        tokens_needed = self.capacity - self.tokens
        return tokens_needed / self.refill_rate


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with three limits:
    - 60 requests per minute per token (general rate limit)
    - 10 sessions per minute per user
    - 5 games per session per minute
    """
    
    def __init__(self, app):
        super().__init__(app)
        
        # General rate limit: 60 requests/min per token
        self.general_buckets: Dict[str, TokenBucket] = {}
        
        # Session creation limit: 10 sessions/min per user
        self.session_buckets: Dict[str, TokenBucket] = {}
        
        # Game creation limit: 5 games/session/min
        self.game_buckets: Dict[str, TokenBucket] = {}
        
        # Cleanup old buckets periodically
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        
        # Import here to avoid circular dependency
        from ..config import settings
        
        # Skip rate limiting if disabled (e.g., in tests)
        if settings.disable_rate_limiting:
            return await call_next(request)
        
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/healthz", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization", "")
        token = None
        user_id = None
        
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_token(token)
                user_id = payload.get("user_id")
            except Exception:
                pass  # Invalid token, will be handled by auth middleware
        
        # If no token, use IP address as identifier
        identifier = token if token else self._get_client_ip(request)
        
        # Periodic cleanup of old buckets
        self._cleanup_old_buckets()
        
        # 1. Check general rate limit (60 req/min)
        if not self._check_general_limit(identifier):
            return self._rate_limit_response("General rate limit exceeded: 60 requests per minute")
        
        # 2. Check session creation limit (10 sessions/min per user)
        if request.method == "POST" and "/sessions" in request.url.path and "/games" not in request.url.path:
            if user_id and not self._check_session_limit(user_id):
                return self._rate_limit_response("Session creation rate limit exceeded: 10 sessions per minute")
        
        # 3. Check game creation limit (5 games/session/min)
        if request.method == "POST" and "/games" in request.url.path:
            session_id = self._extract_session_id(request.url.path)
            if session_id and not self._check_game_limit(session_id):
                return self._rate_limit_response("Game creation rate limit exceeded: 5 games per session per minute")
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        if identifier:
            remaining = self._get_remaining_tokens(identifier)
            reset_time = self._get_reset_time(identifier)
            
            response.headers["X-RateLimit-Limit"] = "60"
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + reset_time))
        
        return response
    
    def _check_general_limit(self, identifier: str) -> bool:
        """Check general rate limit (60 req/min)."""
        if identifier not in self.general_buckets:
            # 60 requests per minute = 1 request per second
            self.general_buckets[identifier] = TokenBucket(capacity=60, refill_rate=1.0)
        
        return self.general_buckets[identifier].consume(1)
    
    def _check_session_limit(self, user_id: str) -> bool:
        """Check session creation limit (10 sessions/min per user)."""
        key = f"session:{user_id}"
        if key not in self.session_buckets:
            # 10 sessions per minute = 1 session per 6 seconds
            self.session_buckets[key] = TokenBucket(capacity=10, refill_rate=10.0/60.0)
        
        return self.session_buckets[key].consume(1)
    
    def _check_game_limit(self, session_id: str) -> bool:
        """Check game creation limit (5 games/session/min)."""
        key = f"game:{session_id}"
        if key not in self.game_buckets:
            # 5 games per minute = 1 game per 12 seconds
            self.game_buckets[key] = TokenBucket(capacity=5, refill_rate=5.0/60.0)
        
        return self.game_buckets[key].consume(1)
    
    def _get_remaining_tokens(self, identifier: str) -> int:
        """Get remaining tokens for identifier."""
        if identifier in self.general_buckets:
            return self.general_buckets[identifier].remaining()
        return 60
    
    def _get_reset_time(self, identifier: str) -> float:
        """Get time until rate limit resets."""
        if identifier in self.general_buckets:
            return self.general_buckets[identifier].reset_time()
        return 0.0
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        # Check X-Forwarded-For header (proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Use direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def _extract_session_id(self, path: str) -> str:
        """Extract session ID from URL path."""
        # Match pattern: /api/v1/sessions/{session_id}/games
        parts = path.split("/")
        try:
            sessions_idx = parts.index("sessions")
            if sessions_idx + 1 < len(parts):
                return parts[sessions_idx + 1]
        except (ValueError, IndexError):
            pass
        return ""
    
    def _cleanup_old_buckets(self):
        """Remove buckets that haven't been used recently."""
        now = time.time()
        
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remove buckets with full tokens (unused for a while)
        self.general_buckets = {
            k: v for k, v in self.general_buckets.items()
            if v.remaining() < v.capacity
        }
        
        self.session_buckets = {
            k: v for k, v in self.session_buckets.items()
            if v.remaining() < v.capacity
        }
        
        self.game_buckets = {
            k: v for k, v in self.game_buckets.items()
            if v.remaining() < v.capacity
        }
        
        self.last_cleanup = now
        logger.debug(f"Cleaned up rate limiter buckets. Remaining: general={len(self.general_buckets)}, session={len(self.session_buckets)}, game={len(self.game_buckets)}")
    
    def _rate_limit_response(self, message: str) -> JSONResponse:
        """Return 429 rate limit response."""
        logger.warning(f"Rate limit exceeded: {message}")
        
        return JSONResponse(
            status_code=429,
            content={
                "detail": message,
                "error_code": "RATE_LIMIT_EXCEEDED"
            },
            headers={
                "Retry-After": "60"
            }
        )
