"""User repository: in-memory user storage."""

from typing import Dict, Optional, List


class UserRepository:
    """Repository for user data management."""
    
    def __init__(self):
        self._users: Dict[str, dict] = {}
        
    def create(self, user_data: dict) -> dict:
        """Create a new user."""
        self._users[user_data["user_id"]] = user_data
        return user_data
        
    def get_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID."""
        return self._users.get(user_id)
        
    def get_by_email(self, email: str) -> Optional[dict]:
        """Get user by email."""
        for user in self._users.values():
            if user["email"] == email:
                return user
        return None
        
    def get_all(self) -> List[dict]:
        """Get all users."""
        return list(self._users.values())
        
    def count(self) -> int:
        """Count total users."""
        return len(self._users)
        
    def exists(self, user_id: str) -> bool:
        """Check if user exists."""
        return user_id in self._users
