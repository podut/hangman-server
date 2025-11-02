"""Game repository: in-memory game storage."""

from typing import Dict, Optional, List


class GameRepository:
    """Repository for game data management."""
    
    def __init__(self):
        self._games: Dict[str, dict] = {}
        self._guesses: Dict[str, List[dict]] = {}
        
    def create(self, game_data: dict) -> dict:
        """Create a new game."""
        self._games[game_data["game_id"]] = game_data
        self._guesses[game_data["game_id"]] = []
        return game_data
        
    def get_by_id(self, game_id: str) -> Optional[dict]:
        """Get game by ID."""
        return self._games.get(game_id)
        
    def get_by_session(self, session_id: str) -> List[dict]:
        """Get all games for a session."""
        return [g for g in self._games.values() if g["session_id"] == session_id]
        
    def update(self, game_id: str, updates: dict) -> Optional[dict]:
        """Update game data."""
        if game_id in self._games:
            self._games[game_id].update(updates)
            return self._games[game_id]
        return None
        
    def add_guess(self, game_id: str, guess_data: dict) -> dict:
        """Add a guess to a game."""
        if game_id not in self._guesses:
            self._guesses[game_id] = []
        self._guesses[game_id].append(guess_data)
        return guess_data
        
    def get_guesses(self, game_id: str) -> List[dict]:
        """Get all guesses for a game."""
        return self._guesses.get(game_id, [])
        
    def get_all(self) -> List[dict]:
        """Get all games."""
        return list(self._games.values())
