"""Custom exceptions with error codes."""

from typing import Optional
from .models.error import ErrorCode


class HangmanException(Exception):
    """Base exception for all Hangman API errors."""
    
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        detail: Optional[str] = None,
        status_code: int = 400
    ):
        self.error_code = error_code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)


# Authentication & Authorization Exceptions

class AuthenticationException(HangmanException):
    """Base class for authentication errors."""
    
    def __init__(self, error_code: ErrorCode, message: str, detail: Optional[str] = None):
        super().__init__(error_code, message, detail, status_code=401)


class InvalidCredentialsException(AuthenticationException):
    """Raised when login credentials are invalid."""
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            ErrorCode.INVALID_CREDENTIALS,
            "Invalid username or password",
            detail
        )


class TokenExpiredException(AuthenticationException):
    """Raised when JWT token has expired."""
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            ErrorCode.TOKEN_EXPIRED,
            "Authentication token has expired",
            detail
        )


class TokenInvalidException(AuthenticationException):
    """Raised when JWT token is invalid."""
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            ErrorCode.TOKEN_INVALID,
            "Invalid authentication token",
            detail
        )


class UnauthorizedException(AuthenticationException):
    """Raised when user is not authenticated."""
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            ErrorCode.UNAUTHORIZED,
            "Authentication required",
            detail
        )


class ForbiddenException(HangmanException):
    """Raised when user lacks required permissions."""
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            ErrorCode.FORBIDDEN,
            "Access forbidden",
            detail,
            status_code=403
        )


class UserAlreadyExistsException(HangmanException):
    """Raised when attempting to register duplicate username."""
    
    def __init__(self, username: str):
        super().__init__(
            ErrorCode.USER_ALREADY_EXISTS,
            f"User '{username}' already exists",
            "Please choose a different username",
            status_code=409
        )


class UserNotFoundException(HangmanException):
    """Raised when user is not found."""
    
    def __init__(self, user_id: str):
        super().__init__(
            ErrorCode.USER_NOT_FOUND,
            f"User not found",
            f"User ID: {user_id}",
            status_code=404
        )


# Session Exceptions

class SessionNotFoundException(HangmanException):
    """Raised when session is not found."""
    
    def __init__(self, session_id: str):
        super().__init__(
            ErrorCode.SESSION_NOT_FOUND,
            "Session not found",
            f"Session ID: {session_id}",
            status_code=404
        )


class SessionAccessDeniedException(ForbiddenException):
    """Raised when user tries to access another user's session."""
    
    def __init__(self, session_id: str):
        super().__init__(f"Access denied to session {session_id}")
        self.error_code = ErrorCode.SESSION_ACCESS_DENIED


class SessionAlreadyFinishedException(HangmanException):
    """Raised when trying to modify a finished session."""
    
    def __init__(self, session_id: str):
        super().__init__(
            ErrorCode.SESSION_ALREADY_FINISHED,
            "Session already finished",
            f"Cannot modify finished session {session_id}",
            status_code=409
        )


class MaxSessionsExceededException(HangmanException):
    """Raised when user exceeds maximum active sessions."""
    
    def __init__(self, max_sessions: int):
        super().__init__(
            ErrorCode.MAX_SESSIONS_EXCEEDED,
            "Maximum active sessions exceeded",
            f"You can have at most {max_sessions} active sessions",
            status_code=409
        )


class SessionLimitReachedException(HangmanException):
    """Raised when session game limit is reached."""
    
    def __init__(self, num_games: int):
        super().__init__(
            ErrorCode.SESSION_LIMIT_REACHED,
            "Session game limit reached",
            f"This session is limited to {num_games} games",
            status_code=409
        )


# Game Exceptions

class GameNotFoundException(HangmanException):
    """Raised when game is not found."""
    
    def __init__(self, game_id: str):
        super().__init__(
            ErrorCode.GAME_NOT_FOUND,
            "Game not found",
            f"Game ID: {game_id}",
            status_code=404
        )


class GameAccessDeniedException(ForbiddenException):
    """Raised when user tries to access another user's game."""
    
    def __init__(self, game_id: str):
        super().__init__(f"Access denied to game {game_id}")
        self.error_code = ErrorCode.GAME_ACCESS_DENIED


class GameAlreadyFinishedException(HangmanException):
    """Raised when trying to play a finished game."""
    
    def __init__(self, game_id: str, status: str):
        super().__init__(
            ErrorCode.GAME_ALREADY_FINISHED,
            "Game already finished",
            f"Game {game_id} has status: {status}",
            status_code=409
        )


class InvalidGuessException(HangmanException):
    """Raised when guess is invalid."""
    
    def __init__(self, reason: str):
        super().__init__(
            ErrorCode.INVALID_GUESS,
            f"Invalid guess: {reason}",
            reason,
            status_code=400
        )


class GameLimitReachedException(HangmanException):
    """Raised when session game limit is reached."""
    
    def __init__(self, limit: int):
        super().__init__(
            ErrorCode.GAME_LIMIT_REACHED,
            "Game limit reached",
            f"Session is limited to {limit} games",
            status_code=409
        )


class NoWordsAvailableException(HangmanException):
    """Raised when no unique words are available."""
    
    def __init__(self):
        super().__init__(
            ErrorCode.NO_WORDS_AVAILABLE,
            "No words available",
            "All words in dictionary have been used in this session",
            status_code=409
        )


# Dictionary Exceptions

class DictionaryNotFoundException(HangmanException):
    """Raised when dictionary is not found."""
    
    def __init__(self, dictionary_id: str):
        super().__init__(
            ErrorCode.DICTIONARY_NOT_FOUND,
            "Dictionary not found",
            f"Dictionary ID: {dictionary_id}",
            status_code=404
        )


class DictionaryInvalidException(HangmanException):
    """Raised when dictionary data is invalid."""
    
    def __init__(self, reason: str):
        super().__init__(
            ErrorCode.DICTIONARY_INVALID,
            "Dictionary is invalid",
            reason,
            status_code=400
        )


class DictionaryTooFewWordsException(HangmanException):
    """Raised when dictionary has too few words."""
    
    def __init__(self, count: int, minimum: int = 10):
        super().__init__(
            ErrorCode.DICTIONARY_TOO_FEW_WORDS,
            "Dictionary has too few words",
            f"Dictionary has {count} words, minimum is {minimum}",
            status_code=400
        )


class DictionaryAlreadyExistsException(HangmanException):
    """Raised when dictionary ID already exists."""
    
    def __init__(self, dictionary_id: str):
        super().__init__(
            ErrorCode.DICTIONARY_ALREADY_EXISTS,
            "Dictionary already exists",
            f"Dictionary ID '{dictionary_id}' is already in use",
            status_code=409
        )


# Validation Exceptions

class ValidationException(HangmanException):
    """Raised for validation errors."""
    
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            ErrorCode.VALIDATION_ERROR,
            message,
            detail,
            status_code=422
        )


# Server Exceptions

class InternalServerException(HangmanException):
    """Raised for internal server errors."""
    
    def __init__(self, detail: Optional[str] = None):
        super().__init__(
            ErrorCode.INTERNAL_ERROR,
            "Internal server error",
            detail,
            status_code=500
        )
