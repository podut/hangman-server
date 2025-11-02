"""Game service: game management and guess processing."""

from datetime import datetime
from typing import Dict, Any, List, Optional
import random
from ..repositories.game_repository import GameRepository
from ..repositories.session_repository import SessionRepository
from ..repositories.dictionary_repository import DictionaryRepository
from ..utils.game_utils import normalize, update_pattern, calculate_score
from ..exceptions import (
    InvalidGuessException,
    GameAlreadyFinishedException,
    GameNotFoundException
)


class GameService:
    """Service for game operations."""
    
    def __init__(
        self,
        game_repo: GameRepository,
        session_repo: SessionRepository,
        dict_repo: DictionaryRepository
    ):
        self.game_repo = game_repo
        self.session_repo = session_repo
        self.dict_repo = dict_repo
        
    def create_game(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """Create a new game in a session."""
        session = self.session_repo.get_by_id(session_id)
        
        if not session:
            raise ValueError("Session not found")
            
        if session["user_id"] != user_id:
            raise PermissionError("Access denied")
            
        if session["games_created"] >= session["num_games"]:
            raise ValueError("Session game limit reached")
            
        # Get dictionary
        dict_id = session["params"].get("dictionary_id", "dict_ro_basic")
        dictionary = self.dict_repo.get_by_id(dict_id)
        
        if not dictionary:
            dict_id = "dict_ro_basic"
            dictionary = self.dict_repo.get_by_id(dict_id)
            
        available_words = dictionary["words"].copy()
        
        # Get words already used in this session
        session_games = self.game_repo.get_by_session(session_id)
        used_words = {game["secret"] for game in session_games}
        
        # Filter out used words
        available_words = [w for w in available_words if w not in used_words]
        
        if not available_words:
            raise ValueError("No more unique words available in dictionary")
            
        # Select random word
        rng = random.Random(session["params"].get("seed", None))
        secret = rng.choice(available_words)
        
        # Create game
        game_id = f"g_{self.game_repo.count() + 1}"
        
        game_data = {
            "game_id": game_id,
            "session_id": session_id,
            "status": "IN_PROGRESS",
            "secret": secret,
            "length": len(secret),
            "pattern": "*" * len(secret),
            "guessed_letters": [],
            "wrong_letters": [],
            "remaining_misses": session["params"]["max_misses"],
            "total_guesses": 0,
            "wrong_word_guesses": 0,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "finished_at": None,
            "time_seconds": 0.0,
            "composite_score": 0.0,
            "result": None
        }
        
        self.game_repo.create(game_data)
        
        # Update session
        self.session_repo.update(session_id, {
            "games_created": session["games_created"] + 1
        })
        
        # Return without secret
        return {k: v for k, v in game_data.items() if k != "secret"}
        
    def get_game(self, game_id: str, user_id: str) -> Dict[str, Any]:
        """Get game state (without secret for active games)."""
        game = self.game_repo.get_by_id(game_id)
        
        if not game:
            raise ValueError("Game not found")
            
        session = self.session_repo.get_by_id(game["session_id"])
        
        if session["user_id"] != user_id:
            raise PermissionError("Access denied")
        
        # Hide secret only for active games
        if game["status"] == "IN_PROGRESS":
            return {k: v for k, v in game.items() if k != "secret"}
        else:
            # Reveal secret for finished games
            return game
        
    def make_guess_letter(
        self,
        game_id: str,
        letter: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process a letter guess."""
        game = self.game_repo.get_by_id(game_id)
        
        if not game:
            raise ValueError("Game not found")
            
        session = self.session_repo.get_by_id(game["session_id"])
        
        if session["user_id"] != user_id:
            raise PermissionError("Access denied")
            
        if game["status"] != "IN_PROGRESS":
            raise GameAlreadyFinishedException(game_id, game["status"])
            
        letter = letter.strip().lower()
        
        if len(letter) != 1:
            raise InvalidGuessException("Must be a single letter")
            
        if letter in game["guessed_letters"]:
            raise InvalidGuessException("Letter has already been guessed")
            
        # Process guess
        game["guessed_letters"].append(letter)
        old_pattern = game["pattern"]
        game["pattern"] = update_pattern(game["secret"], game["pattern"], letter)
        correct = old_pattern != game["pattern"]
        
        if not correct:
            game["wrong_letters"].append(letter)
            game["remaining_misses"] -= 1
            
        game["total_guesses"] += 1
        
        # Add guess to history
        guess_data = {
            "index": len(self.game_repo.get_guesses(game_id)) + 1,
            "type": "LETTER",
            "value": letter,
            "correct": correct,
            "pattern_after": game["pattern"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.game_repo.add_guess(game_id, guess_data)
        
        # Check win/loss conditions
        if "*" not in game["pattern"]:
            game["status"] = "WON"
            game["finished_at"] = datetime.utcnow().isoformat() + "Z"
            game["result"] = {"won": True, "secret": game["secret"]}
        elif game["remaining_misses"] <= 0:
            game["status"] = "LOST"
            game["finished_at"] = datetime.utcnow().isoformat() + "Z"
            game["result"] = {"won": False, "secret": game["secret"]}
            
        game["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Calculate score if finished
        if game["status"] in ["WON", "LOST"]:
            self._calculate_final_score(game)
            
        # Update game
        self.game_repo.update(game_id, game)
        
        # Return game state with additional guess info
        return {
            "guess_index": guess_data["index"],
            "type": "LETTER",
            "value": letter,
            "correct": correct,
            "success": correct,  # Alias for tests
            "pattern": game["pattern"],
            "pattern_after": game["pattern"],
            "guessed_letters": game["guessed_letters"],
            "wrong_letters": game["wrong_letters"],
            "remaining_misses": game["remaining_misses"],
            "status": game["status"]
        }
        
    def make_guess_word(
        self,
        game_id: str,
        word: str,
        user_id: str
    ) -> Dict[str, Any]:
        """Process a word guess."""
        game = self.game_repo.get_by_id(game_id)
        
        if not game:
            raise ValueError("Game not found")
            
        session = self.session_repo.get_by_id(game["session_id"])
        
        if session["user_id"] != user_id:
            raise PermissionError("Access denied")
            
        if game["status"] != "IN_PROGRESS":
            raise GameAlreadyFinishedException(game_id, game["status"])
            
        if not session["params"]["allow_word_guess"]:
            raise InvalidGuessException("Word guessing not allowed")
            
        word = word.strip().lower()
        game["total_guesses"] += 1
        correct = normalize(word) == normalize(game["secret"])
        
        if correct:
            game["pattern"] = game["secret"]
            game["status"] = "WON"
            game["finished_at"] = datetime.utcnow().isoformat() + "Z"
            game["result"] = {"won": True, "secret": game["secret"]}
        else:
            game["wrong_word_guesses"] += 1
            game["remaining_misses"] -= 2
            if game["remaining_misses"] <= 0:
                game["status"] = "LOST"
                game["finished_at"] = datetime.utcnow().isoformat() + "Z"
                game["result"] = {"won": False, "secret": game["secret"]}
                
        # Add guess to history
        guess_data = {
            "index": len(self.game_repo.get_guesses(game_id)) + 1,
            "type": "WORD",
            "value": word,
            "correct": correct,
            "pattern_after": game["pattern"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.game_repo.add_guess(game_id, guess_data)
        
        game["updated_at"] = datetime.utcnow().isoformat() + "Z"
        
        # Calculate score if finished
        if game["status"] in ["WON", "LOST"]:
            self._calculate_final_score(game)
            
        # Update game
        self.game_repo.update(game_id, game)
        
        return {
            "guess_index": guess_data["index"],
            "type": "WORD",
            "value": word,
            "correct": correct,
            "success": correct,  # Alias for tests
            "pattern": game["pattern"],
            "pattern_after": game["pattern"],
            "wrong_word_guesses": game["wrong_word_guesses"],
            "remaining_misses": game["remaining_misses"],
            "status": game["status"]
        }
        
    def abort_game(self, game_id: str, user_id: str) -> Dict[str, Any]:
        """Abort an active game."""
        game = self.game_repo.get_by_id(game_id)
        
        if not game:
            raise ValueError("Game not found")
            
        session = self.session_repo.get_by_id(game["session_id"])
        
        if session["user_id"] != user_id:
            raise PermissionError("Access denied")
            
        if game["status"] != "IN_PROGRESS":
            raise ValueError("Game is not in progress")
            
        game["status"] = "ABORTED"
        game["finished_at"] = datetime.utcnow().isoformat() + "Z"
        game["result"] = {"won": False, "secret": game["secret"], "aborted": True}
        
        self.game_repo.update(game_id, game)
        
        return {k: v for k, v in game.items() if k != "secret"}
        
    def list_session_games(
        self,
        session_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """List games in a session with pagination."""
        session = self.session_repo.get_by_id(session_id)
        
        if not session:
            raise ValueError("Session not found")
            
        if session["user_id"] != user_id:
            raise PermissionError("Access denied")
            
        all_games = self.game_repo.get_by_session(session_id)
        
        # Pagination
        total = len(all_games)
        start = (page - 1) * page_size
        end = start + page_size
        games = all_games[start:end]
        
        # Remove secret from response
        games_safe = [{k: v for k, v in g.items() if k != "secret"} for g in games]
        
        return {
            "games": games_safe,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
        
    def _calculate_final_score(self, game: dict):
        """Calculate composite score for finished game."""
        created = datetime.fromisoformat(game["created_at"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(game["finished_at"].replace("Z", "+00:00"))
        game["time_seconds"] = (finished - created).total_seconds()
        
        won = 1 if game["status"] == "WON" else 0
        game["composite_score"] = calculate_score(
            won=won,
            total_guesses=game["total_guesses"],
            wrong_letters=len(game["wrong_letters"]),
            wrong_word_guesses=game["wrong_word_guesses"],
            time_sec=game["time_seconds"],
            length=game["length"]
        )

    def count(self) -> int:
        """Count total games (helper for ID generation)."""
        return len(self.game_repo.get_all())
