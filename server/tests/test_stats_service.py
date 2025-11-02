"""
Unit tests for StatsService.
Tests user statistics, global statistics, and leaderboard.
"""

import pytest


@pytest.mark.unit
class TestStatsServiceUserStats:
    """Test user statistics functionality."""
    
    def test_get_user_stats_no_games(self, stats_service, created_user):
        """Test getting stats for user with no games."""
        result = stats_service.get_user_stats(
            user_id=created_user["user_id"],
            period="all"
        )
        
        assert result["user_id"] == created_user["user_id"]
        assert result["total_games"] == 0
        assert result["games_won"] == 0
        assert result["games_lost"] == 0
        assert result["win_rate"] == 0.0
        assert result["avg_score"] == 0.0
        
    def test_get_user_stats_with_won_game(
        self, stats_service, game_service, created_game, created_user
    ):
        """Test getting stats after winning a game."""
        # Win the game
        game_service.make_guess_word(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"],
            word=created_game["secret"]
        )
        
        result = stats_service.get_user_stats(
            user_id=created_user["user_id"],
            period="all"
        )
        
        assert result["total_games"] == 1
        assert result["games_won"] == 1
        assert result["games_lost"] == 0
        assert result["win_rate"] == 100.0
        assert result["avg_score"] > 0
        
    def test_get_user_stats_with_lost_game(
        self, stats_service, game_service, created_game, created_user
    ):
        """Test getting stats after losing a game."""
        # Make wrong guesses until game is lost
        # Use a longer list of unlikely letters to ensure we have enough wrong guesses
        unlikely_letters = "qxzjkvwfb"
        for i, letter in enumerate(unlikely_letters):
            try:
                result = game_service.make_guess_letter(
                    game_id=created_game["game_id"],
                    user_id=created_user["user_id"],
                    letter=letter
                )
                # Stop if game is finished
                if result["status"] in ["WON", "LOST"]:
                    break
            except Exception:
                break
                
        result = stats_service.get_user_stats(
            user_id=created_user["user_id"],
            period="all"
        )
        
        assert result["total_games"] >= 1
        assert result["games_lost"] >= 1
        
    def test_get_user_stats_mixed_results(
        self, stats_service, game_service, session_service, 
        created_user, sample_session_params
    ):
        """Test stats with multiple games."""
        # Create session with multiple games
        session = session_service.create_session(
            user_id=created_user["user_id"],
            num_games=3,
            dictionary_id="dict_ro_basic", difficulty="medium", language="ro", max_misses=6, allow_word_guess=True, seed=None
        )
        
        # Create and win first game
        game1 = game_service.create_game(
            session_id=session["session_id"],
            user_id=created_user["user_id"]
        )
        # Get secret from mock repo since create_game doesn't return it
        game1_full = game_service.game_repo.get_by_id(game1["game_id"])
        game_service.make_guess_word(
            game_id=game1["game_id"],
            user_id=created_user["user_id"],
            word=game1_full["secret"]
        )
        
        # Create and abort second game
        game2 = game_service.create_game(
            session_id=session["session_id"],
            user_id=created_user["user_id"]
        )
        game_service.abort_game(
            game_id=game2["game_id"],
            user_id=created_user["user_id"]
        )
        
        result = stats_service.get_user_stats(
            user_id=created_user["user_id"],
            period="all"
        )
        
        assert result["total_games"] == 2
        assert result["games_won"] == 1
        assert result["games_aborted"] == 1


@pytest.mark.unit
class TestStatsServiceGlobalStats:
    """Test global statistics functionality."""
    
    def test_get_global_stats_no_games(self, stats_service):
        """Test global stats with no games."""
        result = stats_service.get_global_stats()
        
        assert result["total_games"] == 0
        assert result["total_users"] >= 0
        
    def test_get_global_stats_with_games(
        self, stats_service, game_service, created_game, created_user
    ):
        """Test global stats after games are played."""
        # Win a game
        game_service.make_guess_word(
            game_id=created_game["game_id"],
            user_id=created_user["user_id"],
            word=created_game["secret"]
        )
        
        result = stats_service.get_global_stats()
        
        assert result["total_games"] >= 1
        assert result["total_users"] >= 1


@pytest.mark.unit
class TestStatsServiceLeaderboard:
    """Test leaderboard functionality."""
    
    def test_get_leaderboard_empty(self, stats_service):
        """Test leaderboard with no completed games."""
        result = stats_service.get_leaderboard(limit=10)
        
        assert isinstance(result, list)
        assert len(result) == 0
        
    def test_get_leaderboard_with_players(
        self, stats_service, game_service, auth_service,
        session_service, sample_session_params
    ):
        """Test leaderboard with multiple players."""
        # Create two users
        user1 = auth_service.register_user(
            email="player1@example.com",
            password="Pass123!"
        )
        user2 = auth_service.register_user(
            email="player2@example.com",
            password="Pass123!"
        )
        
        # Create sessions and games for both users
        for user in [user1, user2]:
            session = session_service.create_session(
                user_id=user["user_id"],
                num_games=1,
                dictionary_id="dict_ro_basic", difficulty="medium", language="ro", max_misses=6, allow_word_guess=True, seed=None
            )
            game = game_service.create_game(
                session_id=session["session_id"],
                user_id=user["user_id"]
            )
            # Get secret from mock repo since create_game doesn't return it
            game_full = game_service.game_repo.get_by_id(game["game_id"])
            game_service.make_guess_word(
                game_id=game["game_id"],
                user_id=user["user_id"],
                word=game_full["secret"]
            )
        
        result = stats_service.get_leaderboard(limit=10)
        
        assert len(result) >= 2
        assert all("user_id" in entry for entry in result)
        assert all("total_score" in entry for entry in result)
        # Check that leaderboard is sorted by score (descending)
        if len(result) > 1:
            assert result[0]["total_score"] >= result[1]["total_score"]
            
    def test_get_leaderboard_respects_limit(
        self, stats_service, game_service, auth_service,
        session_service, sample_session_params
    ):
        """Test that leaderboard respects limit parameter."""
        # Create 3 users with games
        for i in range(3):
            user = auth_service.register_user(
                email=f"player{i}@example.com",
                password="Pass123!"
            )
            session = session_service.create_session(
                user_id=user["user_id"],
                num_games=1,
                dictionary_id="dict_ro_basic", difficulty="medium", language="ro", max_misses=6, allow_word_guess=True, seed=None
            )
            game = game_service.create_game(
                session_id=session["session_id"],
                user_id=user["user_id"]
            )
            # Get secret from mock repo since create_game doesn't return it
            game_full = game_service.game_repo.get_by_id(game["game_id"])
            game_service.make_guess_word(
                game_id=game["game_id"],
                user_id=user["user_id"],
                word=game_full["secret"]
            )
        
        result = stats_service.get_leaderboard(limit=2)
        
        assert len(result) <= 2

