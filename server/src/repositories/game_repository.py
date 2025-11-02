"""Game repository: in-memory game storage."""

from typing import Dict, Optional, List
from copy import deepcopy


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
        game = self._games.get(game_id)
        return deepcopy(game) if game else None
        
    def get_by_session(self, session_id: str) -> List[dict]:
        """Get all games for a session."""
        return [deepcopy(g) for g in self._games.values() if g["session_id"] == session_id]
        
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
        
    def count(self) -> int:
        """Get total number of games."""
        return len(self._games)
    
    def delete(self, game_id: str) -> bool:
        """Delete game by ID. Returns True if deleted, False if not found."""
        if game_id in self._games:
            del self._games[game_id]
            if game_id in self._guesses:
                del self._guesses[game_id]
            return True
        return False
    
    def delete_by_session(self, session_id: str) -> int:
        """Delete all games for a session. Returns number of games deleted."""
        games_to_delete = [gid for gid, g in self._games.items() if g["session_id"] == session_id]
        for game_id in games_to_delete:
            del self._games[game_id]
            if game_id in self._guesses:
                del self._guesses[game_id]
        return len(games_to_delete)
    
    def delete_by_user(self, user_id: str, session_ids: list) -> int:
        """Delete all games for a user via session IDs. Returns number of games deleted."""
        count = 0
        for session_id in session_ids:
            count += self.delete_by_session(session_id)
        return count
