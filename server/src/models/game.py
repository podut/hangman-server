"""Game-related Pydantic models."""

from pydantic import BaseModel
from typing import Optional, List


class GuessRequest(BaseModel):
    letter: Optional[str] = None
    word: Optional[str] = None


class GuessResponse(BaseModel):
    guess_index: int
    type: str
    value: str
    correct: bool
    pattern_after: str
    remaining_misses: int
    status: str


class GameResponse(BaseModel):
    game_id: str
    session_id: str
    status: str
    pattern: str
    guessed_letters: List[str]
    wrong_letters: List[str]
    remaining_misses: int
    total_guesses: int
    created_at: str
    finished_at: Optional[str] = None
    result: Optional[dict] = None
