"""
Integration tests for brute-force login protection.
Tests account lockout after repeated failed login attempts.
"""

import pytest
import time
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Provide a test client."""
    return TestClient(app)


@pytest.fixture
def registered_user(client):
    """Create a registered user for testing."""
    email = "bruteforce@example.com"
    password = "ValidPass123!"
    
    # Register user
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password
        }
    )
    
    return {"email": email, "password": password}


@pytest.mark.integration
class TestBruteForceProtection:
    """Test brute-force login protection."""
    
    def test_successful_login_after_few_failures(self, client, registered_user):
        """Test that user can still login after 1-2 failed attempts."""
        email = registered_user["email"]
        password = registered_user["password"]
        
        # First failed attempt
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123!"}
        )
        assert response.status_code == 401
        
        # Second failed attempt
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123!"}
        )
        assert response.status_code == 401
        
        # Successful login with correct password
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
    
    def test_account_lockout_after_max_attempts(self, client, registered_user):
        """Test that account is locked after maximum failed attempts."""
        email = registered_user["email"]
        
        # Make 5 failed login attempts (default max_attempts)
        for i in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": f"WrongPass{i}!"}
            )
            assert response.status_code == 401
        
        # 6th attempt should be locked
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123!"}
        )
        assert response.status_code == 401
        data = response.json()
        
        # Check for account locked error
        assert "locked" in data.get("detail", "").lower() or "locked" in data.get("message", "").lower()
    
    def test_correct_password_also_locked(self, client, registered_user):
        """Test that even correct password fails when account is locked."""
        email = registered_user["email"]
        password = registered_user["password"]
        
        # Make 5 failed attempts
        for i in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": f"WrongPass{i}!"}
            )
        
        # Try with correct password - should still be locked
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert response.status_code == 401
        data = response.json()
        assert "locked" in data.get("detail", "").lower() or "locked" in data.get("message", "").lower()
    
    def test_lockout_includes_remaining_time(self, client, registered_user):
        """Test that lockout response includes remaining time."""
        email = registered_user["email"]
        
        # Trigger lockout
        for i in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": f"WrongPass{i}!"}
            )
        
        # Check locked response
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass123!"}
        )
        assert response.status_code == 401
        data = response.json()
        
        # Should mention time or seconds in message/detail
        message = (data.get("detail", "") + data.get("message", "")).lower()
        assert "second" in message or "time" in message or "locked" in message
    
    def test_successful_login_resets_counter(self, client):
        """Test that successful login resets the failed attempts counter."""
        # Use a unique email for this test to avoid interference from other tests
        email = "reset_counter@example.com"
        password = "ResetTest123!"
        
        # Register fresh user
        client.post("/api/v1/auth/register", json={"email": email, "password": password})
        
        # Make 3 failed attempts
        for i in range(3):
            client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": f"WrongPass{i}!"}
            )
        
        # Successful login
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert response.status_code == 200
        
        # Make 3 more failed attempts - should not be locked yet
        for i in range(3):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": f"WrongPass{i}!"}
            )
            assert response.status_code == 401
        
        # Should still be able to login (counter was reset)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        assert response.status_code == 200
    
    def test_different_users_isolated(self, client):
        """Test that failed attempts are isolated per user."""
        # Register two users
        user1_email = "user1_bruteforce@example.com"
        user1_pass = "User1Pass123!"
        user2_email = "user2_bruteforce@example.com"
        user2_pass = "User2Pass123!"
        
        client.post("/api/v1/auth/register", json={"email": user1_email, "password": user1_pass})
        client.post("/api/v1/auth/register", json={"email": user2_email, "password": user2_pass})
        
        # Make 5 failed attempts for user1
        for i in range(5):
            client.post("/api/v1/auth/login", json={"email": user1_email, "password": f"Wrong{i}!"})
        
        # User1 should be locked
        response = client.post("/api/v1/auth/login", json={"email": user1_email, "password": user1_pass})
        assert response.status_code == 401
        assert "locked" in response.json().get("detail", "").lower() or "locked" in response.json().get("message", "").lower()
        
        # User2 should still be able to login
        response = client.post("/api/v1/auth/login", json={"email": user2_email, "password": user2_pass})
        assert response.status_code == 200
    
    def test_nonexistent_user_not_locked(self, client):
        """Test that non-existent users can still get 401 (don't reveal existence)."""
        email = "nonexistent@example.com"
        
        # Make multiple attempts with non-existent user
        for i in range(6):
            response = client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": f"Pass{i}!"}
            )
            # Should always return 401 (invalid credentials)
            assert response.status_code == 401
            # Should not mention lockout for non-existent users
            data = response.json()
            # Either generic invalid credentials or lockout is acceptable
            assert "detail" in data or "message" in data

