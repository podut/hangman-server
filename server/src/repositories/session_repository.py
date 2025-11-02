"""Session repository: in-memory session storage."""

from typing import Dict, Optional, List


class SessionRepository:
    """Repository for session data management."""
    
    def __init__(self):
        self._sessions: Dict[str, dict] = {}
        
    def create(self, session_data: dict) -> dict:
        """Create a new session."""
        self._sessions[session_data["session_id"]] = session_data
        return session_data
        
    def get_by_id(self, session_id: str) -> Optional[dict]:
        """Get session by ID."""
        return self._sessions.get(session_id)
        
    def get_by_user(self, user_id: str) -> List[dict]:
        """Get all sessions for a user."""
        return [s for s in self._sessions.values() if s["user_id"] == user_id]
        
    def update(self, session_id: str, updates: dict) -> Optional[dict]:
        """Update session data."""
        if session_id in self._sessions:
            self._sessions[session_id].update(updates)
            return self._sessions[session_id]
        return None
        
    def get_all(self) -> List[dict]:
        """Get all sessions."""
        return list(self._sessions.values())
        
    def count(self) -> int:
        """Count total sessions."""
        return len(self._sessions)
