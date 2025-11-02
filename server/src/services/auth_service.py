"""Authentication service: user registration, login, token management."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets
from ..repositories.user_repository import UserRepository
from ..utils.auth_utils import hash_password, verify_password, create_access_token
from ..utils.login_tracker import LoginAttemptTracker
from ..config import settings
from ..exceptions import (
    UserAlreadyExistsException,
    InvalidCredentialsException,
    UserNotFoundException,
    InvalidPasswordException,
    InvalidTokenException,
    AccountLockedException
)


class AuthService:
    """Service for authentication operations."""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        # In-memory storage for reset tokens (in production, use Redis or database)
        self._reset_tokens: Dict[str, Dict[str, Any]] = {}
        # Login attempt tracker for brute-force protection
        self.login_tracker = LoginAttemptTracker(
            max_attempts=settings.max_login_attempts,
            lockout_duration_minutes=settings.login_lockout_duration_minutes,
            attempt_window_minutes=settings.login_attempt_window_minutes
        )
        
    def register_user(self, email: str, password: str, nickname: Optional[str] = None) -> Dict[str, Any]:
        """Register a new user."""
        # Validate password
        if len(password) < 8:
            raise InvalidPasswordException("Password must be at least 8 characters")
        if not any(c.isupper() for c in password):
            raise InvalidPasswordException("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in password):
            raise InvalidPasswordException("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in password):
            raise InvalidPasswordException("Password must contain at least one number")
        
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
        # Check if account is locked
        if self.login_tracker.is_locked(email):
            lockout_seconds = self.login_tracker.get_lockout_remaining(email)
            raise AccountLockedException(lockout_seconds or 0)
        
        user = self.user_repo.get_by_email(email)
        
        if not user or not verify_password(password, user["password"]):
            # Record failed attempt
            self.login_tracker.record_failed_attempt(email)
            raise InvalidCredentialsException()
        
        # Successful login - reset failed attempts
        self.login_tracker.record_successful_login(email)
            
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
    
    def request_password_reset(self, email: str) -> Dict[str, str]:
        """Generate password reset token for user."""
        user = self.user_repo.get_by_email(email)
        
        if not user:
            # Don't reveal if email exists for security
            return {"message": "If the email exists, a reset link has been sent"}
        
        # Generate secure random token
        token = secrets.token_urlsafe(32)
        
        # Store token with expiration (15 minutes)
        self._reset_tokens[token] = {
            "email": email,
            "user_id": user["user_id"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
        }
        
        # In production, send email with reset link
        # For now, just return the token (for testing)
        return {
            "message": "If the email exists, a reset link has been sent",
            "token": token  # Only for testing - remove in production
        }
    
    def reset_password(self, token: str, new_password: str) -> Dict[str, str]:
        """Reset password using reset token."""
        # Validate token exists
        if token not in self._reset_tokens:
            raise InvalidTokenException("Token not found or already used")
        
        token_data = self._reset_tokens[token]
        
        # Check if token expired
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        if datetime.now(timezone.utc) > expires_at:
            # Clean up expired token
            del self._reset_tokens[token]
            raise InvalidTokenException("Token has expired")
        
        # Validate new password
        if len(new_password) < 8:
            raise InvalidPasswordException("Password must be at least 8 characters")
        if not any(c.isupper() for c in new_password):
            raise InvalidPasswordException("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in new_password):
            raise InvalidPasswordException("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in new_password):
            raise InvalidPasswordException("Password must contain at least one number")
        
        # Update password
        user = self.user_repo.get_by_id(token_data["user_id"])
        if not user:
            raise UserNotFoundException(token_data["user_id"])
        
        user["password"] = hash_password(new_password)
        self.user_repo.update(user["user_id"], {"password": user["password"]})
        
        # Invalidate token
        del self._reset_tokens[token]
        
        return {"message": "Password successfully reset"}
    
    def update_profile(self, user_id: str, email: Optional[str] = None, nickname: Optional[str] = None) -> Dict[str, Any]:
        """Update user profile (email and/or nickname)."""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundException(user_id)
        
        updates = {}
        
        # Update email if provided
        if email is not None:
            # Check if new email is different
            if email != user["email"]:
                # Check if email already exists
                existing_user = self.user_repo.get_by_email(email)
                if existing_user:
                    raise UserAlreadyExistsException(email)
                updates["email"] = email
        
        # Update nickname if provided
        if nickname is not None:
            updates["nickname"] = nickname
        
        # Apply updates if any
        if updates:
            self.user_repo.update(user_id, updates)
            user.update(updates)
        
        # Return updated user without password
        return {k: v for k, v in user.items() if k != "password"}
