"""Integration tests for session stats endpoint."""

import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


@pytest.fixture
def admin_headers():
    """Register and login first user (becomes admin)."""
    # Register
    client.post("/api/v1/auth/register", json={
        "email": "admin_session_stats@test.com",
        "password": "AdminPass123!",
        "nickname": "admin_session_stats"
    })
    
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": "admin_session_stats@test.com",
        "password": "AdminPass123!"
    })
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_session_stats_with_games(admin_headers):
    """Test getting session stats with completed games."""
    # Create session
    session_response = client.post(
        "/api/v1/sessions",
        headers=admin_headers,
        json={"num_games": 5, "max_misses": 6}
    )
    assert session_response.status_code == 201
    session_id = session_response.json()["session_id"]
    
    # Create and play some games
    for i in range(3):
        # Create game
        game_response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=admin_headers
        )
        game_id = game_response.json()["game_id"]
        
        # Make enough guesses to ensure game completion
        for letter in "abcdefghijklmnopqrstuvwxyz":
            guess_response = client.post(
                f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
                headers=admin_headers,
                json={"letter": letter}
            )
            # Check if game finished
            if guess_response.json().get("status") in ["WON", "LOST"]:
                break
    
    # Get stats
    stats_response = client.get(
        f"/api/v1/sessions/{session_id}/stats",
        headers=admin_headers
    )
    
    assert stats_response.status_code == 200
    data = stats_response.json()
    
    # Verify structure
    assert "session_id" in data
    assert "games_total" in data
    assert "games_finished" in data
    assert "games_won" in data
    assert "games_lost" in data
    assert "games_aborted" in data
    assert "win_rate" in data
    assert "avg_total_guesses" in data
    assert "avg_wrong_letters" in data
    assert "avg_time_sec" in data
    assert "composite_score" in data
    
    # Verify values
    assert data["session_id"] == session_id
    assert data["games_total"] == 5
    assert data["games_finished"] >= 1  # At least one game finished
    assert data["games_won"] + data["games_lost"] == data["games_finished"]
    assert 0 <= data["win_rate"] <= 100
    assert data["avg_total_guesses"] >= 0


def test_get_session_stats_empty(admin_headers):
    """Test getting stats for session with no finished games."""
    # Create session
    session_response = client.post(
        "/api/v1/sessions",
        headers=admin_headers,
        json={"num_games": 5, "max_misses": 6}
    )
    session_id = session_response.json()["session_id"]
    
    # Get stats immediately (no games played)
    stats_response = client.get(
        f"/api/v1/sessions/{session_id}/stats",
        headers=admin_headers
    )
    
    assert stats_response.status_code == 200
    data = stats_response.json()
    
    # Verify empty stats
    assert data["session_id"] == session_id
    assert data["games_finished"] == 0
    assert data["games_won"] == 0
    assert data["games_lost"] == 0
    assert data["win_rate"] == 0.0
    assert data["avg_total_guesses"] == 0.0
    assert data["composite_score"] == 0.0


def test_get_session_stats_not_found(admin_headers):
    """Test getting stats for non-existent session."""
    response = client.get(
        "/api/v1/sessions/s_999/stats",
        headers=admin_headers
    )
    
    assert response.status_code == 404


def test_get_session_stats_no_auth():
    """Test getting stats without authentication."""
    response = client.get(
        "/api/v1/sessions/s_1/stats"
    )
    
    assert response.status_code in [401, 403]


def test_get_session_stats_with_aborted_games(admin_headers):
    """Test stats calculation excludes aborted games."""
    # Create session
    session_response = client.post(
        "/api/v1/sessions",
        headers=admin_headers,
        json={"num_games": 5, "max_misses": 6}
    )
    session_id = session_response.json()["session_id"]
    
    # Create and finish one game
    game_response = client.post(
        f"/api/v1/sessions/{session_id}/games",
        headers=admin_headers
    )
    game_id = game_response.json()["game_id"]
    
    # Play until finished - guess enough letters to ensure game completion
    for letter in "abcdefghijklmnopqrstuvwxyz":
        guess_response = client.post(
            f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
            headers=admin_headers,
            json={"letter": letter}
        )
        if guess_response.json().get("status") in ["WON", "LOST"]:
            break
    
    # Create and abort another game
    game_response2 = client.post(
        f"/api/v1/sessions/{session_id}/games",
        headers=admin_headers
    )
    game_id2 = game_response2.json()["game_id"]
    
    client.post(
        f"/api/v1/sessions/{session_id}/games/{game_id2}/abort",
        headers=admin_headers
    )
    
    # Get stats
    stats_response = client.get(
        f"/api/v1/sessions/{session_id}/stats",
        headers=admin_headers
    )
    
    assert stats_response.status_code == 200
    data = stats_response.json()
    
    # Verify aborted game not counted in finished games
    assert data["games_finished"] == 1  # Only the finished one
    assert data["games_aborted"] == 1  # One aborted
    assert data["games_won"] + data["games_lost"] == 1
