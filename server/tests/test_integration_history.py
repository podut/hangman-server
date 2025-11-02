"""Integration tests for game history endpoint."""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


@pytest.fixture
def admin_headers():
    """Register and login first user (becomes admin)."""
    # Register
    client.post("/api/v1/auth/register", json={
        "email": "admin_history@test.com",
        "password": "AdminPass123!",
        "nickname": "admin_history"
    })
    
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": "admin_history@test.com",
        "password": "AdminPass123!"
    })
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_game_history_success(admin_headers):
    """Test getting game history with multiple guesses."""
    # Create session
    session_response = client.post(
        "/api/v1/sessions",
        headers=admin_headers,
        json={"num_games": 1, "max_misses": 6}
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["session_id"]
    
    # Create game
    game_response = client.post(
        f"/api/v1/sessions/{session_id}/games",
        headers=admin_headers
    )
    assert game_response.status_code == 201
    game_id = game_response.json()["game_id"]
    
    # Make some guesses
    client.post(
        f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
        headers=admin_headers,
        json={"letter": "a"}
    )
    
    client.post(
        f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
        headers=admin_headers,
        json={"letter": "e"}
    )
    
    client.post(
        f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
        headers=admin_headers,
        json={"letter": "i"}
    )
    
    # Get history
    history_response = client.get(
        f"/api/v1/sessions/{session_id}/games/{game_id}/history",
        headers=admin_headers
    )
    
    assert history_response.status_code == 200
    data = history_response.json()
    
    # Verify structure
    assert "game_id" in data
    assert "session_id" in data
    assert "status" in data
    assert "guesses" in data
    assert "total_guesses" in data
    
    assert data["game_id"] == game_id
    assert data["session_id"] == session_id
    assert data["total_guesses"] == 3
    assert len(data["guesses"]) == 3
    
    # Verify each guess has required fields
    for guess in data["guesses"]:
        assert "index" in guess
        assert "type" in guess
        assert "value" in guess
        assert "correct" in guess
        assert "pattern_after" in guess
        assert "timestamp" in guess


def test_get_game_history_empty(admin_headers):
    """Test getting history for game with no guesses."""
    # Create session and game
    session_response = client.post(
        "/api/v1/sessions",
        headers=admin_headers,
        json={"num_games": 1, "max_misses": 6}
    )
    session_id = session_response.json()["session_id"]
    
    game_response = client.post(
        f"/api/v1/sessions/{session_id}/games",
        headers=admin_headers
    )
    game_id = game_response.json()["game_id"]
    
    # Get history immediately
    history_response = client.get(
        f"/api/v1/sessions/{session_id}/games/{game_id}/history",
        headers=admin_headers
    )
    
    assert history_response.status_code == 200
    data = history_response.json()
    assert data["total_guesses"] == 0
    assert len(data["guesses"]) == 0


def test_get_game_history_not_found(admin_headers):
    """Test getting history for non-existent game."""
    response = client.get(
        "/api/v1/sessions/s_999/games/g_999/history",
        headers=admin_headers
    )
    
    assert response.status_code == 404


def test_get_game_history_no_auth():
    """Test getting history without authentication."""
    response = client.get(
        "/api/v1/sessions/s_1/games/g_1/history"
    )
    
    assert response.status_code in [401, 403]


def test_get_game_history_pattern_progression(admin_headers):
    """Test that history shows pattern progression."""
    # Create session and game
    session_response = client.post(
        "/api/v1/sessions",
        headers=admin_headers,
        json={"num_games": 1, "max_misses": 6}
    )
    session_id = session_response.json()["session_id"]
    
    game_response = client.post(
        f"/api/v1/sessions/{session_id}/games",
        headers=admin_headers
    )
    game_id = game_response.json()["game_id"]
    
    # Make several guesses
    letters = ["a", "e", "i", "o", "u"]
    for letter in letters:
        client.post(
            f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
            headers=admin_headers,
            json={"letter": letter}
        )
    
    # Get history
    history_response = client.get(
        f"/api/v1/sessions/{session_id}/games/{game_id}/history",
        headers=admin_headers
    )
    
    data = history_response.json()
    guesses = data["guesses"]
    
    # Verify indices are sequential
    for i, guess in enumerate(guesses, 1):
        assert guess["index"] == i
        assert guess["type"] == "LETTER"
        assert guess["value"] in letters
        assert "pattern_after" in guess
        # Pattern should show some progression
        assert isinstance(guess["pattern_after"], str)
