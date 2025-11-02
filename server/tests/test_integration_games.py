"""
Integration tests for Game endpoints.
Tests the full HTTP request/response cycle for game management and gameplay.
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
    """Provide authentication headers with a valid token."""
    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "gametest@example.com",
            "password": "GameTest123!"
        }
    )
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "gametest@example.com",
            "password": "GameTest123!"
        }
    )
    
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def session_id(client, auth_headers):
    """Create a session and return its ID."""
    response = client.post(
        "/api/v1/sessions",
        headers=auth_headers,
        json={
            "num_games": 10,
            "dictionary_id": "dict_ro_basic",
            "difficulty": "easy",
            "language": "ro",
            "max_misses": 6,
            "allow_word_guess": True
        }
    )
    return response.json()["session_id"]


@pytest.mark.integration
class TestGameEndpoints:
    """Test game CRUD and gameplay endpoints."""
    
    def test_create_game_success(self, client, auth_headers, session_id):
        """Test creating a new game."""
        response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "game_id" in data
        assert "pattern" in data
        assert "status" in data
        assert data["status"] == "IN_PROGRESS"
        assert data["remaining_misses"] > 0
        
    def test_create_game_session_not_found(self, client, auth_headers):
        """Test creating game with non-existent session."""
        response = client.post(
            "/api/v1/sessions/nonexistent/games",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error_code" in data
        
    def test_get_game_state(self, client, auth_headers, session_id):
        """Test retrieving game state."""
        # Create game
        create_response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=auth_headers
        )
        game_id = create_response.json()["game_id"]
        
        # Get game state
        response = client.get(
            f"/api/v1/sessions/{session_id}/games/{game_id}/state",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["game_id"] == game_id
        assert "pattern" in data
        assert "guessed_letters" in data
        assert "remaining_misses" in data
        
    def test_make_guess_letter_correct(self, client, auth_headers, session_id):
        """Test making a correct letter guess."""
        # Create game
        create_response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=auth_headers
        )
        game_id = create_response.json()["game_id"]
        pattern = create_response.json()["pattern"]
        
        # Try common letters until we find one in the word
        for letter in "aeiou":
            response = client.post(
                f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
                headers=auth_headers,
                json={"letter": letter}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("correct"):
                    # Found a correct letter
                    assert data["pattern"] != pattern
                    assert letter in data["guessed_letters"]
                    break
                    
    def test_make_guess_letter_incorrect(self, client, auth_headers, session_id):
        """Test making an incorrect letter guess."""
        # Create game
        create_response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=auth_headers
        )
        game_id = create_response.json()["game_id"]
        initial_misses = create_response.json()["remaining_misses"]
        
        # Try letters until we find an incorrect one
        for letter in "xyz":
            response = client.post(
                f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
                headers=auth_headers,
                json={"letter": letter}
            )
            
            if response.status_code == 200:
                data = response.json()
                if not data.get("correct"):
                    # Found an incorrect letter
                    assert data["remaining_misses"] < initial_misses
                    assert letter in data["guessed_letters"]
                    break
                    
    def test_make_guess_already_guessed(self, client, auth_headers, session_id):
        """Test guessing the same letter twice."""
        # Create game
        create_response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=auth_headers
        )
        game_id = create_response.json()["game_id"]
        
        # Make first guess
        client.post(
            f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
            headers=auth_headers,
            json={"letter": "a"}
        )
        
        # Try same letter again
        response = client.post(
            f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
            headers=auth_headers,
            json={"letter": "a"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error_code" in data
        
    def test_make_guess_invalid_format(self, client, auth_headers, session_id):
        """Test making guess with invalid letter format."""
        # Create game
        create_response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=auth_headers
        )
        game_id = create_response.json()["game_id"]
        
        # Try invalid guess (multiple letters)
        response = client.post(
            f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
            headers=auth_headers,
            json={"letter": "abc"}
        )
        
        assert response.status_code == 400
        
    def test_make_guess_word(self, client, auth_headers, session_id):
        """Test making a word guess."""
        # Create game
        create_response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=auth_headers
        )
        game_id = create_response.json()["game_id"]
        
        # Try word guess (will likely be wrong unless we're lucky)
        response = client.post(
            f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
            headers=auth_headers,
            json={"word": "test"}
        )
        
        # Should succeed (even if wrong), not validation error
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        
    def test_abort_game(self, client, auth_headers, session_id):
        """Test aborting a game."""
        # Create game
        create_response = client.post(
            f"/api/v1/sessions/{session_id}/games",
            headers=auth_headers
        )
        game_id = create_response.json()["game_id"]
        
        # Abort game
        response = client.post(
            f"/api/v1/sessions/{session_id}/games/{game_id}/abort",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ABORTED"
        assert data["message"] == "Game aborted successfully"
        
    def test_game_not_found(self, client, auth_headers, session_id):
        """Test accessing non-existent game."""
        response = client.get(
            f"/api/v1/sessions/{session_id}/games/nonexistent/state",
            headers=auth_headers
        )
        
        assert response.status_code == 404
