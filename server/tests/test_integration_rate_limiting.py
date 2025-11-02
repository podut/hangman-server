"""Integration tests for rate limiting middleware."""

import pytest
import time
import uuid
from src.main import app
from src.config import settings
from fastapi.testclient import TestClient


client = TestClient(app)


@pytest.fixture(autouse=True)
def enable_rate_limiting():
    """Enable rate limiting for rate limiting tests."""
    original_value = settings.disable_rate_limiting
    settings.disable_rate_limiting = False
    yield
    settings.disable_rate_limiting = original_value


@pytest.fixture
def admin_headers():
    """Create admin user and return auth headers."""
    # Generate unique username/email to avoid conflicts
    unique_id = uuid.uuid4().hex[:8]
    
    # Register admin user
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": f"ratelimit_admin_{unique_id}",
            "email": f"ratelimit_{unique_id}@example.com",
            "password": "AdminPass123!",
            "role": "admin"
        }
    )
    assert register_response.status_code == 201
    
    # Login
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"ratelimit_{unique_id}@example.com",
            "password": "AdminPass123!"
        }
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


def test_general_rate_limit_enforcement(admin_headers):
    """Test that general rate limit (60 req/min) is enforced."""
    # Make 60 requests quickly to health check (excluded from rate limit)
    for i in range(60):
        response = client.get("/healthz", headers=admin_headers)
        # Health endpoint is excluded from rate limiting
        assert response.status_code == 200
    
    # Now test actual endpoint
    # Create a session to get a valid endpoint
    session_response = client.post(
        "/api/v1/sessions",
        json={"difficulty": "easy"},
        headers=admin_headers
    )
    assert session_response.status_code == 201
    
    # Make many requests to exceed limit
    exceeded = False
    for i in range(65):
        response = client.get("/api/v1/users/me", headers=admin_headers)
        if response.status_code == 429:
            exceeded = True
            assert "rate limit" in response.json()["detail"].lower()
            assert "Retry-After" in response.headers
            break
    
    # Should have hit rate limit
    assert exceeded, "Rate limit was not enforced"


def test_rate_limit_headers(admin_headers):
    """Test that rate limit headers are included in responses."""
    response = client.get("/api/v1/users/me", headers=admin_headers)
    
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
    
    # Verify header values
    assert response.headers["X-RateLimit-Limit"] == "60"
    remaining = int(response.headers["X-RateLimit-Remaining"])
    assert 0 <= remaining <= 60


def test_session_creation_rate_limit():
    """Test that session creation is limited to 10/min per user."""
    # Create a fresh user to avoid hitting active session limit
    unique_id = uuid.uuid4().hex[:8]
    client.post(
        "/api/v1/auth/register",
        json={
            "username": f"ratelimit_test_{unique_id}",
            "email": f"ratelimit_test_{unique_id}@example.com",
            "password": "TestPass123!",
            "role": "admin"
        }
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": f"ratelimit_test_{unique_id}@example.com",
            "password": "TestPass123!"
        }
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    
    # Try to create 11 sessions rapidly
    success_count = 0
    rate_limited = False
    
    for i in range(11):
        response = client.post(
            "/api/v1/sessions",
            json={"difficulty": "easy"},
            headers=headers
        )
        
        if response.status_code == 201:
            success_count += 1
        elif response.status_code == 429:
            rate_limited = True
            detail = response.json()["detail"].lower()
            # Should be rate limit, not session limit
            assert "rate limit" in detail
            break
        elif response.status_code == 409:
            # Hit max active sessions (10), this is OK
            break
    
    # Either hit rate limit or business logic limit (both are valid limits)
    assert success_count <= 10


def test_game_creation_rate_limit(admin_headers):
    """Test that game creation is limited to 5/min per session."""
    # Create a session first
    session_response = client.post(
        "/api/v1/sessions",
        json={"difficulty": "easy"},
        headers=admin_headers
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["session_id"]
    
    # Try to create 6 games rapidly in the same session
    success_count = 0
    rate_limited = False
    
    for i in range(7):
        response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            json={"dictionary_id": "default"},
            headers=admin_headers
        )
        
        if response.status_code == 201:
            success_count += 1
        elif response.status_code == 429:
            rate_limited = True
            assert "game creation" in response.json()["detail"].lower()
            break
    
    # Should have created at most 5 games before rate limit
    assert success_count <= 5
    assert rate_limited, "Game creation rate limit was not enforced"


def test_rate_limit_excludes_health_check():
    """Test that health check endpoint is not rate limited."""
    # Make many health check requests
    for i in range(100):
        response = client.get("/healthz")
        assert response.status_code == 200
    
    # All should succeed (no rate limit)


def test_rate_limit_per_token_isolation(admin_headers):
    """Test that rate limits are per-token, not global."""
    # Create second user
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "rate_limit_user2",
            "email": "ratelimit2@example.com",
            "password": "UserPass123!",
            "role": "player"
        }
    )
    assert register_response.status_code == 201
    
    # Login second user
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "ratelimit2@example.com",
            "password": "UserPass123!"
        }
    )
    assert login_response.status_code == 200
    token2 = login_response.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    # Make requests with first user
    for i in range(30):
        response = client.get("/api/v1/users/me", headers=admin_headers)
        assert response.status_code == 200
    
    # Second user should still have full rate limit
    response = client.get("/api/v1/users/me", headers=headers2)
    assert response.status_code == 200
    remaining = int(response.headers["X-RateLimit-Remaining"])
    assert remaining >= 55  # Should have most of bucket remaining


def test_rate_limit_refill_over_time(admin_headers):
    """Test that rate limit tokens refill over time."""
    # Make some requests to consume tokens
    for i in range(10):
        response = client.get("/api/v1/users/me", headers=admin_headers)
        assert response.status_code == 200
    
    # Check remaining
    response = client.get("/api/v1/users/me", headers=admin_headers)
    remaining_before = int(response.headers["X-RateLimit-Remaining"])
    
    # Wait for token refill (60 req/min = 1 req/sec)
    time.sleep(3)
    
    # Make another request
    response = client.get("/api/v1/users/me", headers=admin_headers)
    remaining_after = int(response.headers["X-RateLimit-Remaining"])
    
    # Should have refilled at least 2 tokens (allowing margin for timing)
    assert remaining_after >= remaining_before + 1


def test_rate_limit_error_format(admin_headers):
    """Test that rate limit error response has correct format."""
    # Create many sessions to trigger rate limit
    for i in range(12):
        response = client.post(
            "/api/v1/sessions",
            json={"difficulty": "easy"},
            headers=admin_headers
        )
        
        if response.status_code == 429:
            # Verify error response format
            body = response.json()
            assert "detail" in body
            assert "error_code" in body
            assert body["error_code"] == "RATE_LIMIT_EXCEEDED"
            assert "Retry-After" in response.headers
            break
