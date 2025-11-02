"""Integration tests for user account deletion (GDPR compliance)."""

import pytest
import time
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

# Unique counter for emails to avoid conflicts
_email_counter = 0


def get_unique_email():
    """Generate a unique email for each test."""
    global _email_counter
    _email_counter += 1
    timestamp = int(time.time() * 1000)
    return f"delete_test_{timestamp}_{_email_counter}@example.com"


@pytest.fixture
def registered_user():
    """Create and return a registered user with tokens."""
    email = get_unique_email()
    password = "SecurePass123!"
    
    # Register
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "nickname": "DeleteMe"
    })
    assert response.status_code == 201
    user_data = response.json()
    
    # Login to get tokens
    response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 200
    login_data = response.json()
    
    return {
        "user_id": user_data["user_id"],
        "access_token": login_data["access_token"],
        "email": email,
        "password": password
    }


@pytest.fixture
def user_with_data(registered_user):
    """Create a user with sessions, games, and stats."""
    headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
    
    # Create a session with games
    response = client.post("/api/v1/sessions", json={
        "num_games": 3,
        "dictionary_id": "basic",
        "difficulty": "normal"
    }, headers=headers)
    assert response.status_code == 201
    session_data = response.json()
    session_id = session_data["session_id"]
    
    # Start and play some games
    response = client.post(f"/api/v1/sessions/{session_id}/games", headers=headers)
    assert response.status_code == 201
    game1_data = response.json()
    game1_id = game1_data["game_id"]
    
    # Make some guesses on first game
    client.post(f"/api/v1/sessions/{session_id}/games/{game1_id}/guess", json={"guess": "a"}, headers=headers)
    client.post(f"/api/v1/sessions/{session_id}/games/{game1_id}/guess", json={"guess": "e"}, headers=headers)
    
    # Start second game
    response = client.post(f"/api/v1/sessions/{session_id}/games", headers=headers)
    assert response.status_code == 201
    game2_data = response.json()
    game2_id = game2_data["game_id"]
    
    return {
        **registered_user,
        "session_id": session_id,
        "game_ids": [game1_id, game2_id]
    }


def test_delete_account_success(registered_user):
    """Test successful account deletion."""
    headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
    
    # Delete account
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    assert response.content == b""


def test_delete_account_cascades_sessions(user_with_data):
    """Test that deleting account also deletes all sessions."""
    headers = {"Authorization": f"Bearer {user_with_data['access_token']}"}
    session_id = user_with_data["session_id"]
    
    # Verify session exists before deletion
    response = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert response.status_code == 200
    
    # Delete account
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    
    # Try to access session - should fail (user is deleted, can't authenticate)
    response = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert response.status_code == 404  # User not found


def test_delete_account_cascades_games(user_with_data):
    """Test that deleting account also deletes all games."""
    headers = {"Authorization": f"Bearer {user_with_data['access_token']}"}
    session_id = user_with_data["session_id"]
    game_id = user_with_data["game_ids"][0]
    
    # Verify game exists before deletion
    response = client.get(f"/api/v1/sessions/{session_id}/games/{game_id}/state", headers=headers)
    assert response.status_code == 200
    
    # Delete account
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    
    # Try to access game - should fail (user is deleted)
    response = client.get(f"/api/v1/sessions/{session_id}/games/{game_id}/state", headers=headers)
    assert response.status_code == 404  # User or game not found


def test_delete_account_unauthorized_no_token():
    """Test that deletion without token returns 401."""
    response = client.delete("/api/v1/users/me")
    assert response.status_code == 401
    data = response.json()
    assert data["error_code"] == "UNAUTHORIZED"
    assert "Authentication required" in data["message"]


def test_delete_account_unauthorized_invalid_token():
    """Test that deletion with invalid token returns 401."""
    headers = {"Authorization": "Bearer invalid_token_xyz"}
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 401
    data = response.json()
    assert data["error_code"] == "UNAUTHORIZED"


def test_deleted_account_cannot_login(registered_user):
    """Test that deleted account cannot be used to login."""
    headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
    email = registered_user["email"]
    password = registered_user["password"]
    
    # Delete account
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    
    # Try to login with deleted account
    response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 401
    data = response.json()
    assert "Invalid" in data["message"] or "password" in data["message"]


def test_deleted_account_token_invalid(registered_user):
    """Test that tokens from deleted account become invalid."""
    headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
    
    # Delete account
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    
    # Try to use old token to access profile
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 404
    data = response.json()
    assert "User not found" in data["message"]


def test_delete_account_idempotent_fails_after_first():
    """Test that deleting account twice fails on second attempt."""
    email = get_unique_email()
    password = "SecurePass123!"
    
    # Register user
    response = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "nickname": "DoubleDelete"
    })
    assert response.status_code == 201
    
    # Login to get token
    response = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # First deletion succeeds
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    
    # Second deletion fails (user doesn't exist anymore)
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 404  # User not found


def test_delete_account_removes_all_game_history(user_with_data):
    """Test that game history is completely removed after deletion."""
    headers = {"Authorization": f"Bearer {user_with_data['access_token']}"}
    session_id = user_with_data["session_id"]
    game_id = user_with_data["game_ids"][0]
    
    # Verify game history exists
    response = client.get(f"/api/v1/sessions/{session_id}/games/{game_id}/history", headers=headers)
    assert response.status_code == 200
    history = response.json()
    # Note: guesses might be empty if no valid guesses were made
    
    # Delete account
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    
    # Try to access game history - should fail
    response = client.get(f"/api/v1/sessions/{session_id}/games/{game_id}/history", headers=headers)
    assert response.status_code == 404  # User or game not found


def test_delete_account_removes_session_stats(user_with_data):
    """Test that session stats are removed after deletion."""
    headers = {"Authorization": f"Bearer {user_with_data['access_token']}"}
    session_id = user_with_data["session_id"]
    
    # Verify stats exist
    response = client.get(f"/api/v1/sessions/{session_id}/stats", headers=headers)
    assert response.status_code == 200
    
    # Delete account
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    
    # Try to access stats - should fail
    response = client.get(f"/api/v1/sessions/{session_id}/stats", headers=headers)
    assert response.status_code == 404  # User or session not found


def test_delete_account_multiple_sessions(registered_user):
    """Test that all sessions are deleted when user has multiple sessions."""
    headers = {"Authorization": f"Bearer {registered_user['access_token']}"}
    
    # Create multiple sessions
    session_ids = []
    for i in range(3):
        response = client.post("/api/v1/sessions", json={
            "num_games": 2,
            "dictionary_id": "basic",
            "difficulty": "easy"
        }, headers=headers)
        assert response.status_code == 201
        session_ids.append(response.json()["session_id"])
    
    # Delete account
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    
    # Verify all sessions are inaccessible
    for session_id in session_ids:
        response = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
        assert response.status_code == 404  # User not found


def test_delete_account_gdpr_compliance(user_with_data):
    """Test GDPR right to be forgotten - all data must be removed."""
    headers = {"Authorization": f"Bearer {user_with_data['access_token']}"}
    user_id = user_with_data["user_id"]
    session_id = user_with_data["session_id"]
    game_ids = user_with_data["game_ids"]
    
    # Verify data exists
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["user_id"] == user_id
    
    response = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert response.status_code == 200
    
    for game_id in game_ids:
        response = client.get(f"/api/v1/sessions/{session_id}/games/{game_id}/state", headers=headers)
        assert response.status_code == 200
    
    # Delete account
    response = client.delete("/api/v1/users/me", headers=headers)
    assert response.status_code == 204
    
    # Verify all data is gone (404 because user/resources don't exist)
    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 404
    
    response = client.get(f"/api/v1/sessions/{session_id}", headers=headers)
    assert response.status_code == 404
    
    for game_id in game_ids:
        response = client.get(f"/api/v1/sessions/{session_id}/games/{game_id}/state", headers=headers)
        assert response.status_code == 404
