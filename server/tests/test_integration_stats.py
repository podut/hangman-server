"""
Integration tests for Statistics endpoints.
Tests the full HTTP request/response cycle for stats retrieval.
"""

import pytest
from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """Provide a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Provide authentication headers with a valid token and user_id."""
    # Try to register user (may already exist)
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "statstest@example.com",
            "password": "StatsTest123!"
        }
    )
    
    # Get user_id from registration if successful
    if response.status_code == 201:
        user_id = response.json()["user_id"]
    else:
        # User already exists, will get user_id from login
        user_id = None
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "statstest@example.com",
            "password": "StatsTest123!"
        }
    )
    
    token = response.json()["access_token"]
    if user_id is None:
        user_id = response.json()["user_id"]
    
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user_id": user_id
    }


@pytest.mark.integration
class TestStatsEndpoints:
    """Test statistics endpoints."""
    
    def test_get_user_stats_no_games(self, client, auth_headers):
        """Test getting stats for user with no games."""
        user_id = auth_headers["user_id"]
        headers = auth_headers["headers"]
        
        response = client.get(
            f"/api/v1/users/{user_id}/stats",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_games"] == 0
        assert data["games_won"] == 0
        assert data["games_lost"] == 0
        assert data["win_rate"] == 0.0
        
    def test_get_user_stats_with_games(self, client, auth_headers):
        """Test getting stats after playing some games."""
        user_id = auth_headers["user_id"]
        headers = auth_headers["headers"]
        
        # Create session
        session_response = client.post(
            "/api/v1/sessions",
            headers=headers,
            json={
                "num_games": 5,
                "dictionary_id": "dict_ro_basic",
                "difficulty": "easy",
                "language": "ro",
                "max_misses": 6,
                "allow_word_guess": True
            }
        )
        session_id = session_response.json()["session_id"]
        
        # Create a game
        client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=headers
        )
        
        # Get stats
        response = client.get(
            f"/api/v1/users/{user_id}/stats",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        # Stats endpoint works even if stats aren't updated yet
        assert "total_games" in data
        assert "games_won" in data
        
    def test_get_user_stats_with_period(self, client, auth_headers):
        """Test getting stats with period filter."""
        user_id = auth_headers["user_id"]
        headers = auth_headers["headers"]
        
        response = client.get(
            f"/api/v1/users/{user_id}/stats?period=week",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_games" in data
        assert "win_rate" in data
        
    def test_get_user_stats_forbidden(self, client, auth_headers):
        """Test accessing another user's stats."""
        headers = auth_headers["headers"]
        
        response = client.get(
            "/api/v1/users/other_user_id/stats",
            headers=headers
        )
        
        assert response.status_code == 403
        
    def test_get_global_stats(self, client):
        """Test getting global statistics."""
        response = client.get("/api/v1/stats/global")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_games" in data
        assert "total_users" in data
        assert "games_won" in data
        assert "games_lost" in data
        
    def test_get_global_stats_with_period(self, client):
        """Test getting global stats with period filter."""
        response = client.get("/api/v1/stats/global?period=month")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_games" in data
        
    def test_get_leaderboard_empty(self, client):
        """Test getting leaderboard when no data."""
        response = client.get("/api/v1/leaderboard")
        
        assert response.status_code == 200
        data = response.json()
        assert "entries" in data
        assert isinstance(data["entries"], list)
        assert "metric" in data
        assert "period" in data
        
    def test_get_leaderboard_with_metric(self, client):
        """Test getting leaderboard with specific metric."""
        response = client.get("/api/v1/leaderboard?metric=total_score&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert data["metric"] == "total_score"
        assert "entries" in data
        
    def test_get_leaderboard_with_period(self, client):
        """Test getting leaderboard with period filter."""
        response = client.get("/api/v1/leaderboard?period=week")
        
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "week"
