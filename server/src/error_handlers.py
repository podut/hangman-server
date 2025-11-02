"""Exception handlers for FastAPI application."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Union
import logging
import traceback

from .exceptions import HangmanException
from .models.error import ErrorResponse, ErrorCode

logger = logging.getLogger(__name__)


async def hangman_exception_handler(request: Request, exc: HangmanException) -> JSONResponse:
    """Handle custom Hangman exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    error_response = ErrorResponse.create(
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
        request_id=request_id,
        path=request.url.path
    )
    
    # Log the error
    logger.warning(
        f"HangmanException: {exc.error_code.value} - {exc.message}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "error_code": exc.error_code.value,
            "status_code": exc.status_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = getattr(request.state, "request_id", None)
    
    # Format validation errors
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(f"{field}: {error['msg']}")
    
    error_response = ErrorResponse.create(
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Validation error",
        detail="; ".join(errors),
        request_id=request_id,
        path=request.url.path
    )
    
    logger.warning(
        f"Validation error: {errors}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "errors": errors
        }
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump()
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    # Map HTTP status codes to error codes
    error_code_map = {
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.SESSION_NOT_FOUND,  # Generic not found
        500: ErrorCode.INTERNAL_ERROR,
    }
    
    error_code = error_code_map.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    
    error_response = ErrorResponse.create(
        error_code=error_code,
        message=exc.detail or "HTTP error",
        detail=None,
        request_id=request_id,
        path=request.url.path
    )
    
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "status_code": exc.status_code
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = getattr(request.state, "request_id", None)
    
    # Log the full traceback for debugging
    logger.error(
        f"Unhandled exception: {type(exc).__name__}: {str(exc)}",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "traceback": traceback.format_exc()
        }
    )
    
    error_response = ErrorResponse.create(
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error",
        detail="An unexpected error occurred" if not logger.isEnabledFor(logging.DEBUG) else str(exc),
        request_id=request_id,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump()
    )


def register_exception_handlers(app) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(HangmanException, hangman_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info("Exception handlers registered")
