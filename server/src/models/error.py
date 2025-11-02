"""Error response models and error codes."""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ErrorCode(str, Enum):
    """Standardized error codes for the API."""
    
    # Authentication & Authorization (1xxx)
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    USER_EXISTS = "USER_EXISTS"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    
    # Session Management (2xxx)
    SESSION_NOT_FOUND = "SESSION_2001"
    SESSION_ACCESS_DENIED = "SESSION_2002"
    SESSION_ALREADY_FINISHED = "SESSION_2003"
    MAX_SESSIONS_EXCEEDED = "SESSION_2004"
    SESSION_LIMIT_REACHED = "SESSION_2005"
    
    # Game Management (3xxx)
    GAME_NOT_FOUND = "GAME_3001"
    GAME_ACCESS_DENIED = "GAME_3002"
    GAME_ALREADY_FINISHED = "GAME_3003"
    INVALID_GUESS = "GAME_3004"
    GAME_LIMIT_REACHED = "GAME_3005"
    NO_WORDS_AVAILABLE = "GAME_3006"
    
    # Dictionary Management (4xxx)
    DICTIONARY_NOT_FOUND = "DICT_4001"
    DICTIONARY_INVALID = "DICT_4002"
    DICTIONARY_TOO_FEW_WORDS = "DICT_4003"
    DICTIONARY_ALREADY_EXISTS = "DICT_4004"
    
    # Validation Errors (5xxx)
    VALIDATION_ERROR = "VAL_5001"
    INVALID_INPUT = "VAL_5002"
    MISSING_FIELD = "VAL_5003"
    INVALID_FORMAT = "VAL_5004"
    
    # Server Errors (9xxx)
    INTERNAL_ERROR = "SERVER_9001"
    SERVICE_UNAVAILABLE = "SERVER_9002"
    NOT_IMPLEMENTED = "SERVER_9003"


class ErrorResponse(BaseModel):
    """Standardized error response format."""
    
    error_code: str  # Error code from ErrorCode enum
    message: str  # Human-readable error message
    detail: Optional[str] = None  # Additional detail about the error
    request_id: Optional[str] = None  # Request tracking ID
    timestamp: str  # ISO 8601 timestamp
    path: Optional[str] = None  # Request path that caused the error
    
    @classmethod
    def create(
        cls,
        error_code: ErrorCode,
        message: str,
        detail: Optional[str] = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None
    ) -> "ErrorResponse":
        """Factory method to create error responses."""
        return cls(
            error_code=error_code.value,
            message=message,
            detail=detail,
            request_id=request_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            path=path
        )
    
    class Config:
        json_schema_extra = {
            "example": {
                "error_code": "GAME_3003",
                "message": "Game already finished",
                "detail": "Cannot make guesses on a completed game",
                "request_id": "req_abc123",
                "timestamp": "2025-11-02T12:34:56.789Z",
                "path": "/api/v1/sessions/s_1/games/g_1/guess"
            }
        }
