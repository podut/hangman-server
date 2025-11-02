"""
Unit tests for GameService.
Tests game creation, guess processing, game state management.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.exceptions import (
    SessionNotFoundException,
    GameNotFoundException,
    GameAlreadyFinishedException,
    InvalidGuessException,
    GameAccessDeniedException
)


@pytest.mark.unit
class TestGameServiceCreation:
    """Test game creation functionality."""
    
    def test_create_game_success(self, game_service, created_session, created_user):
        """Test successful game creation."""
        result = game_service.create_game(
            session_id=created_session["session_id"],
            user_id=created_user["user_id"]
        )
        
        assert result["game_id"].startswith("g_")
        assert result["session_id"] == created_session["session_id"]
        assert result["status"] == "IN_PROGRESS"
        assert "secret" not in result  # Secret is hidden during active game
        assert result["length"] > 0
        assert result["pattern"] == "*" * result["length"]
        assert result["guessed_letters"] == []
        assert result["wrong_letters"] == []
        assert result["remaining_misses"] == created_session["params"]["max_misses"]
        assert result["total_guesses"] == 0
        
    def test_create_game_session_not_found(self, game_service, created_user):
        """Test game creation with non-existent session."""
        with pytest.raises(ValueError, match="Session not found"):
            game_service.create_game(
                session_id="s_nonexistent",
                user_id=created_user["user_id"]
            )
            
    def test_create_game_permission_denied(self, game_service, created_session, auth_service):
        """Test game creation with wrong user."""
        # Create another user
        other_user = auth_service.register_user(
            email="other@example.com",
            password="OtherPass123!"
        )
        
        with pytest.raises(PermissionError, match="Access denied"):
            game_service.create_game(
                session_id=created_session["session_id"],
                user_id=other_user["user_id"]
            )
            
    def test_create_game_exceeds_limit(self, game_service, session_service, created_user, sample_session_params):
        """Test game creation when session limit reached."""
        # Create session with limit of 1 game
        session = session_service.create_session(
            user_id=created_user["user_id"],
            num_games=1,
            dictionary_id="dict_ro_basic",
            difficulty="medium",
            language="ro",
            max_misses=6,
            allow_word_guess=True,
            seed=None
        )
        
        # Create first game (should succeed)
        game_service.create_game(
            session_id=session["session_id"],
            user_id=created_user["user_id"]
        )
        
        # Try to create second game (should fail)
        with pytest.raises(ValueError, match="Session game limit reached"):
            game_service.create_game(
                session_id=session["session_id"],
                user_id=created_user["user_id"]
            )


@pytest.mark.unit
class TestGameServiceGuesses:
    """Test guess processing functionality."""
    
    def test_guess_letter_correct(self, game_service, created_game, created_user):
        """Test correct letter guess."""
        # Get the secret word and pick first letter
        secret = created_game["secret"]
        letter = secret[0].lower()
        
        result = game_service.make_guess_letter(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"],
            letter=letter
        )
        
        assert result["success"] is True
        assert letter in result["guessed_letters"]
        assert result["remaining_misses"] == created_game["remaining_misses"]
        assert result["pattern"] != "*" * len(secret)
        
    def test_guess_letter_incorrect(self, game_service, created_game, created_user):
        """Test incorrect letter guess."""
        # Find a letter not in the secret word
        secret = created_game["secret"]
        wrong_letter = next(c for c in "qxz" if c not in secret.lower())
        
        result = game_service.make_guess_letter(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"],
            letter=wrong_letter
        )
        
        assert result["success"] is False
        assert wrong_letter in result["wrong_letters"]
        assert result["remaining_misses"] == created_game["remaining_misses"] - 1
        
    def test_guess_letter_already_guessed(self, game_service, created_game, created_user):
        """Test guessing same letter twice."""
        letter = created_game["secret"][0].lower()
        
        # First guess
        game_service.make_guess_letter(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"],
            letter=letter
        )
        
        # Second guess (same letter)
        with pytest.raises(InvalidGuessException, match="already been guessed"):
            game_service.make_guess_letter(
                game_id=created_game["game_id"],
                user_id=created_user["user_id"],
                letter=letter
            )
            
    def test_guess_letter_invalid_format(self, game_service, created_game, created_user):
        """Test guessing with invalid letter format."""
        with pytest.raises(InvalidGuessException, match="single letter"):
            game_service.make_guess_letter(
                game_id=created_game["game_id"],
                user_id=created_user["user_id"],
                letter="ab"  # Multiple letters
            )
            
    def test_guess_word_correct(self, game_service, created_game, created_user):
        """Test correct word guess."""
        result = game_service.make_guess_word(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"],
            word=created_game["secret"]
        )
        
        assert result["success"] is True
        assert result["status"] == "WON"
        assert result["pattern"] == created_game["secret"]
        
    def test_guess_word_incorrect(self, game_service, created_game, created_user):
        """Test incorrect word guess."""
        result = game_service.make_guess_word(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"],
            word="wrongword"
        )
        
        assert result["success"] is False
        assert result["wrong_word_guesses"] == 1
        assert result["status"] == "IN_PROGRESS"
        
    def test_guess_on_finished_game(self, game_service, created_game, created_user):
        """Test guessing on already finished game."""
        # Win the game
        game_service.make_guess_word(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"],
            word=created_game["secret"]
        )
        
        # Try to guess again
        with pytest.raises(GameAlreadyFinishedException):
            game_service.make_guess_letter(
                game_id=created_game["game_id"],
                user_id=created_user["user_id"],
                letter="a"
            )


@pytest.mark.unit
class TestGameServiceStateManagement:
    """Test game state management."""
    
    def test_get_game_state(self, game_service, created_game, created_user):
        """Test getting game state."""
        result = game_service.get_game(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"]
        )
        
        assert result["game_id"] == created_game["game_id"]
        assert result["status"] == "IN_PROGRESS"
        assert "pattern" in result
        assert "secret" not in result  # Secret should be hidden
        
    def test_get_game_state_finished_reveals_secret(self, game_service, created_game, created_user):
        """Test that finished game reveals secret."""
        # Win the game
        game_service.make_guess_word(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"],
            word=created_game["secret"]
        )
        
        # Get state
        result = game_service.get_game(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"]
        )
        
        assert result["secret"] == created_game["secret"]
        
    def test_abort_game(self, game_service, created_game, created_user):
        """Test aborting a game."""
        result = game_service.abort_game(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"]
        )
        
        assert result["status"] == "ABORTED"
        assert result["finished_at"] is not None
        
    def test_get_session_games(self, game_service, created_session, created_user):
        """Test getting all games in a session."""
        # Create multiple games
        game_service.create_game(
            session_id=created_session["session_id"],
            user_id=created_user["user_id"]
        )
        game_service.create_game(
            session_id=created_session["session_id"],
            user_id=created_user["user_id"]
        )
        
        result = game_service.list_session_games(
            session_id=created_session["session_id"],
            user_id=created_user["user_id"]
        )
        
        assert len(result["games"]) == 2
        assert all(g["session_id"] == created_session["session_id"] for g in result["games"])

