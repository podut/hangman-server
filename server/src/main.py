"""Hangman Server API - Clean refactored version."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from datetime import datetime
import logging

# Import config
from .config import settings

# Import models
from .models import (
    RegisterRequest, LoginRequest, RefreshRequest,
    CreateSessionRequest, GuessRequest, ErrorResponse
)

# Import repositories
from .repositories import (
    UserRepository, SessionRepository,
    GameRepository, DictionaryRepository
)

# Import services
from .services import (
    AuthService, SessionService, GameService,
    StatsService, DictionaryService
)

# Import utils
from .utils.auth_utils import decode_token
from .utils.logging_config import setup_logging

# Import exception handlers
from .error_handlers import register_exception_handlers
from .exceptions import UnauthorizedException, ForbiddenException

# Import middleware
from .middleware import RequestIDMiddleware, LoggingMiddleware

# Configure logging with structured format
setup_logging(log_level=settings.log_level, log_format=settings.log_format)
logger = logging.getLogger(__name__)

# Validate configuration at startup
try:
    settings.validate_config()
    logger.info("✓ Configuration validation passed")
except ValueError as e:
    logger.warning(f"⚠ Configuration validation warnings: {e}")
    if not settings.debug:
        logger.error("Configuration errors in production mode - refusing to start")
        raise  # Fail fast in production
    else:
        logger.info("Running in DEBUG mode - proceeding despite validation warnings")

# Initialize FastAPI app
app = FastAPI(
    title="Hangman Server API",
    version="1.0.0",
    description="Hangman game server with modular architecture",
    debug=settings.debug,
    responses={
        400: {"model": ErrorResponse, "description": "Bad Request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden"},
        404: {"model": ErrorResponse, "description": "Not Found"},
        409: {"model": ErrorResponse, "description": "Conflict"},
        422: {"model": ErrorResponse, "description": "Validation Error"},
        500: {"model": ErrorResponse, "description": "Internal Server Error"},
    }
)

# Register exception handlers
register_exception_handlers(app)

# Add middleware (order matters - last added is executed first)
# 1. CORS (outermost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins_list(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Logging middleware
app.add_middleware(LoggingMiddleware)

# 3. Request ID middleware (innermost - closest to endpoint)
app.add_middleware(RequestIDMiddleware)

# Security
security = HTTPBearer()

# Initialize repositories (singletons)
user_repo = UserRepository()
session_repo = SessionRepository()
game_repo = GameRepository()
dict_repo = DictionaryRepository()

# Initialize services with dependency injection
auth_service = AuthService(user_repo)
session_service = SessionService(session_repo, dict_repo)
game_service = GameService(game_repo, session_repo, dict_repo)
stats_service = StatsService(user_repo, session_repo, game_repo)
dict_service = DictionaryService(dict_repo)


# ============= DEPENDENCIES =============

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user."""
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedException("Invalid token: missing user ID")
        user = auth_service.get_user_by_id(user_id)
        if not user:
            raise UnauthorizedException("User not found")
        return user
    except ValueError as e:
        # decode_token raises ValueError for invalid tokens
        raise UnauthorizedException(str(e))


def get_admin_user(user=Depends(get_current_user)):
    """Dependency to ensure user is admin."""
    if not auth_service.is_admin(user["user_id"]):
        raise ForbiddenException("Admin access required")
    return user


# ============= UTILITY ENDPOINTS =============

@app.get("/healthz")
def health():
    """Health check endpoint."""
    return {"ok": True}


@app.get("/version")
def version():
    """Get API version."""
    return {"version": "1.0.0", "build": "2025-11-02"}


@app.get("/time")
def server_time():
    """Get server time."""
    return {"time": datetime.utcnow().isoformat() + "Z"}


# ============= AUTH ENDPOINTS =============

@app.post("/api/v1/auth/register", status_code=201)
def register(req: RegisterRequest):
    """Register a new user."""
    try:
        result = auth_service.register_user(req.email, req.password, req.nickname)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/auth/login")
def login(req: LoginRequest):
    """Login and get access token."""
    try:
        result = auth_service.login_user(req.email, req.password)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/v1/auth/refresh")
def refresh(req: RefreshRequest):
    """Refresh access token."""
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        result = auth_service.refresh_token(payload["sub"])
        return result
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


@app.get("/api/v1/users/me")
def get_profile(user=Depends(get_current_user)):
    """Get current user profile."""
    return user


# ============= SESSION ENDPOINTS =============

@app.post("/api/v1/sessions", status_code=201)
def create_session(req: CreateSessionRequest, user=Depends(get_current_user)):
    """Create a new game session."""
    try:
        result = session_service.create_session(
            user_id=user["user_id"],
            num_games=req.num_games,
            dictionary_id=req.dictionary_id,
            difficulty=req.difficulty,
            language=req.language,
            max_misses=req.max_misses,
            allow_word_guess=req.allow_word_guess,
            seed=req.seed
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id: str, user=Depends(get_current_user)):
    """Get session details."""
    try:
        session = session_service.get_session(session_id, user["user_id"])
        
        # Add game counts
        session_games = game_repo.get_by_session(session_id)
        finished = sum(1 for g in session_games if g["status"] in ["WON", "LOST", "ABORTED"])
        
        return {
            **session,
            "games_finished": finished,
            "games_total": session["num_games"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/abort")
def abort_session(session_id: str, user=Depends(get_current_user)):
    """Abort a session."""
    try:
        result = session_service.abort_session(session_id, user["user_id"])
        
        # Abort all IN_PROGRESS games in session
        for game in game_repo.get_by_session(session_id):
            if game["status"] == "IN_PROGRESS":
                game_repo.update(game["game_id"], {
                    "status": "ABORTED",
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                })
        
        return {"session_id": session_id, "status": "ABORTED", "message": "Session aborted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/games")
def list_session_games(
    session_id: str,
    page: int = 1,
    page_size: int = 10,
    user=Depends(get_current_user)
):
    """List games in a session with pagination."""
    try:
        result = game_service.list_session_games(session_id, user["user_id"], page, page_size)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ============= GAME ENDPOINTS =============

@app.post("/api/v1/sessions/{session_id}/games", status_code=201)
def create_game(session_id: str, user=Depends(get_current_user)):
    """Create a new game in a session."""
    try:
        result = game_service.create_game(session_id, user["user_id"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/games/{game_id}/state")
def get_game_state(session_id: str, game_id: str, user=Depends(get_current_user)):
    """Get current game state."""
    try:
        game = game_service.get_game(game_id, user["user_id"])
        return game
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/games/{game_id}/guess")
def make_guess(session_id: str, game_id: str, req: GuessRequest, user=Depends(get_current_user)):
    """Make a guess (letter or word)."""
    try:
        if req.letter:
            result = game_service.make_guess_letter(game_id, req.letter, user["user_id"])
        elif req.word:
            result = game_service.make_guess_word(game_id, req.word, user["user_id"])
        else:
            raise HTTPException(status_code=400, detail="Must provide letter or word")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.post("/api/v1/sessions/{session_id}/games/{game_id}/abort")
def abort_game(session_id: str, game_id: str, user=Depends(get_current_user)):
    """Abort a game."""
    try:
        result = game_service.abort_game(game_id, user["user_id"])
        return {"game_id": game_id, "status": "ABORTED", "message": "Game aborted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ============= STATISTICS ENDPOINTS =============

@app.get("/api/v1/users/{user_id}/stats")
def get_user_stats(user_id: str, period: str = "all", current_user=Depends(get_current_user)):
    """Get user statistics."""
    if user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = stats_service.get_user_stats(user_id, period)
    return result


@app.get("/api/v1/stats/global")
def get_global_stats(period: str = "all"):
    """Get global statistics."""
    result = stats_service.get_global_stats(period)
    return result


@app.get("/api/v1/leaderboard")
def get_leaderboard(metric: str = "composite_score", period: str = "all", limit: int = 10):
    """Get leaderboard."""
    result = stats_service.get_leaderboard(metric, period, limit)
    return {"entries": result, "metric": metric, "period": period}


# ============= ADMIN ENDPOINTS =============

@app.get("/api/v1/admin/dictionaries")
def list_dictionaries(admin=Depends(get_admin_user)):
    """List all dictionaries (admin only)."""
    result = dict_service.list_dictionaries(active_only=False)
    return {"dictionaries": result}


@app.post("/api/v1/admin/dictionaries", status_code=201)
def create_dictionary(
    name: str,
    words: list[str],
    description: Optional[str] = None,
    language: str = "ro",
    difficulty: str = "auto",
    admin=Depends(get_admin_user)
):
    """Create a new dictionary (admin only)."""
    try:
        result = dict_service.create_dictionary(name, words, description, language, difficulty)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.patch("/api/v1/admin/dictionaries/{dictionary_id}")
def update_dictionary(
    dictionary_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    active: Optional[bool] = None,
    admin=Depends(get_admin_user)
):
    """Update dictionary metadata (admin only)."""
    try:
        result = dict_service.update_dictionary(dictionary_id, name, description, active)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/v1/admin/dictionaries/{dictionary_id}/words")
def get_dictionary_words(dictionary_id: str, sample: Optional[int] = None, admin=Depends(get_admin_user)):
    """Get words from a dictionary (admin only)."""
    try:
        result = dict_service.get_dictionary_words(dictionary_id, sample)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ============= STARTUP/SHUTDOWN =============

@app.on_event("startup")
async def startup_event():
    """Log configuration on startup."""
    logger.info("=" * 60)
    logger.info("Hangman Server Starting")
    logger.info("=" * 60)
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info(f"Server: {settings.server_host}:{settings.server_port}")
    logger.info(f"CORS Origins: {settings.get_cors_origins_list()}")
    logger.info(f"JWT Algorithm: {settings.jwt_algorithm}")
    logger.info(f"Token Expiry: {settings.access_token_expire_minutes} minutes")
    logger.info(f"Max Sessions/User: {settings.max_sessions_per_user}")
    logger.info(f"Max Games/Session: {settings.max_games_per_session}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("Hangman Server Shutting Down")


# ============= MAIN =============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host=settings.server_host, 
        port=settings.server_port,
        log_level=settings.log_level.lower()
    )
