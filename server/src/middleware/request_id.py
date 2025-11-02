"""Request ID middleware for tracking requests."""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from typing import Callable


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add a unique request ID to each request.
    
    The request ID can be:
    1. Provided by the client via X-Request-ID header
    2. Auto-generated if not provided
    
    The request ID is:
    - Stored in request.state.request_id
    - Added to the response X-Request-ID header
    - Available for logging throughout the request lifecycle
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and add request ID."""
        # Check if client provided a request ID
        request_id = request.headers.get("X-Request-ID")
        
        # Generate a new ID if not provided
        if not request_id:
            request_id = f"req_{uuid.uuid4().hex[:16]}"
        
        # Store request ID in request state (accessible throughout the request)
        request.state.request_id = request_id
        
        # Process the request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
