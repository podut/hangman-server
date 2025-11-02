"""Authentication service: user registration, login, token management."""

from datetime import datetime
from typing import Optional, Dict, Any
from ..repositories.user_repository import UserRepository
from ..utils.auth_utils import hash_password, verify_password, create_access_token
from ..exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    UserNotFoundException
)


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        
    def register_user(self, email: str, password: str, nickname: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user."""
        # Check if email already exists
        if self.user_repo.get_by_email(email):
            raise UserAlreadyExistsException(email)
            
        # Generate user ID
        user_id = f"u_{self.user_repo.count() + 1}"
        
        # First user is admin
        is_admin = self.user_repo.count() == 0
        
        # Create user
        user_data = {
            "user_id": user_id,
            "email": email,
            "password": hash_password(password),
            "nickname": nickname or email.split("@")[0],
            "is_admin": is_admin,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        self.user_repo.create(user_data)
        
        return {
            "user_id": user_id,
            "email": email,
            "nickname": user_data["nickname"],
            "is_admin": is_admin,
            "created_at": user_data["created_at"]
        }
        
    def login_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return tokens."""
        user = self.user_repo.get_by_email(email)
        
        if not user or not verify_password(password, user["password"]):
            raise InvalidCredentialsException()
            
        access_token = create_access_token({"sub": user["user_id"]})
        refresh_token = create_access_token({"sub": user["user_id"], "type": "refresh"})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": 3600,  # 60 minutes
            "user_id": user["user_id"]
        }
        
    def refresh_token(self, user_id: str) -> Dict[str, str]:
        """Generate a new access token."""
        access_token = create_access_token({"sub": user_id})
        return {
            "access_token": access_token,
            "expires_in": 3600
        }
        
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID (excluding password)."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id)
        return {k: v for k, v in user.items() if k != "password"}
        
    def is_admin(self, user_id: str) -> bool:
        """Check if user is admin."""
        user = self.user_repo.get_by_id(user_id)
        return user.get("is_admin", False) if user else False
