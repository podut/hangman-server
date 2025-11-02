"""Session-related Pydantic models."""

from pydantic import BaseModel
from typing import Optional, Literal


class CreateSessionRequest(BaseModel):
    num_games: int = 100
    dictionary_id: str = "dict_ro_basic"
    difficulty: Literal["easy", "normal", "hard", "auto"] = "auto"
    language: Literal["ro", "en"] = "ro"
    max_misses: int = 6
    allow_word_guess: bool = True
    seed: Optional[int] = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    num_games: int
    dictionary_id: str
    status: str
    created_at: str
    params: dict
