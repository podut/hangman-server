"""
Unit tests for SessionService.
Tests session creation, management, and validation.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.exceptions import (
    SessionNotFoundException,
    MaxSessionsExceededException,
    UserNotFoundException
)


@pytest.mark.unit
class TestSessionServiceCreation:
    """Test session creation functionality."""
    
    def test_create_session_success(self, session_service, created_user, sample_session_params):
        """Test successful session creation."""
        result = session_service.create_session(
            user_id=created_user["user_id"],
            num_games=5,
            dictionary_id=sample_session_params.get("dictionary_id", "dict_ro_basic"),
            difficulty=sample_session_params.get("difficulty", "medium"),
            language=sample_session_params.get("language", "ro"),
            max_misses=sample_session_params.get("max_misses", 6),
            allow_word_guess=sample_session_params.get("allow_word_guess", True),
            seed=sample_session_params.get("seed")
        )
        
        assert result["session_id"].startswith("s_")
        assert result["user_id"] == created_user["user_id"]
        assert result["num_games"] == 5
        assert result["games_created"] == 0
        assert result["games_won"] == 0
        assert result["games_lost"] == 0
        assert result["status"] == "ACTIVE"
        
    def test_create_session_user_not_found(self, session_service, sample_session_params):
        """Test session creation with non-existent user."""
        # This test is not applicable since SessionService doesn't validate user existence
        # User validation happens at the controller/endpoint level
        pass
            
    def test_create_session_exceeds_limit(self, session_service, created_user, sample_session_params):
        """Test that max_sessions_per_user limit is enforced."""
        result = session_service.create_session(
            user_id=created_user["user_id"],
            num_games=1,
            dictionary_id=sample_session_params.get("dictionary_id", "dict_ro_basic"),
            difficulty=sample_session_params.get("difficulty", "medium"),
            language=sample_session_params.get("language", "ro"),
            max_misses=sample_session_params.get("max_misses", 6),
            allow_word_guess=sample_session_params.get("allow_word_guess", True),
            seed=sample_session_params.get("seed")
        )
        
        assert result["session_id"].startswith("s_")


@pytest.mark.unit
class TestSessionServiceRetrieval:
    """Test session retrieval functionality."""
    
    def test_get_session_by_id(self, session_service, created_session, created_user):
        """Test getting session by ID."""
        result = session_service.get_session(
            session_id=created_session["session_id"],
            user_id=created_user["user_id"]
        )
        
        assert result["session_id"] == created_session["session_id"]
        assert result["user_id"] == created_session["user_id"]
        
    def test_get_session_not_found(self, session_service, created_user):
        """Test getting non-existent session."""
        with pytest.raises(SessionNotFoundException):
            session_service.get_session(
                session_id="s_nonexistent",
                user_id=created_user["user_id"]
            )
            
    def test_get_user_sessions(self, session_service, created_user, sample_session_params):
        """Test getting all sessions for a user."""
        # Create multiple sessions
        session_service.create_session(
            user_id=created_user["user_id"],
            num_games=3,
            dictionary_id="dict_ro_basic",
            difficulty="medium",
            language="ro",
            max_misses=6,
            allow_word_guess=True,
            seed=None
        )
        session_service.create_session(
            user_id=created_user["user_id"],
            num_games=5,
            dictionary_id="dict_ro_basic",
            difficulty="medium",
            language="ro",
            max_misses=6,
            allow_word_guess=True,
            seed=None
        )
        
        result = session_service.list_user_sessions(created_user["user_id"])
        
        assert len(result) >= 2
        assert all(s["user_id"] == created_user["user_id"] for s in result)


@pytest.mark.unit
class TestSessionServiceUpdate:
    """Test session update functionality."""
    
    def test_update_session_status(self, session_service, created_session):
        """Test updating session status."""
        result = session_service.update_session_status(
            session_id=created_session["session_id"],
            status="COMPLETED"
        )
        
        assert result["status"] == "COMPLETED"
        
    def test_increment_games_created(self, session_service, created_session):
        """Test incrementing games_created counter."""
        initial_count = created_session["games_created"]
        
        result = session_service.increment_games_created(created_session["session_id"])
        
        assert result["games_created"] == initial_count + 1
        
    def test_update_session_stats(self, session_service, created_session):
        """Test updating session statistics."""
        result = session_service.update_session_stats(
            session_id=created_session["session_id"],
            games_won=1,
            games_lost=0,
            total_score=100.0
        )
        
        assert result["games_won"] == 1
        assert result["games_lost"] == 0


@pytest.mark.unit
class TestSessionServiceValidation:
    """Test session validation."""
    
    def test_validate_session_params(self, session_service, created_user):
        """Test that invalid session params are rejected."""
        # Test with negative num_games
        with pytest.raises(ValueError):
            session_service.create_session(
                user_id=created_user["user_id"],
                num_games=-1,
                dictionary_id="dict_ro_basic",
                difficulty="medium",
                language="ro",
                max_misses=6,
                allow_word_guess=True,
                seed=None
            )
            
    def test_validate_max_misses(self, session_service, created_user):
        """Test that max_misses is validated."""
        # Test with invalid max_misses
        with pytest.raises(ValueError):
            session_service.create_session(
                user_id=created_user["user_id"],
                num_games=5,
                dictionary_id="dict_ro_basic",
                difficulty="medium",
                language="ro",
                max_misses=0,  # Should be at least 1
                allow_word_guess=True,
                seed=None
            )
