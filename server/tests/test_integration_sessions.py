"""
Integration tests for Session endpoints.
Tests the full HTTP request/response cycle for session management.
"""

import pytest
from fastapi.testclient import TestClient
from server.src.main import app


@pytest.fixture
def client():
    """Provide a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Provide authentication headers with a valid token."""
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "sessiontest@example.com",
            "password": "SessionTest123!"
        }
    )
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "sessiontest@example.com",
            "password": "SessionTest123!"
        }
    )
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
class TestSessionEndpoints:
    """Test session CRUD endpoints."""
    
    def test_create_session_success(self, client, auth_headers):
        """Test creating a new session."""
        response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={
                "num_games": 5,
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
        assert data["num_games"] == 5
        assert data["status"] == "ACTIVE"
        
    def test_create_session_invalid_difficulty(self, client, auth_headers):
        """Test creating session with invalid difficulty."""
        response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={
                "num_games": 5,
                "dictionary_id": "dict_ro_basic",
                "difficulty": "invalid",  # Invalid value
                "language": "ro",
                "max_misses": 6,
                "allow_word_guess": True
            }
        )
        
        assert response.status_code == 422  # Validation error
        
    def test_get_session_success(self, client, auth_headers):
        """Test retrieving a session."""
        # Create session first
        create_response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={
                "num_games": 3,
                "dictionary_id": "dict_ro_basic",
                "difficulty": "easy",
                "language": "ro",
                "max_misses": 6,
                "allow_word_guess": True
            }
        )
        session_id = create_response.json()["session_id"]
        
        # Get session
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "games_finished" in data
        assert "games_total" in data
        
    def test_get_session_not_found(self, client, auth_headers):
        """Test getting non-existent session."""
        response = client.get(
            "/api/v1/sessions/nonexistent",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        
    def test_abort_session_success(self, client, auth_headers):
        """Test aborting a session."""
        # Create session
        create_response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={
                "num_games": 3,
                "dictionary_id": "dict_ro_basic",
                "difficulty": "normal",
                "language": "ro",
                "max_misses": 6,
                "allow_word_guess": True
            }
        )
        session_id = create_response.json()["session_id"]
        
        # Abort session
        response = client.post(
            f"/api/v1/sessions/{session_id}/abort",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ABORTED"
        assert data["message"] == "Session aborted successfully"
        
    def test_list_session_games(self, client, auth_headers):
        """Test listing games in a session."""
        # Create session
        create_response = client.post(
            "/api/v1/sessions",
            headers=auth_headers,
            json={
                "num_games": 5,
                "dictionary_id": "dict_ro_basic",
                "difficulty": "normal",
                "language": "ro",
                "max_misses": 6,
                "allow_word_guess": True
            }
        )
        session_id = create_response.json()["session_id"]
        
        # List games
        response = client.get(
            f"/api/v1/sessions/{session_id}/games",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "games" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
