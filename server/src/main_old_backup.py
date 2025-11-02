"""Hangman Server API - Refactored with modular architecture."""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from datetime import datetime

# Import models
from models import (
    RegisterRequest, LoginRequest, RefreshRequest,
    CreateSessionRequest, GuessRequest
)

# Import repositories
from repositories import (
    UserRepository, SessionRepository,
    GameRepository, DictionaryRepository
)

# Import services
from services import (
    AuthService, SessionService, GameService,
    StatsService, DictionaryService
)

# Import utils
from utils.auth_utils import decode_token

# Initialize FastAPI app
app = FastAPI(
    title="Hangman Server API",
    version="1.0.0",
    description="Hangman game server with modular architecture"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Initialize repositories (singletons)
user_repo = UserRepository()
session_repo = SessionRepository()
game_repo = GameRepository()
dict_repo = DictionaryRepository()

# Initialize services with dependency injection
auth_service = AuthService(user_repo)
session_service = SessionService(session_repo, dict_repo)
game_service = GameService(game_repo, session_repo, dict_repo)
stats_service = StatsService(user_repo, session_repo, game_repo)
dict_service = DictionaryService(dict_repo)

# Load dictionary
DICT_PATH = Path(__file__).parent / "dict_ro_basic.txt"
if not DICT_PATH.exists():
    DICT_PATH.write_text("student\nprogramare\ncomputer\npython\nserver\nclient\naplicatie\ndicționar\nîncercare\nstatistică")
WORDS = [w.strip().lower() for w in DICT_PATH.read_text(encoding="utf-8").splitlines() if w.strip()]

# Initialize default dictionary
dictionaries_db["dict_ro_basic"] = {
    "dictionary_id": "dict_ro_basic",
    "name": "Romanian Basic",
    "language": "ro",
    "difficulty": "auto",
    "words": WORDS.copy(),
    "active": True,
    "created_at": datetime.utcnow().isoformat() + "Z"
}

# ============= MODELS =============
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nickname: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class CreateSessionRequest(BaseModel):
    num_games: int = 100
    dictionary_id: str = "dict_ro_basic"
    difficulty: Literal["easy", "normal", "hard", "auto"] = "auto"
    language: Literal["ro", "en"] = "ro"
    max_misses: int = 6
    allow_word_guess: bool = True
    seed: Optional[int] = None

class GuessRequest(BaseModel):
    letter: Optional[str] = None
    word: Optional[str] = None

# ============= AUTH UTILS =============
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None or user_id not in users_db:
            raise HTTPException(status_code=401, detail="Invalid token")
        return users_db[user_id]
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============= GAME LOGIC =============
def normalize(s: str) -> str:
    return s.lower().replace('ă','a').replace('â','a').replace('î','i').replace('ș','s').replace('ț','t')

def update_pattern(secret: str, pattern: str, letter: str) -> str:
    letter_norm = normalize(letter)
    result = list(pattern)
    for i, c in enumerate(secret):
        if normalize(c) == letter_norm:
            result[i] = secret[i]
    return ''.join(result)

def calculate_score(won: bool, total_guesses: int, wrong_letters: int, wrong_word_guesses: int, time_sec: float, length: int) -> float:
    return (1000 * int(won) - 10 * total_guesses - 5 * wrong_letters - 40 * wrong_word_guesses - 0.2 * time_sec + 2 * length)

# ============= ENDPOINTS =============

@app.get("/healthz")
def health():
    return {"ok": True}

@app.get("/version")
def version():
    return {"version": "1.0.0", "build": "2025-10-31"}

@app.get("/time")
def server_time():
    return {"time": datetime.utcnow().isoformat() + "Z"}

def get_admin_user(user = Depends(get_current_user)):
    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

@app.post("/api/v1/auth/register", status_code=201)
def register(req: RegisterRequest):
    if req.email in [u["email"] for u in users_db.values()]:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_id = f"u_{len(users_db) + 1}"
    # First user is admin
    is_admin = len(users_db) == 0
    users_db[user_id] = {
        "user_id": user_id,
        "email": req.email,
        "password": pwd_context.hash(req.password),
        "nickname": req.nickname or req.email.split("@")[0],
        "is_admin": is_admin,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    return {"user_id": user_id, "created_at": users_db[user_id]["created_at"], "is_admin": is_admin}

@app.post("/api/v1/auth/login")
def login(req: LoginRequest):
    user = next((u for u in users_db.values() if u["email"] == req.email), None)
    if not user or not pwd_context.verify(req.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token({"sub": user["user_id"]})
    refresh_token = create_access_token({"sub": user["user_id"], "type": "refresh"})
    return {"access_token": access_token, "refresh_token": refresh_token, "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60}

@app.post("/api/v1/auth/refresh")
def refresh(req: RefreshRequest):
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        access_token = create_access_token({"sub": payload["sub"]})
        return {"access_token": access_token, "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.get("/api/v1/users/me")
def get_profile(user = Depends(get_current_user)):
    return {k: v for k, v in user.items() if k != "password"}

@app.post("/api/v1/sessions", status_code=201)
def create_session(req: CreateSessionRequest, user = Depends(get_current_user)):
    session_id = f"s_{len(sessions_db) + 1}"
    sessions_db[session_id] = {
        "session_id": session_id,
        "user_id": user["user_id"],
        "num_games": req.num_games,
        "params": req.model_dump(exclude={"num_games"}),
        "status": "ACTIVE",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "finished_at": None,
        "games_created": 0
    }
    return {
        "session_id": session_id,
        "num_games": req.num_games,
        "created_at": sessions_db[session_id]["created_at"],
        "status": "ACTIVE"
    }

@app.get("/api/v1/sessions/{session_id}")
def get_session(session_id: str, user = Depends(get_current_user)):
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions_db[session_id]
    if session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session_games = [g for g in games_db.values() if g["session_id"] == session_id]
    finished = sum(1 for g in session_games if g["status"] in ["WON", "LOST", "ABORTED"])
    
    return {
        **session,
        "games_finished": finished,
        "games_total": session["num_games"]
    }

@app.post("/api/v1/sessions/{session_id}/games", status_code=201)
def create_game(session_id: str, user = Depends(get_current_user)):
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions_db[session_id]
    if session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if session["games_created"] >= session["num_games"]:
        raise HTTPException(status_code=400, detail="Session game limit reached")
    
    # Get dictionary
    dict_id = session["params"].get("dictionary_id", "dict_ro_basic")
    if dict_id not in dictionaries_db:
        dict_id = "dict_ro_basic"
    available_words = dictionaries_db[dict_id]["words"].copy()
    
    # Get words already used in this session
    used_words = set()
    for game in games_db.values():
        if game["session_id"] == session_id:
            used_words.add(game["secret"])
    
    # Filter out used words
    available_words = [w for w in available_words if w not in used_words]
    if not available_words:
        raise HTTPException(status_code=400, detail="No more unique words available in dictionary")
    
    rng = random.Random(session["params"].get("seed", None))
    secret = rng.choice(available_words)
    
    game_id = f"g_{len(games_db) + 1}"
    games_db[game_id] = {
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
    sessions_db[session_id]["games_created"] += 1
    guesses_db[game_id] = []
    
    return {k: v for k, v in games_db[game_id].items() if k != "secret"}

@app.get("/api/v1/sessions/{session_id}/games/{game_id}/state")
def get_game_state(session_id: str, game_id: str, user = Depends(get_current_user)):
    if session_id not in sessions_db or game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game not found")
    if sessions_db[session_id]["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    game = games_db[game_id]
    return {k: v for k, v in game.items() if k != "secret"}

@app.post("/api/v1/sessions/{session_id}/games/{game_id}/guess")
def make_guess(session_id: str, game_id: str, req: GuessRequest, user = Depends(get_current_user)):
    if session_id not in sessions_db or game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game not found")
    if sessions_db[session_id]["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    game = games_db[game_id]
    if game["status"] != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail="Game already finished")
    
    if not req.letter and not req.word:
        raise HTTPException(status_code=400, detail="Must provide letter or word")
    
    guess_type = "LETTER" if req.letter else "WORD"
    guess_value = (req.letter or req.word).strip().lower()
    
    if guess_type == "LETTER":
        if len(guess_value) != 1:
            raise HTTPException(status_code=422, detail="Letter must be single character")
        
        if guess_value in game["guessed_letters"]:
            raise HTTPException(status_code=400, detail="Letter already guessed")
        
        game["guessed_letters"].append(guess_value)
        old_pattern = game["pattern"]
        game["pattern"] = update_pattern(game["secret"], game["pattern"], guess_value)
        correct = old_pattern != game["pattern"]
        
        if not correct:
            game["wrong_letters"].append(guess_value)
            game["remaining_misses"] -= 1
        
        game["total_guesses"] += 1
        
        guesses_db[game_id].append({
            "index": len(guesses_db[game_id]) + 1,
            "type": "LETTER",
            "value": guess_value,
            "correct": correct,
            "pattern_after": game["pattern"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        if "*" not in game["pattern"]:
            game["status"] = "WON"
            game["finished_at"] = datetime.utcnow().isoformat() + "Z"
            game["result"] = {"won": True, "secret": game["secret"]}
        elif game["remaining_misses"] <= 0:
            game["status"] = "LOST"
            game["finished_at"] = datetime.utcnow().isoformat() + "Z"
            game["result"] = {"won": False, "secret": game["secret"]}
    
    else:  # WORD
        if not sessions_db[session_id]["params"]["allow_word_guess"]:
            raise HTTPException(status_code=400, detail="Word guessing not allowed")
        
        game["total_guesses"] += 1
        correct = normalize(guess_value) == normalize(game["secret"])
        
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
        
        guesses_db[game_id].append({
            "index": len(guesses_db[game_id]) + 1,
            "type": "WORD",
            "value": guess_value,
            "correct": correct,
            "pattern_after": game["pattern"],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
    
    game["updated_at"] = datetime.utcnow().isoformat() + "Z"
    
    # Calculate time and composite score when game finishes
    if game["status"] in ["WON", "LOST"] and game["finished_at"]:
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
    
    return {k: v for k, v in game.items() if k != "secret"}

@app.get("/api/v1/sessions/{session_id}/games/{game_id}/history")
def get_game_history(session_id: str, game_id: str, user = Depends(get_current_user)):
    if session_id not in sessions_db or game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game not found")
    if sessions_db[session_id]["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {"game_id": game_id, "guesses": guesses_db.get(game_id, [])}

@app.post("/api/v1/sessions/{session_id}/games/{game_id}/abort")
def abort_game(session_id: str, game_id: str, user = Depends(get_current_user)):
    if session_id not in sessions_db or game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game not found")
    if sessions_db[session_id]["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    game = games_db[game_id]
    if game["status"] != "IN_PROGRESS":
        raise HTTPException(status_code=409, detail="Game already finished")
    
    game["status"] = "ABORTED"
    game["updated_at"] = datetime.utcnow().isoformat() + "Z"
    game["result"] = {"won": False, "aborted": True, "secret": game["secret"]}
    
    return {k: v for k, v in game.items() if k != "secret"}

@app.get("/api/v1/sessions/{session_id}/games")
def list_session_games(session_id: str, page: int = 1, page_size: int = 50, user = Depends(get_current_user)):
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    if sessions_db[session_id]["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session_games = [g for g in games_db.values() if g["session_id"] == session_id]
    session_games.sort(key=lambda x: x["created_at"])
    
    total = len(session_games)
    start = (page - 1) * page_size
    end = start + page_size
    
    games_page = [{k: v for k, v in g.items() if k != "secret"} for g in session_games[start:end]]
    
    return {
        "session_id": session_id,
        "games": games_page,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size
    }

@app.post("/api/v1/sessions/{session_id}/abort")
def abort_session(session_id: str, user = Depends(get_current_user)):
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    session = sessions_db[session_id]
    if session["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    if session["status"] != "ACTIVE":
        raise HTTPException(status_code=409, detail="Session already closed")
    
    session["status"] = "ABORTED"
    session["finished_at"] = datetime.utcnow().isoformat() + "Z"
    
    # Abort all IN_PROGRESS games
    for game in games_db.values():
        if game["session_id"] == session_id and game["status"] == "IN_PROGRESS":
            game["status"] = "ABORTED"
            game["updated_at"] = datetime.utcnow().isoformat() + "Z"
    
    return {"session_id": session_id, "status": "ABORTED", "message": "Session aborted successfully"}

@app.get("/api/v1/sessions/{session_id}/stats")
def get_session_stats(session_id: str, user = Depends(get_current_user)):
    if session_id not in sessions_db:
        raise HTTPException(status_code=404, detail="Session not found")
    if sessions_db[session_id]["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    session_games = [g for g in games_db.values() if g["session_id"] == session_id]
    finished = [g for g in session_games if g["status"] in ["WON", "LOST"]]
    
    if not finished:
        return {"session_id": session_id, "games_total": 0, "message": "No finished games yet"}
    
    wins = sum(1 for g in finished if g["status"] == "WON")
    
    return {
        "session_id": session_id,
        "games_total": len(finished),
        "games_finished": len(finished),
        "wins": wins,
        "losses": len(finished) - wins,
        "win_rate": wins / len(finished) if finished else 0,
        "avg_total_guesses": sum(g["total_guesses"] for g in finished) / len(finished),
        "avg_wrong_letters": sum(len(g["wrong_letters"]) for g in finished) / len(finished)
    }

def filter_games_by_period(games_list, period: str):
    """Filter games by time period."""
    if period == "all":
        return games_list
    
    now = datetime.utcnow()
    period_days = {"1d": 1, "7d": 7, "30d": 30}.get(period, 0)
    if period_days == 0:
        return games_list
    
    cutoff = now - timedelta(days=period_days)
    filtered = []
    for game in games_list:
        if game.get("created_at"):
            try:
                created = datetime.fromisoformat(game["created_at"].replace("Z", "+00:00"))
                if created.replace(tzinfo=None) >= cutoff:
                    filtered.append(game)
            except:
                continue
    return filtered

@app.get("/api/v1/users/{user_id}/stats")
def get_user_stats(user_id: str, period: str = "all", current_user = Depends(get_current_user)):
    if user_id != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all games for user
    user_games = []
    for game in games_db.values():
        if game["status"] not in ["WON", "LOST"]:
            continue
        session = sessions_db.get(game["session_id"])
        if session and session["user_id"] == user_id:
            user_games.append(game)
    
    user_games = filter_games_by_period(user_games, period)
    
    if not user_games:
        return {"user_id": user_id, "period": period, "games_total": 0, "message": "No games played"}
    
    wins = sum(1 for g in user_games if g["status"] == "WON")
    total_score = sum(g.get("composite_score", 0) for g in user_games)
    total_time = sum(g.get("time_seconds", 0) for g in user_games)
    
    return {
        "user_id": user_id,
        "period": period,
        "games_total": len(user_games),
        "wins": wins,
        "losses": len(user_games) - wins,
        "win_rate": wins / len(user_games),
        "avg_total_guesses": sum(g["total_guesses"] for g in user_games) / len(user_games),
        "avg_wrong_letters": sum(len(g["wrong_letters"]) for g in user_games) / len(user_games),
        "avg_time_seconds": total_time / len(user_games),
        "avg_composite_score": total_score / len(user_games),
        "total_composite_score": total_score
    }

@app.get("/api/v1/stats/global")
def get_global_stats(period: str = "all"):
    all_games = [g for g in games_db.values() if g["status"] in ["WON", "LOST"]]
    all_games = filter_games_by_period(all_games, period)
    
    if not all_games:
        return {"period": period, "games_total": 0, "message": "No games played"}
    
    wins = sum(1 for g in all_games if g["status"] == "WON")
    unique_users = len(set(sessions_db[g["session_id"]]["user_id"] for g in all_games if g["session_id"] in sessions_db))
    
    return {
        "period": period,
        "games_total": len(all_games),
        "unique_players": unique_users,
        "wins": wins,
        "losses": len(all_games) - wins,
        "win_rate": wins / len(all_games),
        "avg_total_guesses": sum(g["total_guesses"] for g in all_games) / len(all_games),
        "avg_wrong_letters": sum(len(g["wrong_letters"]) for g in all_games) / len(all_games),
        "avg_time_seconds": sum(g.get("time_seconds", 0) for g in all_games) / len(all_games),
        "avg_composite_score": sum(g.get("composite_score", 0) for g in all_games) / len(all_games)
    }

@app.get("/api/v1/leaderboard")
def get_leaderboard(metric: str = "win_rate", period: str = "all", limit: int = 100):
    all_games = [g for g in games_db.values() if g["status"] in ["WON", "LOST"]]
    all_games = filter_games_by_period(all_games, period)
    
    user_stats = {}
    for game in all_games:
        session = sessions_db.get(game["session_id"])
        if not session:
            continue
        uid = session["user_id"]
        if uid not in user_stats:
            user_stats[uid] = {"wins": 0, "total": 0, "guesses": 0, "score": 0}
        user_stats[uid]["total"] += 1
        if game["status"] == "WON":
            user_stats[uid]["wins"] += 1
        user_stats[uid]["guesses"] += game["total_guesses"]
        user_stats[uid]["score"] += game.get("composite_score", 0)
    
    leaderboard = []
    for uid, stats in user_stats.items():
        if stats["total"] == 0:
            continue
        user = users_db.get(uid)
        if not user:
            continue
        leaderboard.append({
            "user_id": uid,
            "nickname": user["nickname"],
            "games": stats["total"],
            "wins": stats["wins"],
            "win_rate": stats["wins"] / stats["total"],
            "avg_guesses": stats["guesses"] / stats["total"],
            "avg_composite_score": stats["score"] / stats["total"]
        })
    
    if metric == "win_rate":
        leaderboard.sort(key=lambda x: x["win_rate"], reverse=True)
    elif metric == "avg_guesses":
        leaderboard.sort(key=lambda x: x["avg_guesses"])
    elif metric == "composite_score":
        leaderboard.sort(key=lambda x: x["avg_composite_score"], reverse=True)
    
    return {"leaderboard": leaderboard[:limit], "metric": metric, "period": period}

# ============= ADMIN ENDPOINTS =============

@app.get("/api/v1/admin/dictionaries")
def list_dictionaries(admin = Depends(get_admin_user)):
    return {
        "dictionaries": [
            {k: v for k, v in d.items() if k != "words"}
            for d in dictionaries_db.values()
        ]
    }

@app.post("/api/v1/admin/dictionaries", status_code=201)
def create_dictionary(
    dictionary_id: str,
    name: str,
    language: str,
    difficulty: str,
    words_text: str,
    admin = Depends(get_admin_user)
):
    if dictionary_id in dictionaries_db:
        raise HTTPException(status_code=409, detail="Dictionary already exists")
    
    words = [w.strip().lower() for w in words_text.strip().splitlines() if w.strip()]
    if len(words) < 10:
        raise HTTPException(status_code=400, detail="Dictionary must contain at least 10 words")
    
    dictionaries_db[dictionary_id] = {
        "dictionary_id": dictionary_id,
        "name": name,
        "language": language,
        "difficulty": difficulty,
        "words": words,
        "active": True,
        "created_at": datetime.utcnow().isoformat() + "Z"
    }
    
    return {
        "dictionary_id": dictionary_id,
        "name": name,
        "word_count": len(words),
        "created_at": dictionaries_db[dictionary_id]["created_at"]
    }

@app.patch("/api/v1/admin/dictionaries/{dictionary_id}")
def update_dictionary(
    dictionary_id: str,
    name: Optional[str] = None,
    active: Optional[bool] = None,
    admin = Depends(get_admin_user)
):
    if dictionary_id not in dictionaries_db:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    
    dictionary = dictionaries_db[dictionary_id]
    if name is not None:
        dictionary["name"] = name
    if active is not None:
        dictionary["active"] = active
    
    return {k: v for k, v in dictionary.items() if k != "words"}

@app.get("/api/v1/admin/dictionaries/{dictionary_id}/words")
def get_dictionary_words(dictionary_id: str, sample: int = 0, admin = Depends(get_admin_user)):
    if dictionary_id not in dictionaries_db:
        raise HTTPException(status_code=404, detail="Dictionary not found")
    
    words = dictionaries_db[dictionary_id]["words"]
    if sample > 0:
        import random
        words = random.sample(words, min(sample, len(words)))
    
    return {
        "dictionary_id": dictionary_id,
        "total_words": len(dictionaries_db[dictionary_id]["words"]),
        "words": words
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
