"""Integration tests for authentication endpoints."""

from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    def test_register_user_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "SecurePass123!"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["email"] == "newuser@example.com"
        assert "password" not in data
        
    def test_register_user_duplicate_email(self, client):
        """Test registration with duplicate email."""
        # Register first user
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "Pass123!"
            }
        )
        
        # Try to register again with same email
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "DifferentPass123!"
            }
        )
        
        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == "USER_EXISTS"
        
    def test_register_user_invalid_password(self, client):
        """Test registration with invalid password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "weak"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error_code"] == "INVALID_PASSWORD"
        
    def test_login_success(self, client):
        """Test successful login."""
        # Register user first
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "logintest@example.com",
                "password": "LoginPass123!"
            }
        )
        
        # Login
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "logintest@example.com",
                "password": "LoginPass123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "WrongPass123!"
            }
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "INVALID_CREDENTIALS"
        
    def test_refresh_token_success(self, client):
        """Test token refresh."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "refreshtest@example.com",
                "password": "RefreshPass123!"
            }
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "refreshtest@example.com",
                "password": "RefreshPass123!"
            }
        )
        
        refresh_token = login_response.json()["refresh_token"]
        
        # Refresh token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        
    def test_refresh_token_invalid(self, client):
        """Test refresh with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token_here"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error_code"] == "INVALID_TOKEN"


class TestAuthMiddleware:
    """Test authentication middleware."""
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.post("/api/v1/sessions")
        
        assert response.status_code == 401
        
    def test_protected_endpoint_with_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token."""
        response = client.post(
            "/api/v1/sessions",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
        
    def test_protected_endpoint_with_valid_token(self, client):
        """Test accessing protected endpoint with valid token."""
        # Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "protected@example.com",
                "password": "ProtectedPass123!"
            }
        )
        
        login_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "protected@example.com",
                "password": "ProtectedPass123!"
            }
        )
        
        access_token = login_response.json()["access_token"]
        
        # Access protected endpoint
        response = client.post(
            "/api/v1/sessions",
            headers={"Authorization": f"Bearer {access_token}"},
            json={
                "num_games": 3,
                "dictionary_id": "dict_ro_basic",
                "difficulty": "normal",
                "language": "ro",
                "max_misses": 6,
                "allow_word_guess": True
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
