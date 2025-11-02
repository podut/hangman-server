"""Idempotency middleware for handling Idempotency-Key header."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.background import BackgroundTask
import logging

logger = logging.getLogger(__name__)


class IdempotencyStore:
    """In-memory store for idempotency keys and responses.
    
    In production, this should be replaced with Redis or similar distributed cache.
    """
    
    def __init__(self, ttl_hours: int = 24):
        self._store: Dict[str, Dict[str, Any]] = {}
        self.ttl_hours = ttl_hours
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get stored response for idempotency key."""
        if key in self._store:
            entry = self._store[key]
            # Check if expired
            expires_at = datetime.fromisoformat(entry["expires_at"])
            if datetime.utcnow() < expires_at:
                return entry
            else:
                # Clean up expired entry
                del self._store[key]
        return None
    
    def set(self, key: str, status_code: int, body: bytes, headers: Dict[str, str]):
        """Store response for idempotency key."""
        expires_at = datetime.utcnow() + timedelta(hours=self.ttl_hours)
        self._store[key] = {
            "status_code": status_code,
            "body": body,
            "headers": headers,
            "expires_at": expires_at.isoformat()
        }
        logger.debug(f"Stored idempotency key: {key[:16]}... (expires: {expires_at})")
    
    def cleanup_expired(self):
        """Remove expired entries from store."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, entry in self._store.items()
            if datetime.fromisoformat(entry["expires_at"]) < now
        ]
        for key in expired_keys:
            del self._store[key]
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired idempotency keys")


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Middleware to handle Idempotency-Key header for safe request retries.
    
    According to the IETF draft, Idempotency-Key should be used for:
    - POST requests (non-idempotent by default)
    - PATCH requests (may not be idempotent)
    - DELETE requests (should be idempotent, but client may retry)
    
    GET and HEAD requests are naturally idempotent and don't need this.
    """
    
    def __init__(self, app, ttl_hours: int = 24):
        super().__init__(app)
        self.store = IdempotencyStore(ttl_hours=ttl_hours)
        self.idempotent_methods = {"POST", "PATCH", "DELETE"}
    
    async def dispatch(self, request: Request, call_next):
        """Process request with idempotency handling."""
        
        # Skip SSE streaming endpoints
        if request.url.path == "/api/v1/events/stream":
            return await call_next(request)
        
        # Only process methods that benefit from idempotency
        if request.method not in self.idempotent_methods:
            return await call_next(request)
        
        # Get idempotency key from header
        idempotency_key = request.headers.get("Idempotency-Key")
        
        # If no key provided, process request normally
        if not idempotency_key:
            return await call_next(request)
        
        # Validate idempotency key format (should be a reasonable string)
        if len(idempotency_key) < 1 or len(idempotency_key) > 255:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "INVALID_IDEMPOTENCY_KEY",
                        "message": "Idempotency-Key must be between 1 and 255 characters"
                    }
                }
            )
        
        # Create composite key: method + path + idempotency_key + user
        # This ensures keys are scoped to specific operations and users
        user_id = "anonymous"
        if hasattr(request.state, "user"):
            user_id = request.state.user.get("user_id", "anonymous")
        
        # Read request body for fingerprinting
        body = await request.body()
        body_hash = hashlib.sha256(body).hexdigest()[:16]
        
        composite_key = f"{request.method}:{request.url.path}:{idempotency_key}:{user_id}:{body_hash}"
        
        # Check if we have a stored response
        stored = self.store.get(composite_key)
        if stored:
            logger.info(f"Returning stored response for idempotency key: {idempotency_key[:16]}...")
            # Return stored response
            return Response(
                content=stored["body"],
                status_code=stored["status_code"],
                headers={
                    **stored["headers"],
                    "X-Idempotent-Replay": "true"
                }
            )
        
        # Process request normally
        response = await call_next(request)
        
        # For successful responses (2xx, 3xx), store them for idempotency
        if 200 <= response.status_code < 400:
            try:
                # Try to capture response body
                response_body = b""
                
                # For responses with body attribute (JSONResponse, etc)
                if hasattr(response, 'body'):
                    response_body = response.body
                # For streaming responses
                elif hasattr(response, 'body_iterator'):
                    chunks = []
                    async for chunk in response.body_iterator:
                        if isinstance(chunk, bytes):
                            chunks.append(chunk)
                        elif isinstance(chunk, str):
                            chunks.append(chunk.encode('utf-8'))
                    response_body = b"".join(chunks)
                
                if response_body:
                    # Store the response
                    response_headers = dict(response.headers)
                    response_headers.pop("content-length", None)  # Will be recalculated
                    
                    self.store.set(
                        composite_key,
                        response.status_code,
                        response_body,
                        response_headers
                    )
                    
                    # Return a new response with the captured body
                    return Response(
                        content=response_body,
                        status_code=response.status_code,
                        headers={
                            **response_headers,
                            "X-Idempotent-Stored": "true"
                        },
                        media_type=getattr(response, 'media_type', None)
                    )
            except Exception as e:
                # If we can't capture the body, log and return original response
                logger.warning(f"Could not capture response body for idempotency: {e}")
                return response
        
        # Don't store error responses (4xx, 5xx) or if capture failed
        return response
