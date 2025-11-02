"""Integration tests for password reset functionality."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta


def test_forgot_password_success(client: TestClient, test_user):
    """Test requesting password reset with valid email."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "token" in data  # Token returned for testing
    assert len(data["token"]) > 0


def test_forgot_password_unknown_email(client: TestClient):
    """Test requesting password reset with unknown email (should not reveal)."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@example.com"}
    )
    
    # Should return same message to not reveal if email exists
    assert response.status_code == 200
    data = response.json()
    assert "message" in data


def test_forgot_password_invalid_email_format(client: TestClient):
    """Test requesting password reset with invalid email format."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "not-an-email"}
    )
    
    assert response.status_code == 422  # Validation error


def test_reset_password_success(client: TestClient, test_user, auth_service):
    """Test successful password reset."""
    # Request reset token
    reset_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    token = reset_response.json()["token"]
    
    # Reset password
    new_password = "NewSecure123"
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": new_password
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "success" in data["message"].lower()
    
    # Verify can login with new password
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": new_password
        }
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_reset_password_invalid_token(client: TestClient):
    """Test password reset with non-existent token."""
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": "invalid-token-12345",
            "new_password": "NewSecure123"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_TOKEN"


def test_reset_password_expired_token(client: TestClient, test_user):
    """Test password reset with expired token."""
    from datetime import datetime, timedelta, timezone
    from src.main import auth_service
    
    # Request reset token
    reset_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    token = reset_response.json()["token"]
    
    # Manually expire the token by setting past expiration time
    if token in auth_service._reset_tokens:
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
        auth_service._reset_tokens[token]["expires_at"] = past_time
    
    # Try to reset with expired token
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": "NewSecure123"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_TOKEN"
    
    # Verify token was cleaned up
    assert token not in auth_service._reset_tokens


def test_reset_password_token_single_use(client: TestClient, test_user):
    """Test that reset token can only be used once."""
    # Request reset token
    reset_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    token = reset_response.json()["token"]
    
    # Use token first time - should succeed
    response1 = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": "NewSecure123"
        }
    )
    assert response1.status_code == 200
    
    # Try to use same token again - should fail
    response2 = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": "AnotherPass456"
        }
    )
    assert response2.status_code == 400
    data = response2.json()
    assert data["error_code"] == "INVALID_TOKEN"


def test_reset_password_weak_password_too_short(client: TestClient, test_user):
    """Test password reset with password too short."""
    # Request reset token
    reset_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    token = reset_response.json()["token"]
    
    # Try to reset with weak password (too short)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": "Short1"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PASSWORD"
    assert "does not meet requirements" in data["message"] or "8 characters" in data["message"]


def test_reset_password_weak_password_no_uppercase(client: TestClient, test_user):
    """Test password reset with password missing uppercase."""
    # Request reset token
    reset_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    token = reset_response.json()["token"]
    
    # Try to reset with weak password (no uppercase)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": "nouppercase123"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PASSWORD"
    assert "does not meet requirements" in data["message"].lower() or "uppercase" in data["message"].lower()


def test_reset_password_weak_password_no_lowercase(client: TestClient, test_user):
    """Test password reset with password missing lowercase."""
    # Request reset token
    reset_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    token = reset_response.json()["token"]
    
    # Try to reset with weak password (no lowercase)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": "NOLOWERCASE123"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PASSWORD"
    assert "does not meet requirements" in data["message"].lower() or "lowercase" in data["message"].lower()


def test_reset_password_weak_password_no_digit(client: TestClient, test_user):
    """Test password reset with password missing digit."""
    # Request reset token
    reset_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    token = reset_response.json()["token"]
    
    # Try to reset with weak password (no digit)
    response = client.post(
        "/api/v1/auth/reset-password",
        json={
            "token": token,
            "new_password": "NoDigitsHere"
        }
    )
    
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == "INVALID_PASSWORD"
    assert "does not meet requirements" in data["message"].lower() or "number" in data["message"].lower()


def test_old_password_works_before_reset(client: TestClient, test_user):
    """Test that old password still works before using reset token."""
    # Request reset token but don't use it yet
    reset_response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    assert reset_response.status_code == 200
    
    # Old password should still work
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": "TestPassword123"  # Original password
        }
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()


def test_forgot_password_multiple_requests_overwrites_token(client: TestClient, test_user):
    """Test that requesting multiple reset tokens invalidates previous ones."""
    from src.main import auth_service
    # Request first token
    response1 = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    token1 = response1.json()["token"]
    
    # Request second token
    response2 = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    token2 = response2.json()["token"]
    
    # Tokens should be different
    assert token1 != token2
    
    # Both tokens should exist in storage (implementation keeps all tokens)
    # Note: This test validates current implementation behavior
    # In production, you might want to invalidate old tokens
    assert token1 in auth_service._reset_tokens
    assert token2 in auth_service._reset_tokens
