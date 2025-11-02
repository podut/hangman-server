"""Hangman Server API - Clean refactored version."""

from fastapi import FastAPI, Depends, HTTPException, status, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
import asyncio
import json
import logging

# Import config
from .config import settings

# Import models
from .models import (
    RegisterRequest, LoginRequest, RefreshRequest,
    CreateSessionRequest, GuessRequest, ErrorResponse,
    ForgotPasswordRequest, ResetPasswordRequest, UpdateProfileRequest
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
from .exceptions import (
    UnauthorizedException, ForbiddenException, TokenInvalidException,
    DictionaryNotFoundException, DictionaryInvalidException
)

# Import middleware
from .middleware import RequestIDMiddleware, LoggingMiddleware, RateLimiterMiddleware, IdempotencyMiddleware

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

# 2. Rate limiter (before logging to avoid logging rate-limited requests)
app.add_middleware(RateLimiterMiddleware)

# 3. Idempotency middleware (before logging so replays are logged)
# DISABLED: BaseHTTPMiddleware conflicts with FastAPI response handling
# The middleware code exists but is not active due to technical limitations
# Consider implementing idempotency at endpoint level for critical operations
# app.add_middleware(IdempotencyMiddleware, ttl_hours=24)

# 4. Logging middleware
app.add_middleware(LoggingMiddleware)

# 5. Request ID middleware (innermost - closest to endpoint)
app.add_middleware(RequestIDMiddleware)

# Security - auto_error=False so we can return 401 instead of 403
security = HTTPBearer(auto_error=False)

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
dict_service = DictionaryService(dict_repo, session_repo)


# ============= DEPENDENCIES =============

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Dependency to get current authenticated user."""
    if not credentials:
        raise UnauthorizedException("Authorization header required")
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


# Initialize Prometheus metrics instrumentation
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=False,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[],
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)

# Instrument the app and expose /metrics endpoint
instrumentator.instrument(app).expose(app, include_in_schema=True, tags=["Observability"])


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
        # Add token_type for standard OAuth2 response
        return {**result, "token_type": "bearer"}
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/v1/auth/refresh")
def refresh(req: RefreshRequest):
    """Refresh access token."""
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise TokenInvalidException("Invalid refresh token type")
        result = auth_service.refresh_token(payload["sub"])
        # Return refresh token back with new access token and token_type
        return {**result, "refresh_token": req.refresh_token, "token_type": "bearer"}
    except ValueError:
        raise TokenInvalidException("Invalid or expired refresh token")


@app.post("/api/v1/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    """Request password reset token."""
    return auth_service.request_password_reset(req.email)


@app.post("/api/v1/auth/reset-password")
def reset_password(req: ResetPasswordRequest):
    """Reset password using token."""
    return auth_service.reset_password(req.token, req.new_password)


@app.get("/api/v1/users/me")
def get_profile(user=Depends(get_current_user)):
    """Get current user profile."""
    return user


@app.patch("/api/v1/users/me")
def update_profile(req: UpdateProfileRequest, user=Depends(get_current_user)):
    """Update user profile (email and/or nickname)."""
    user_id = user["user_id"]
    
    # At least one field must be provided
    if req.email is None and req.nickname is None:
        raise HTTPException(status_code=400, detail="At least one field (email or nickname) must be provided")
    
    # Update profile
    updated_user = auth_service.update_profile(user_id, req.email, req.nickname)
    return updated_user


@app.delete("/api/v1/users/me", status_code=204)
def delete_account(user=Depends(get_current_user)):
    """Delete user account and all associated data (GDPR compliance)."""
    user_id = user["user_id"]
    
    # Cascade delete all user data
    # 1. Get all user sessions to delete games
    user_sessions = session_repo.get_by_user(user_id)
    session_ids = [s["session_id"] for s in user_sessions]
    
    # 2. Delete all games for those sessions (includes guesses)
    games_deleted = game_repo.delete_by_user(user_id, session_ids)
    logger.info(f"Deleted {games_deleted} games for user {user_id}")
    
    # 3. Delete all sessions
    sessions_deleted = session_repo.delete_by_user(user_id)
    logger.info(f"Deleted {sessions_deleted} sessions for user {user_id}")
    
    # 4. Delete user account
    user_deleted = user_repo.delete(user_id)
    if not user_deleted:
        logger.error(f"Failed to delete user {user_id}")
        raise HTTPException(status_code=500, detail="Failed to delete user account")
    
    logger.info(f"User account {user_id} deleted successfully")
    return None  # 204 No Content


@app.get("/api/v1/users/me/export")
def export_user_data(user=Depends(get_current_user)):
    """Export all user data (GDPR data portability - Article 20)."""
    user_id = user["user_id"]
    
    # Export all user data
    export_data = auth_service.export_user_data(
        user_id,
        session_repo,
        game_repo,
        stats_service
    )
    
    logger.info(f"User data export generated for user {user_id}")
    return export_data


@app.get("/api/v1/events/stream")
async def event_stream(user=Depends(get_current_user)):
    """Server-Sent Events endpoint for real-time notifications.
    
    Streams events to authenticated users:
    - game_completed: When a game finishes (WON/LOST/ABORTED)
    - session_finished: When all games in a session are complete
    - leaderboard_update: When user position changes (future)
    
    Client usage:
    ```javascript
    const eventSource = new EventSource('/api/v1/events/stream', {
        headers: { 'Authorization': 'Bearer <token>' }
    });
    
    eventSource.addEventListener('game_completed', (e) => {
        const data = JSON.parse(e.data);
        console.log('Game finished:', data);
    });
    ```
    """
    from .utils.event_manager import event_manager
    
    user_id = user["user_id"]
    queue = asyncio.Queue()
    
    async def event_generator():
        """Generate SSE events for the client."""
        try:
            # Subscribe to events
            await event_manager.subscribe(user_id, queue)
            logger.info(f"SSE stream started for user {user_id}")
            
            # Send initial connection event
            yield f"event: connected\ndata: {json.dumps({'user_id': user_id, 'timestamp': datetime.utcnow().isoformat() + 'Z'})}\n\n"
            
            # Stream events
            while True:
                try:
                    # Wait for event with timeout to allow periodic heartbeat
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    
                    # Format as SSE
                    event_type = event.get("event", "message")
                    event_data = json.dumps(event)
                    yield f"event: {event_type}\ndata: {event_data}\n\n"
                    
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"
                    
        except asyncio.CancelledError:
            logger.info(f"SSE stream cancelled for user {user_id}")
        except Exception as e:
            logger.error(f"Error in SSE stream for user {user_id}: {e}")
        finally:
            # Unsubscribe on disconnect
            await event_manager.unsubscribe(user_id, queue)
            logger.info(f"SSE stream ended for user {user_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============= WEBSOCKET ENDPOINT =============

class ConnectionManager:
    """WebSocket connection manager for real-time bidirectional communication."""
    
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Connect a WebSocket for a user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info(f"WebSocket connected for user {user_id}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Disconnect a WebSocket."""
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to specific user's WebSocket connections."""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending WebSocket message to {user_id}: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected connections
            for conn in disconnected:
                self.disconnect(conn, user_id)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_personal_message(message, user_id)


ws_manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """
    WebSocket endpoint for real-time bidirectional communication.
    
    Authentication via query parameter: /ws?token=<jwt_token>
    
    Message format:
    - Client -> Server:
      {
        "type": "ping" | "subscribe" | "unsubscribe" | "message",
        "data": {...}
      }
    
    - Server -> Client:
      {
        "type": "pong" | "game_update" | "session_update" | "notification",
        "data": {...},
        "timestamp": "2025-11-02T10:30:45Z"
      }
    
    Example client (JavaScript):
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws?token=' + accessToken);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Received:', data);
    };
    
    ws.send(JSON.stringify({
        type: 'subscribe',
        data: { channel: 'games' }
    }));
    ```
    """
    # Authenticate user BEFORE accepting connection
    user_id = None
    if not token:
        await websocket.accept()
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            await websocket.accept()
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        user = auth_service.get_user_by_id(user_id)
        if not user:
            await websocket.accept()
            await websocket.close(code=1008, reason="User not found")
            return
    except Exception as e:
        logger.warning(f"WebSocket authentication failed: {e}")
        await websocket.accept()
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Accept and connect WebSocket
    await ws_manager.connect(websocket, user_id)
    
    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "data": {
            "user_id": user_id,
            "message": "WebSocket connection established"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            msg_type = data.get("type", "")
            msg_data = data.get("data", {})
            
            # Handle different message types
            if msg_type == "ping":
                # Respond with pong
                await websocket.send_json({
                    "type": "pong",
                    "data": {"timestamp": datetime.utcnow().isoformat() + "Z"},
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
            
            elif msg_type == "subscribe":
                # Subscribe to channel (future enhancement)
                channel = msg_data.get("channel", "general")
                await websocket.send_json({
                    "type": "subscribed",
                    "data": {"channel": channel},
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
                logger.info(f"User {user_id} subscribed to channel {channel}")
            
            elif msg_type == "message":
                # Echo message back (or handle custom logic)
                await websocket.send_json({
                    "type": "message_received",
                    "data": msg_data,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
            
            else:
                # Unknown message type
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": f"Unknown message type: {msg_type}"},
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                })
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        ws_manager.disconnect(websocket, user_id)


# ============= SESSION ENDPOINTS =============

@app.get("/api/v1/sessions")
def list_user_sessions(user=Depends(get_current_user)):
    """List all sessions for the current user."""
    try:
        user_sessions = session_repo.get_by_user(user["user_id"])
        
        # Add game counts for each session
        result = []
        for session in user_sessions:
            session_games = game_repo.get_by_session(session["session_id"])
            finished = sum(1 for g in session_games if g["status"] in ["WON", "LOST", "ABORTED"])
            result.append({
                **session,
                "games_created": len(session_games),
                "games_finished": finished
            })
        
        return result
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sessions", status_code=201)
def create_session(req: CreateSessionRequest, request: Request, user=Depends(get_current_user)):
    """
    Create a new game session.
    
    Supports idempotency via Idempotency-Key header.
    """
    from .utils.idempotency import _idempotency_store
    import hashlib
    
    # Check for idempotency key
    idempotency_key = request.headers.get("Idempotency-Key")
    
    if idempotency_key:
        # Generate composite key (user_id + idempotency_key)
        composite_key = f"{user['user_id']}:{idempotency_key}"
        
        # Check if already processed
        if composite_key in _idempotency_store:
            cached_result, timestamp = _idempotency_store[composite_key]
            from datetime import datetime, timedelta
            if datetime.utcnow() - timestamp < timedelta(hours=24):
                logger.info(f"Idempotency replay: key={idempotency_key}, endpoint=create_session")
                return cached_result
    
    # Execute normally
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
        
        # Store result if idempotency key was provided
        if idempotency_key:
            from datetime import datetime
            _idempotency_store[composite_key] = (result, datetime.utcnow())
        
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
    request: Request,
    session_id: str,
    page: int = 1,
    page_size: int = 10,
    user=Depends(get_current_user)
):
    """List games in a session with pagination."""
    from .utils.pagination import build_link_header
    from fastapi.responses import JSONResponse
    
    try:
        result = game_service.list_session_games(session_id, user["user_id"], page, page_size)
        
        # Build Link header for pagination (RFC 5988)
        base_url = str(request.url).split('?')[0]
        link_header = build_link_header(
            base_url=base_url,
            page=page,
            page_size=page_size,
            total_items=result.get("total", 0)
        )
        
        # Create response with Link header
        return JSONResponse(
            content=result,
            headers={"Link": link_header}
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@app.get("/api/v1/sessions/{session_id}/stats")
def get_session_stats(session_id: str, user=Depends(get_current_user)):
    """Get statistics for a session."""
    try:
        # Verify session exists and user has access
        session = session_service.get_session(session_id, user["user_id"])
        
        # Get all games for session
        session_games = game_repo.get_by_session(session_id)
        
        # Filter finished games (won or lost, not aborted)
        finished_games = [g for g in session_games if g["status"] in ["WON", "LOST"]]
        
        if not finished_games:
            return {
                "session_id": session_id,
                "games_total": session["num_games"],
                "games_finished": 0,
                "games_won": 0,
                "games_lost": 0,
                "games_aborted": 0,
                "win_rate": 0.0,
                "avg_total_guesses": 0.0,
                "avg_wrong_letters": 0.0,
                "avg_time_sec": 0.0,
                "composite_score": 0.0
            }
        
        # Calculate statistics
        wins = sum(1 for g in finished_games if g["status"] == "WON")
        losses = sum(1 for g in finished_games if g["status"] == "LOST")
        aborted = sum(1 for g in session_games if g["status"] == "ABORTED")
        
        total_guesses = sum(g["total_guesses"] for g in finished_games)
        total_wrong = sum(len(g["wrong_letters"]) for g in finished_games)
        total_time = sum(g.get("time_seconds", 0) for g in finished_games)
        total_score = sum(g.get("composite_score", 0) for g in finished_games)
        
        return {
            "session_id": session_id,
            "games_total": session["num_games"],
            "games_finished": len(finished_games),
            "games_won": wins,
            "games_lost": losses,
            "games_aborted": aborted,
            "win_rate": (wins / len(finished_games) * 100) if finished_games else 0.0,
            "avg_total_guesses": total_guesses / len(finished_games) if finished_games else 0.0,
            "avg_wrong_letters": total_wrong / len(finished_games) if finished_games else 0.0,
            "avg_time_sec": total_time / len(finished_games) if finished_games else 0.0,
            "composite_score": total_score
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ============= GAME ENDPOINTS =============

@app.post("/api/v1/sessions/{session_id}/games", status_code=201)
def create_game(session_id: str, request: Request, user=Depends(get_current_user)):
    """
    Create a new game in a session.
    
    Supports idempotency via Idempotency-Key header.
    """
    from .utils.idempotency import _idempotency_store
    
    # Check for idempotency key
    idempotency_key = request.headers.get("Idempotency-Key")
    
    if idempotency_key:
        # Generate composite key (user_id + session_id + idempotency_key)
        composite_key = f"{user['user_id']}:{session_id}:{idempotency_key}"
        
        # Check if already processed
        if composite_key in _idempotency_store:
            cached_result, timestamp = _idempotency_store[composite_key]
            from datetime import datetime, timedelta
            if datetime.utcnow() - timestamp < timedelta(hours=24):
                logger.info(f"Idempotency replay: key={idempotency_key}, endpoint=create_game")
                return cached_result
    
    # Execute normally
    try:
        result = game_service.create_game(session_id, user["user_id"])
        
        # Store result if idempotency key was provided
        if idempotency_key:
            from datetime import datetime
            _idempotency_store[composite_key] = (result, datetime.utcnow())
        
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


@app.get("/api/v1/sessions/{session_id}/games/{game_id}/history")
def get_game_history(session_id: str, game_id: str, user=Depends(get_current_user)):
    """Get guess history for a game."""
    try:
        result = game_service.get_game_history(game_id, user["user_id"])
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
def get_leaderboard(
    request: Request,
    metric: str = "composite_score",
    period: str = "all",
    limit: int = 10,
    page: int = 1
):
    """Get leaderboard with pagination support."""
    from .utils.pagination import build_link_header
    from fastapi.responses import JSONResponse
    
    # Calculate offset for pagination
    page_size = limit
    offset = (page - 1) * page_size
    
    # Get leaderboard entries (limit + 1 to check if there are more)
    result = stats_service.get_leaderboard(metric, period, page_size + 1)
    
    # Check if there are more entries
    has_more = len(result) > page_size
    entries = result[:page_size] if has_more else result
    
    # For leaderboard, we estimate total based on what we know
    # In production, you'd want to get actual total from stats_service
    estimated_total = offset + len(entries) + (1 if has_more else 0)
    
    response_data = {
        "entries": entries,
        "metric": metric,
        "period": period,
        "page": page,
        "page_size": page_size,
        "has_more": has_more
    }
    
    # Build Link header
    base_url = str(request.url).split('?')[0]
    link_header = build_link_header(
        base_url=base_url,
        page=page,
        page_size=page_size,
        total_items=estimated_total,
        query_params={"metric": metric, "period": period}
    )
    
    return JSONResponse(
        content=response_data,
        headers={"Link": link_header}
    )


# ============= ADMIN ENDPOINTS =============

@app.get("/api/v1/admin/stats")
def get_admin_stats(admin=Depends(get_admin_user)):
    """Get comprehensive admin dashboard statistics (admin only)."""
    result = stats_service.get_admin_stats()
    return result


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
        # Generate dict_id from name (slugified)
        import re
        dict_id = "dict_" + re.sub(r'[^a-z0-9_]', '_', name.lower().replace(' ', '_'))
        
        dict_data = {
            "dict_id": dict_id,
            "name": name,
            "words": words,
            "description": description,
            "language": language,
            "difficulty": difficulty
        }
        result = dict_service.create_dictionary(dict_data)
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
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if active is not None:
            updates["active"] = active
        
        result = dict_service.update_dictionary(dictionary_id, updates)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/v1/admin/dictionaries/{dictionary_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dictionary(dictionary_id: str, admin=Depends(get_admin_user)):
    """Delete a dictionary (admin only). Cannot delete if in use by active sessions."""
    try:
        dict_service.delete_dictionary(dictionary_id)
        return None
    except DictionaryNotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except DictionaryInvalidException as e:
        # Cannot delete dictionary that is in use
        raise HTTPException(status_code=409, detail=str(e))


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
    
    # Prepare uvicorn configuration
    uvicorn_config = {
        "app": app,
        "host": settings.server_host,
        "port": settings.server_port,
        "log_level": settings.log_level.lower()
    }
    
    # Add SSL/TLS configuration if enabled
    if settings.ssl_enabled:
        if settings.ssl_keyfile and settings.ssl_certfile:
            uvicorn_config["ssl_keyfile"] = settings.ssl_keyfile
            uvicorn_config["ssl_certfile"] = settings.ssl_certfile
            logger.info(f"✓ TLS enabled: keyfile={settings.ssl_keyfile}, certfile={settings.ssl_certfile}")
        else:
            logger.warning("⚠ SSL_ENABLED=True but ssl_keyfile or ssl_certfile not set. Running without TLS.")
    
    uvicorn.run(**uvicorn_config)
