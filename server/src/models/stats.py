"""Statistics-related Pydantic models."""

from pydantic import BaseModel
from typing import Optional


class UserStats(BaseModel):
    user_id: str
    total_games: int
    games_won: int
    games_lost: int
    games_aborted: int
    win_rate: float
    avg_guesses: float
    avg_score: float
    best_score: float
    total_time_sec: float


class GlobalStats(BaseModel):
    total_users: int
    total_sessions: int
    total_games: int
    games_won: int
    games_lost: int
    games_aborted: int
    avg_game_duration_sec: float
    most_active_user: Optional[str] = None


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    nickname: Optional[str] = None
    total_games: int
    games_won: int
    win_rate: float
    avg_score: float
    composite_score: float
