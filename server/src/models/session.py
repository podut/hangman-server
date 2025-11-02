"""Session-related Pydantic models."""

from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from ..config import get_settings

settings = get_settings()


class CreateSessionRequest(BaseModel):
    num_games: int = 100
    dictionary_id: str = "dict_ro_basic"
    difficulty: Literal["easy", "normal", "hard", "auto"] = "auto"
    language: Literal["ro", "en"] = "ro"
    max_misses: int = settings.default_max_wrong_guesses
    allow_word_guess: bool = True
    seed: Optional[int] = None
    
    @field_validator("num_games")
    @classmethod
    def validate_num_games(cls, v: int) -> int:
        if v < 1:
            raise ValueError("num_games must be at least 1")
        if v > settings.max_games_per_session:
            raise ValueError(f"num_games cannot exceed {settings.max_games_per_session}")
        return v
    
    @field_validator("max_misses")
    @classmethod
    def validate_max_misses(cls, v: int) -> int:
        if v < 1:
            raise ValueError("max_misses must be at least 1")
        if v > 20:
            raise ValueError("max_misses cannot exceed 20")
        return v


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    num_games: int
    dictionary_id: str
    status: str
    created_at: str
    params: dict
