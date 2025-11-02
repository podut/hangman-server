"""Idempotency decorator for endpoint-level idempotency."""

import hashlib
import json
from functools import wraps
from typing import Any, Callable, Optional
from fastapi import Request, Response, HTTPException
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# In-memory store for idempotency keys (in production, use Redis)
_idempotency_store: dict[str, tuple[Any, datetime]] = {}


def _cleanup_expired_keys(ttl_hours: int = 24):
    """Clean up expired idempotency keys."""
    expiry_time = datetime.utcnow() - timedelta(hours=ttl_hours)
    expired_keys = [
        key for key, (_, timestamp) in _idempotency_store.items()
        if timestamp < expiry_time
    ]
    for key in expired_keys:
        del _idempotency_store[key]
    if expired_keys:
        logger.debug(f"Cleaned up {len(expired_keys)} expired idempotency keys")


def idempotent(
    ttl_hours: int = 24,
    key_header: str = "Idempotency-Key",
    include_body: bool = True
):
    """
    Decorator for endpoint-level idempotency.
    
    Usage:
    ```python
    @app.post("/api/v1/sessions")
    @idempotent(ttl_hours=24, key_header="Idempotency-Key")
    async def create_session(req: CreateSessionRequest, request: Request):
        # Your endpoint logic
        ...
    ```
    
    Args:
        ttl_hours: Time-to-live for idempotency keys in hours (default: 24)
        key_header: Header name for idempotency key (default: "Idempotency-Key")
        include_body: Include request body in key generation (default: True)
    
    Behavior:
        - If Idempotency-Key header is present:
          - First request: executes normally, stores response
          - Duplicate request (same key): returns stored response (replays)
        - If no Idempotency-Key header: executes normally (no idempotency)
    
    Note:
        Uses in-memory store for simplicity. For production, replace with Redis:
        ```python
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0)
        redis_client.setex(idem_key, ttl_hours * 3600, json.dumps(result))
        ```
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract Request object from kwargs
            request: Optional[Request] = kwargs.get('request')
            if not request:
                # Try to find Request in args
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            
            if not request:
                # No request object found, execute without idempotency
                logger.warning(f"Idempotent decorator: Request object not found in {func.__name__}")
                return await func(*args, **kwargs)
            
            # Check for idempotency key in headers
            idempotency_key = request.headers.get(key_header)
            
            if not idempotency_key:
                # No idempotency key provided, execute normally
                return await func(*args, **kwargs)
            
            # Generate composite key (user + idempotency_key + optional body hash)
            user_id = getattr(request.state, 'user_id', 'anonymous')
            
            if include_body:
                try:
                    body = await request.body()
                    body_hash = hashlib.sha256(body).hexdigest()[:16]
                    composite_key = f"{user_id}:{idempotency_key}:{body_hash}"
                except Exception as e:
                    logger.warning(f"Failed to read request body for idempotency: {e}")
                    composite_key = f"{user_id}:{idempotency_key}"
            else:
                composite_key = f"{user_id}:{idempotency_key}"
            
            # Clean up expired keys periodically
            if len(_idempotency_store) > 100:  # Cleanup every 100 requests
                _cleanup_expired_keys(ttl_hours)
            
            # Check if this request was already processed
            if composite_key in _idempotency_store:
                cached_result, timestamp = _idempotency_store[composite_key]
                
                # Check if not expired
                if datetime.utcnow() - timestamp < timedelta(hours=ttl_hours):
                    logger.info(f"Idempotency replay: key={idempotency_key}, func={func.__name__}")
                    return cached_result
                else:
                    # Expired, remove from store
                    del _idempotency_store[composite_key]
            
            # Execute the endpoint
            result = await func(*args, **kwargs)
            
            # Store the result
            _idempotency_store[composite_key] = (result, datetime.utcnow())
            logger.debug(f"Idempotency stored: key={idempotency_key}, func={func.__name__}")
            
            return result
        
        return wrapper
    return decorator


def clear_idempotency_store():
    """Clear all idempotency keys (useful for testing)."""
    global _idempotency_store
    count = len(_idempotency_store)
    _idempotency_store.clear()
    logger.info(f"Cleared {count} idempotency keys from store")


def get_idempotency_stats() -> dict[str, Any]:
    """Get idempotency store statistics."""
    return {
        "total_keys": len(_idempotency_store),
        "oldest_key_age_seconds": (
            min(
                (datetime.utcnow() - timestamp).total_seconds()
                for _, timestamp in _idempotency_store.values()
            ) if _idempotency_store else 0
        ),
        "newest_key_age_seconds": (
            max(
                (datetime.utcnow() - timestamp).total_seconds()
                for _, timestamp in _idempotency_store.values()
            ) if _idempotency_store else 0
        )
    }
