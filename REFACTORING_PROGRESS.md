# Task 1.1 - Refactoring Progress

## ✅ Completat (60%)

### Structură Modulară Creată
```
server/src/
├── models/          # ✅ Complete (5/5 files)
│   ├── user.py      # RegisterRequest, LoginRequest, UserResponse
│   ├── session.py   # CreateSessionRequest, SessionResponse
│   ├── game.py      # GuessRequest, GameResponse, GuessResponse
│   ├── dictionary.py# DictionaryCreate, DictionaryUpdate, DictionaryResponse
│   └── stats.py     # UserStats, GlobalStats, LeaderboardEntry
├── utils/           # ✅ Complete (2/2 files)
│   ├── auth_utils.py    # verify_password, hash_password, create_access_token, decode_token
│   └── game_utils.py    # normalize, update_pattern, calculate_score
├── repositories/    # ✅ Complete (4/4 files)
│   ├── user_repository.py       # UserRepository with CRUD
│   ├── session_repository.py    # SessionRepository with CRUD
│   ├── game_repository.py       # GameRepository with CRUD + guesses
│   └── dictionary_repository.py # DictionaryRepository with CRUD
├── services/        # ⚠️ Partial (2/5 files)
│   ├── auth_service.py     # ✅ AuthService (register, login, refresh)
│   ├── session_service.py  # ✅ SessionService (create, get, list, abort)
│   ├── game_service.py     # ❌ TODO
│   ├── stats_service.py    # ❌ TODO
│   └── dictionary_service.py # ❌ TODO
└── routes/          # ❌ Not Started (0/6 files)
    ├── auth.py      # ❌ TODO: Extract from main.py
    ├── sessions.py  # ❌ TODO: Extract from main.py
    ├── games.py     # ❌ TODO: Extract from main.py
    ├── stats.py     # ❌ TODO: Extract from main.py
    ├── admin.py     # ❌ TODO: Extract from main.py
    └── utils.py     # ❌ TODO: Extract from main.py
```

## 🚧 În Lucru

### Files Created
- ✅ 5 models (user, session, game, dictionary, stats)
- ✅ 2 utils (auth_utils, game_utils)
- ✅ 4 repositories (user, session, game, dictionary)
- ✅ 2 services (auth, session)
- ⚠️ 1 routes placeholder (__init__.py)

### Commits
```
35e396b - refactor(wip): Task 1.1 - Creare structura modulara
```

## ❌ Rămâs de Făcut

### Priority 1: Complete Services (2-3 ore)

#### `game_service.py` (120-150 linii)
Metode necesare:
```python
class GameService:
    def create_game(session_id, user_id) -> Dict
    def get_game(game_id, user_id) -> Dict
    def make_guess_letter(game_id, letter, user_id) -> Dict
    def make_guess_word(game_id, word, user_id) -> Dict
    def abort_game(game_id, user_id) -> Dict
    def list_session_games(session_id, user_id, page, page_size) -> List
```

#### `stats_service.py` (100-120 linii)
Metode necesare:
```python
class StatsService:
    def get_user_stats(user_id, period) -> UserStats
    def get_global_stats(period) -> GlobalStats
    def get_leaderboard(metric, period, limit) -> List[LeaderboardEntry]
```

#### `dictionary_service.py` (80-100 linii)
Metode necesare:
```python
class DictionaryService:
    def list_dictionaries() -> List[Dict]
    def create_dictionary(name, words, ...) -> Dict
    def update_dictionary(dict_id, updates) -> Dict
    def get_dictionary_words(dict_id, sample) -> List[str]
```

### Priority 2: Extract Routes (3-4 ore)

#### `routes/auth.py` (80-100 linii)
Endpoints:
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- GET /api/v1/users/me

#### `routes/sessions.py` (60-80 linii)
Endpoints:
- POST /api/v1/sessions
- GET /api/v1/sessions/{session_id}
- POST /api/v1/sessions/{session_id}/abort
- GET /api/v1/sessions/{session_id}/games

#### `routes/games.py` (100-120 linii)
Endpoints:
- POST /api/v1/sessions/{sid}/games
- GET /api/v1/sessions/{sid}/games/{gid}/state
- POST /api/v1/sessions/{sid}/games/{gid}/guess
- POST /api/v1/sessions/{sid}/games/{gid}/abort

#### `routes/stats.py` (60-80 linii)
Endpoints:
- GET /api/v1/users/{uid}/stats
- GET /api/v1/stats/global
- GET /api/v1/leaderboard

#### `routes/admin.py` (100-120 linii)
Endpoints:
- GET /api/v1/admin/dictionaries
- POST /api/v1/admin/dictionaries
- PATCH /api/v1/admin/dictionaries/{id}
- GET /api/v1/admin/dictionaries/{id}/words

#### `routes/utils.py` (30-40 linii)
Endpoints:
- GET /healthz
- GET /version
- GET /time

### Priority 3: New main.py (50-80 linii)

#### Structură țintă:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Import routes
from routes import api_router, utils_router

# Initialize app
app = FastAPI(title="Hangman Server API", version="1.0.0")

# Add middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

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

# Dependency injection setup
def get_auth_service():
    return auth_service

def get_game_service():
    return game_service

# ... etc

# Include routers
app.include_router(api_router)
app.include_router(utils_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## 📊 Estimare Timp Rămas

| Task | Estimare | Priority |
|------|----------|----------|
| Complete game_service.py | 1.5h | 🔴 High |
| Complete stats_service.py | 1h | 🔴 High |
| Complete dictionary_service.py | 0.5h | 🟡 Medium |
| Extract routes (6 files) | 3h | 🔴 High |
| New main.py + testing | 1h | 🔴 High |
| **TOTAL** | **7h** | |

## 🎯 Next Steps

1. **Imediat**: Complete `game_service.py` (cele mai multe linii de logică)
2. **Apoi**: Complete `stats_service.py` și `dictionary_service.py`
3. **După**: Extract toate endpoint-urile în routes/
4. **Final**: Create new `main.py` și șterge `main_original.py`
5. **Test**: Rulează serverul și verifică că toate endpoint-urile funcționează

## 📝 Notes

- Type hints warnings în repositories pot fi ignorate pentru moment
- `datetime.utcnow()` deprecated warnings - vor fi fixate în Task 1.2 (config)
- FastAPI dependencies (Depends) vor fi configurate în routes
- Original `main.py` păstrat ca backup în `main_original.py`

## ✅ Success Criteria

- [ ] `main.py` < 100 linii (target: ~60-80 linii)
- [ ] Toate services complete cu business logic
- [ ] Toate routes extrase și organizate
- [ ] Dependency injection funcțional
- [ ] Server pornește fără erori
- [ ] Toate endpoint-urile funcționale (testate cu client Python)
- [ ] Code organizat și ușor de menținut
