"""Login attempt tracking for brute-force protection."""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class LoginAttempt:
    """Data class for tracking login attempts."""
    email: str
    failed_attempts: int
    last_attempt: datetime
    locked_until: Optional[datetime] = None


class LoginAttemptTracker:
    """Track failed login attempts and implement exponential backoff."""
    
    def __init__(
        self,
        max_attempts: int = 5,
        lockout_duration_minutes: int = 15,
        attempt_window_minutes: int = 15
    ):
        """
        Initialize login attempt tracker.
        
        Args:
            max_attempts: Maximum failed attempts before lockout
            lockout_duration_minutes: Duration of account lockout in minutes
            attempt_window_minutes: Time window to reset failed attempts counter
        """
        self._attempts: Dict[str, LoginAttempt] = {}
        self.max_attempts = max_attempts
        self.lockout_duration = timedelta(minutes=lockout_duration_minutes)
        self.attempt_window = timedelta(minutes=attempt_window_minutes)
    
    def is_locked(self, email: str) -> bool:
        """Check if account is currently locked due to failed attempts."""
        attempt = self._attempts.get(email)
        if not attempt or not attempt.locked_until:
            return False
        
        now = datetime.now(timezone.utc)
        
        # Check if lockout has expired
        if now >= attempt.locked_until:
            # Reset the attempt record
            self._attempts[email] = LoginAttempt(
                email=email,
                failed_attempts=0,
                last_attempt=now,
                locked_until=None
            )
            return False
        
        return True
    
    def get_lockout_remaining(self, email: str) -> Optional[int]:
        """Get remaining lockout time in seconds, or None if not locked."""
        attempt = self._attempts.get(email)
        if not attempt or not attempt.locked_until:
            return None
        
        now = datetime.now(timezone.utc)
        if now >= attempt.locked_until:
            return None
        
        remaining = (attempt.locked_until - now).total_seconds()
        return int(remaining)
    
    def record_failed_attempt(self, email: str) -> None:
        """Record a failed login attempt and apply lockout if needed."""
        now = datetime.now(timezone.utc)
        
        attempt = self._attempts.get(email)
        
        if not attempt:
            # First failed attempt
            self._attempts[email] = LoginAttempt(
                email=email,
                failed_attempts=1,
                last_attempt=now,
                locked_until=None
            )
            return
        
        # Check if previous attempts are outside the time window
        if now - attempt.last_attempt > self.attempt_window:
            # Reset counter if outside attempt window
            self._attempts[email] = LoginAttempt(
                email=email,
                failed_attempts=1,
                last_attempt=now,
                locked_until=None
            )
            return
        
        # Increment failed attempts
        attempt.failed_attempts += 1
        attempt.last_attempt = now
        
        # Apply lockout if max attempts reached
        if attempt.failed_attempts >= self.max_attempts:
            attempt.locked_until = now + self.lockout_duration
    
    def record_successful_login(self, email: str) -> None:
        """Reset failed attempts counter after successful login."""
        if email in self._attempts:
            del self._attempts[email]
    
    def get_failed_attempts(self, email: str) -> int:
        """Get the number of failed attempts for an email."""
        attempt = self._attempts.get(email)
        if not attempt:
            return 0
        
        now = datetime.now(timezone.utc)
        
        # Check if attempts are outside time window
        if now - attempt.last_attempt > self.attempt_window:
            return 0
        
        return attempt.failed_attempts
    
    def get_delay_seconds(self, email: str) -> int:
        """
        Calculate exponential backoff delay in seconds.
        
        Returns delay based on number of failed attempts:
        - 0-2 attempts: no delay
        - 3 attempts: 5 seconds
        - 4 attempts: 10 seconds
        - 5+ attempts: locked out
        """
        attempts = self.get_failed_attempts(email)
        
        if attempts <= 2:
            return 0
        elif attempts == 3:
            return 5
        elif attempts == 4:
            return 10
        else:
            # Account is locked
            remaining = self.get_lockout_remaining(email)
            return remaining if remaining else 0
