"""Session service: session management business logic."""

from datetime import datetime
from typing import Dict, Any, List, Optional
from ..repositories.session_repository import SessionRepository
from ..repositories.dictionary_repository import DictionaryRepository
from ..config import get_settings
from ..exceptions import (
    SessionNotFoundException,
    SessionAccessDeniedException,
    SessionAlreadyFinishedException,
    MaxSessionsExceededException
)

settings = get_settings()


class SessionService:
    """Service for session operations."""
    
    def __init__(self, session_repo: SessionRepository, dict_repo: DictionaryRepository):
        self.session_repo = session_repo
        self.dict_repo = dict_repo
        
    def create_session(
        self,
        user_id: str,
        num_games: int,
        dictionary_id: str,
        difficulty: str,
        language: str,
        max_misses: int,
        allow_word_guess: bool,
        seed: Optional[int]
    ) -> Dict[str, Any]:
        """Create a new game session."""
        # Check max sessions per user limit
        user_sessions = self.session_repo.get_by_user(user_id)
        active_sessions = [s for s in user_sessions if s["status"] == "ACTIVE"]
        if len(active_sessions) >= settings.max_sessions_per_user:
            raise MaxSessionsExceededException(settings.max_sessions_per_user)
        
        session_id = f"s_{self.session_repo.count() + 1}"
        
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "num_games": num_games,
            "params": {
                "dictionary_id": dictionary_id,
                "difficulty": difficulty,
                "language": language,
                "max_misses": max_misses,
                "allow_word_guess": allow_word_guess,
                "seed": seed
            },
            "status": "ACTIVE",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "finished_at": None,
            "games_created": 0
        }
        
        self.session_repo.create(session_data)
        
        return {
            "session_id": session_id,
            "num_games": num_games,
            "status": "ACTIVE",
            "created_at": session_data["created_at"]
        }
        
    def get_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Get session details."""
        session = self.session_repo.get_by_id(session_id)
        
        if not session:
            raise SessionNotFoundException(session_id)
            
        if session["user_id"] != user_id:
            raise SessionAccessDeniedException(session_id)
            
        return session
        
    def list_user_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """List all sessions for a user."""
        return self.session_repo.get_by_user(user_id)
        
    def abort_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Abort an active session."""
        session = self.get_session(session_id, user_id)
        
        if session["status"] != "ACTIVE":
            raise ValueError("Session is not active")
            
        updates = {
            "status": "ABORTED",
            "finished_at": datetime.utcnow().isoformat() + "Z"
        }
        
        self.session_repo.update(session_id, updates)
        
        return {**session, **updates}
