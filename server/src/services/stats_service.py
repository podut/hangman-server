"""Statistics service: user stats, global stats, leaderboard."""

from datetime import datetime, timedelta
from typing import Dict, Any, List
from ..repositories.user_repository import UserRepository
from ..repositories.session_repository import SessionRepository
from ..repositories.game_repository import GameRepository


class StatsService:
    """Service for statistics operations."""
    
    def __init__(
        self,
        user_repo: UserRepository,
        session_repo: SessionRepository,
        game_repo: GameRepository
    ):
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.game_repo = game_repo
        
    def get_user_stats(self, user_id: str, period: str = "all") -> Dict[str, Any]:
        """Get statistics for a specific user."""
        # Get all games for user
        user_games = []
        for game in self.game_repo.get_all():
            if game["status"] not in ["WON", "LOST", "ABORTED"]:
                continue
            session = self.session_repo.get_by_id(game["session_id"])
            if session and session["user_id"] == user_id:
                user_games.append(game)
                
        # Filter by period
        user_games = self._filter_by_period(user_games, period)
        
        if not user_games:
            return {
                "user_id": user_id,
                "period": period,
                "total_games": 0,
                "games_won": 0,
                "games_lost": 0,
                "games_aborted": 0,
                "win_rate": 0.0,
                "avg_guesses": 0.0,
                "avg_score": 0.0,
                "best_score": 0.0,
                "total_time_sec": 0.0
            }
            
        wins = sum(1 for g in user_games if g["status"] == "WON")
        losses = sum(1 for g in user_games if g["status"] == "LOST")
        aborted = sum(1 for g in user_games if g["status"] == "ABORTED")
        
        finished_games = [g for g in user_games if g["status"] in ["WON", "LOST"]]
        
        total_score = sum(g.get("composite_score", 0) for g in finished_games)
        total_time = sum(g.get("time_seconds", 0) for g in finished_games)
        total_guesses = sum(g["total_guesses"] for g in finished_games)
        
        scores = [g.get("composite_score", 0) for g in finished_games if g.get("composite_score")]
        best_score = max(scores) if scores else 0.0
        
        return {
            "user_id": user_id,
            "period": period,
            "total_games": len(user_games),
            "games_won": wins,
            "games_lost": losses,
            "games_aborted": aborted,
            "win_rate": (wins / len(finished_games) * 100) if finished_games else 0.0,
            "avg_guesses": total_guesses / len(finished_games) if finished_games else 0.0,
            "avg_score": total_score / len(finished_games) if finished_games else 0.0,
            "best_score": best_score,
            "total_time_sec": total_time
        }
        
    def get_global_stats(self, period: str = "all") -> Dict[str, Any]:
        """Get global statistics across all users."""
        all_games = [g for g in self.game_repo.get_all() if g["status"] in ["WON", "LOST", "ABORTED"]]
        all_games = self._filter_by_period(all_games, period)
        
        if not all_games:
            return {
                "period": period,
                "total_users": 0,
                "total_sessions": 0,
                "total_games": 0,
                "games_won": 0,
                "games_lost": 0,
                "games_aborted": 0,
                "avg_game_duration_sec": 0.0,
                "most_active_user": None
            }
            
        wins = sum(1 for g in all_games if g["status"] == "WON")
        losses = sum(1 for g in all_games if g["status"] == "LOST")
        aborted = sum(1 for g in all_games if g["status"] == "ABORTED")
        
        finished_games = [g for g in all_games if g["status"] in ["WON", "LOST"]]
        total_duration = sum(g.get("time_seconds", 0) for g in finished_games)
        
        # Find most active user
        user_game_counts = {}
        for game in all_games:
            session = self.session_repo.get_by_id(game["session_id"])
            if session:
                user_id = session["user_id"]
                user_game_counts[user_id] = user_game_counts.get(user_id, 0) + 1
                
        most_active = max(user_game_counts, key=user_game_counts.get) if user_game_counts else None
        
        # Count unique users and sessions
        unique_sessions = set(g["session_id"] for g in all_games)
        unique_users = set()
        for sess_id in unique_sessions:
            session = self.session_repo.get_by_id(sess_id)
            if session:
                unique_users.add(session["user_id"])
        
        return {
            "period": period,
            "total_users": len(unique_users),
            "total_sessions": len(unique_sessions),
            "total_games": len(all_games),
            "games_won": wins,
            "games_lost": losses,
            "games_aborted": aborted,
            "avg_game_duration_sec": total_duration / len(finished_games) if finished_games else 0.0,
            "most_active_user": most_active
        }
        
    def get_leaderboard(
        self,
        metric: str = "composite_score",
        period: str = "all",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get leaderboard of top players."""
        # Get all games
        all_games = [g for g in self.game_repo.get_all() if g["status"] in ["WON", "LOST"]]
        all_games = self._filter_by_period(all_games, period)
        
        if not all_games:
            return []
            
        # Aggregate stats per user
        user_stats = {}
        for game in all_games:
            session = self.session_repo.get_by_id(game["session_id"])
            if not session:
                continue
                
            user_id = session["user_id"]
            
            if user_id not in user_stats:
                user = self.user_repo.get_by_id(user_id)
                user_stats[user_id] = {
                    "user_id": user_id,
                    "nickname": user.get("nickname") if user else None,
                    "total_games": 0,
                    "games_won": 0,
                    "total_score": 0.0,
                    "scores": []
                }
                
            user_stats[user_id]["total_games"] += 1
            if game["status"] == "WON":
                user_stats[user_id]["games_won"] += 1
                
            score = game.get("composite_score", 0)
            user_stats[user_id]["total_score"] += score
            user_stats[user_id]["scores"].append(score)
            
        # Calculate metrics
        entries = []
        for user_id, stats in user_stats.items():
            avg_score = stats["total_score"] / stats["total_games"] if stats["total_games"] else 0
            win_rate = stats["games_won"] / stats["total_games"] if stats["total_games"] else 0
            
            entries.append({
                "user_id": user_id,
                "nickname": stats["nickname"],
                "total_games": stats["total_games"],
                "games_won": stats["games_won"],
                "win_rate": win_rate,
                "avg_score": avg_score,
                "total_score": stats["total_score"]  # Total score for sorting
            })
            
        # Sort by metric
        if metric == "total_score":
            entries.sort(key=lambda x: x["total_score"], reverse=True)
        elif metric == "win_rate":
            entries.sort(key=lambda x: (x["win_rate"], x["total_games"]), reverse=True)
        elif metric == "total_games":
            entries.sort(key=lambda x: x["total_games"], reverse=True)
        else:
            # Default to total_score
            entries.sort(key=lambda x: x["total_score"], reverse=True)
            
        # Add rank and limit
        for i, entry in enumerate(entries[:limit], 1):
            entry["rank"] = i
            
        return entries[:limit]
        
    def get_admin_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for admin dashboard."""
        # Total users
        all_users = self.user_repo.get_all()
        total_users = len(all_users)
        admin_users = sum(1 for u in all_users if u.get("is_admin", False))
        
        # All sessions
        all_sessions = self.session_repo.get_all()
        total_sessions = len(all_sessions)
        active_sessions = sum(1 for s in all_sessions if s["status"] == "ACTIVE")
        
        # All games
        all_games = self.game_repo.get_all()
        total_games = len(all_games)
        
        # Games by time period
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)
        month_start = now - timedelta(days=30)
        
        games_today = 0
        games_week = 0
        games_month = 0
        
        for game in all_games:
            if game.get("created_at"):
                try:
                    created = datetime.fromisoformat(game["created_at"].replace("Z", "+00:00"))
                    created_naive = created.replace(tzinfo=None)
                    
                    if created_naive >= today_start:
                        games_today += 1
                    if created_naive >= week_start:
                        games_week += 1
                    if created_naive >= month_start:
                        games_month += 1
                except:
                    continue
        
        # Games by status
        finished_games = [g for g in all_games if g["status"] in ["WON", "LOST", "ABORTED"]]
        games_won = sum(1 for g in finished_games if g["status"] == "WON")
        games_lost = sum(1 for g in finished_games if g["status"] == "LOST")
        games_aborted = sum(1 for g in finished_games if g["status"] == "ABORTED")
        games_in_progress = sum(1 for g in all_games if g["status"] == "IN_PROGRESS")
        
        # Average statistics
        avg_game_duration = 0.0
        if finished_games:
            total_duration = sum(g.get("time_seconds", 0) for g in finished_games)
            avg_game_duration = total_duration / len(finished_games)
        
        # Win rate
        win_rate = 0.0
        if games_won + games_lost > 0:
            win_rate = (games_won / (games_won + games_lost)) * 100
        
        # Most active users (top 5)
        user_game_counts = {}
        for game in all_games:
            session = self.session_repo.get_by_id(game["session_id"])
            if session:
                user_id = session["user_id"]
                user_game_counts[user_id] = user_game_counts.get(user_id, 0) + 1
        
        top_users = sorted(user_game_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        most_active_users = [
            {
                "user_id": user_id,
                "nickname": self.user_repo.get_by_id(user_id).get("nickname") if self.user_repo.get_by_id(user_id) else None,
                "game_count": count
            }
            for user_id, count in top_users
        ]
        
        return {
            "users": {
                "total": total_users,
                "admins": admin_users,
                "regular": total_users - admin_users
            },
            "sessions": {
                "total": total_sessions,
                "active": active_sessions,
                "completed": total_sessions - active_sessions
            },
            "games": {
                "total": total_games,
                "won": games_won,
                "lost": games_lost,
                "aborted": games_aborted,
                "in_progress": games_in_progress,
                "win_rate": win_rate
            },
            "games_by_period": {
                "today": games_today,
                "last_7_days": games_week,
                "last_30_days": games_month
            },
            "performance": {
                "avg_game_duration_sec": avg_game_duration
            },
            "most_active_users": most_active_users
        }
    
    def _filter_by_period(self, games: List[dict], period: str) -> List[dict]:
        """Filter games by time period."""
        if period == "all":
            return games
            
        now = datetime.utcnow()
        period_days = {"1d": 1, "7d": 7, "30d": 30}.get(period, 0)
        
        if period_days == 0:
            return games
            
        cutoff = now - timedelta(days=period_days)
        filtered = []
        
        for game in games:
            if game.get("created_at"):
                try:
                    created = datetime.fromisoformat(game["created_at"].replace("Z", "+00:00"))
                    if created.replace(tzinfo=None) >= cutoff:
                        filtered.append(game)
                except:
                    continue
                    
        return filtered
