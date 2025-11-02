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
    
    def delete(self, session_id: str) -> bool:
        """Delete session by ID. Returns True if deleted, False if not found."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False
    
    def delete_by_user(self, user_id: str) -> int:
        """Delete all sessions for a user. Returns number of sessions deleted."""
        sessions_to_delete = [sid for sid, s in self._sessions.items() if s["user_id"] == user_id]
        for session_id in sessions_to_delete:
            del self._sessions[session_id]
        return len(sessions_to_delete)
    
    def is_dictionary_in_use(self, dictionary_id: str) -> bool:
        """Check if dictionary is used by any active sessions."""
        for session in self._sessions.values():
            if session.get("status") == "ACTIVE":
                # Dictionary ID is stored in params.dictionary_id
                params = session.get("params", {})
                if params.get("dictionary_id") == dictionary_id:
                    return True
        return False
