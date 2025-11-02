# Hangman Server - Roadmap pentru Finalizare

## 📋 Context

**Status actual**: 59/71 cerințe implementate (83%)
**Commit**: feat: Implementare completa Hangman Server API v1.0
**Data**: 2025-11-02

---

## 🎯 Taskuri pentru Senior Developer

### 🔴 **Prioritate 1: Arhitectură & Clean Code** (2-3 zile)

#### Task 1.1: Refactoring - Separare în Module

**Obiectiv**: Cod modular, testabil, maintainable

**Structură țintă**:

```
server/src/
├── main.py                 # FastAPI app, routes registration
├── config.py               # Settings, environment variables
├── models/
│   ├── __init__.py
│   ├── user.py            # User, UserCreate, UserResponse
│   ├── session.py         # Session, SessionCreate, SessionResponse
│   ├── game.py            # Game, GameResponse, Guess
│   ├── dictionary.py      # Dictionary, DictionaryCreate
│   └── stats.py           # UserStats, GlobalStats, LeaderboardEntry
├── services/
│   ├── __init__.py
│   ├── auth_service.py    # register_user, login, create_token
│   ├── game_service.py    # create_game, make_guess, calculate_score
│   ├── session_service.py # create_session, abort_session
│   ├── stats_service.py   # get_user_stats, get_global_stats, leaderboard
│   └── dict_service.py    # list_dicts, create_dict, get_words
├── repositories/
│   ├── __init__.py
│   ├── user_repo.py       # In-memory user storage
│   ├── session_repo.py    # In-memory session storage
│   ├── game_repo.py       # In-memory game storage
│   └── dict_repo.py       # In-memory dictionary storage
├── routes/
│   ├── __init__.py
│   ├── auth.py            # /api/v1/auth/*
│   ├── sessions.py        # /api/v1/sessions/*
│   ├── games.py           # /api/v1/sessions/{sid}/games/*
│   ├── stats.py           # /api/v1/users/{uid}/stats, /api/v1/stats/*
│   ├── admin.py           # /api/v1/admin/*
│   └── utils.py           # /health, /version, /time
├── utils/
│   ├── __init__.py
│   ├── auth_utils.py      # verify_password, hash_password, decode_token
│   ├── game_utils.py      # normalize, update_pattern
│   └── validators.py      # Custom validators
└── tests/
    ├── __init__.py
    ├── test_game_logic.py     # ✅ Există (9 teste)
    ├── test_auth_service.py   # TODO
    ├── test_game_service.py   # TODO
    └── test_stats_service.py  # TODO
```

**Criterii de acceptare**:

- [ ] `main.py` < 100 linii (doar app setup + routes registration)
- [ ] Fiecare modul < 300 linii
- [ ] Dependency injection pentru repositories în services
- [ ] Type hints complete (mypy compatible)
- [ ] Docstrings pentru toate funcțiile publice

**Estimare**: 2 zile

---

#### Task 1.2: Environment Configuration

**Obiectiv**: Configurare externalizată, securitate îmbunătățită

**Fișier `.env.example`**:

```env
# Server
APP_NAME=Hangman Server
APP_VERSION=1.0.0
DEBUG=true
HOST=0.0.0.0
PORT=8000

# JWT
SECRET_KEY=your-secret-key-change-in-production-min-32-chars
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Admin
ADMIN_EMAIL=admin@example.com

# CORS (pentru frontend)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080

# Rate Limiting (pentru mai târziu)
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10

# Database (pentru migrare PostgreSQL)
# DATABASE_URL=postgresql://user:password@localhost:5432/hangman_db
# REDIS_URL=redis://localhost:6379/0
```

**Fișier `server/src/config.py`**:

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "Hangman Server"
    app_version: str = "1.0.0"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    admin_email: str
    cors_origins: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings():
    return Settings()
```

**Criterii de acceptare**:

- [ ] `.env` în `.gitignore`
- [ ] `.env.example` committat
- [ ] `SECRET_KEY` generat cu `openssl rand -hex 32`
- [ ] Toate valorile hardcodate migrate în config
- [ ] Validare environment variables la startup

**Estimare**: 0.5 zile

---

### 🟡 **Prioritate 2: Îmbunătățiri API & Developer Experience** (2 zile)

#### Task 2.1: Format Erori Standardizat

**Obiectiv**: Debugging mai ușor, experiență consistentă

**Format țintă**:

```json
{
  "error": {
    "code": "GAME_ALREADY_FINISHED",
    "message": "Acest joc este deja terminat (status: WON)",
    "details": {
      "game_id": "game_123",
      "current_status": "WON"
    }
  },
  "request_id": "req_a1b2c3d4e5f6",
  "timestamp": "2025-11-02T14:30:00Z",
  "path": "/api/v1/sessions/sess_123/games/game_123/guess"
}
```

**Implementare**:

```python
# server/src/models/errors.py
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional
import uuid

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str
    timestamp: datetime
    path: str

# server/src/utils/exceptions.py
class HangmanException(Exception):
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class GameAlreadyFinishedException(HangmanException):
    def __init__(self, game_id: str, status: str):
        super().__init__(
            code="GAME_ALREADY_FINISHED",
            message=f"Joc deja terminat (status: {status})",
            details={"game_id": game_id, "status": status}
        )

# server/src/middleware/error_handler.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
import uuid

@app.exception_handler(HangmanException)
async def hangman_exception_handler(request: Request, exc: HangmanException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details
            },
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )
```

**Coduri eroare**:

- `INVALID_CREDENTIALS` - Email/parolă greșite
- `USER_ALREADY_EXISTS` - Email deja înregistrat
- `SESSION_NOT_FOUND` - Sesiune inexistentă
- `GAME_NOT_FOUND` - Joc inexistent
- `GAME_ALREADY_FINISHED` - Joc terminat (WON/LOST/ABORTED)
- `INVALID_GUESS` - Literă/cuvânt invalid
- `UNAUTHORIZED` - Token lipsă/invalid
- `FORBIDDEN` - Acțiune permisă doar admin
- `DICTIONARY_NOT_FOUND` - Dicționar inexistent
- `INVALID_DICTIONARY` - Dicționar invalid (< 10 cuvinte)

**Criterii de acceptare**:

- [ ] Middleware global pentru exception handling
- [ ] Toate endpoint-urile returnează format standardizat
- [ ] `request_id` tracking prin headers (`X-Request-ID`)
- [ ] Logging cu `request_id` pentru correlație
- [ ] Documentare coduri eroare în `docs/ERROR_CODES.md`

**Estimare**: 1 zi

---

#### Task 2.2: Middleware & Request Tracking

**Obiectiv**: Observabilitate, debugging, audit

**Componente**:

1. **Request ID Middleware**:

```python
# server/src/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

2. **Logging Middleware**:

```python
# server/src/middleware/logging.py
import time
import logging

logger = logging.getLogger("hangman")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        logger.info(
            f"Request started",
            extra={
                "request_id": request.state.request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host
            }
        )

        response = await call_next(request)

        duration = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={
                "request_id": request.state.request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2)
            }
        )

        return response
```

3. **Structured Logging**:

```python
# server/src/utils/logger.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

def setup_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    logger = logging.getLogger("hangman")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
```

**Criterii de acceptare**:

- [ ] `X-Request-ID` header în request/response
- [ ] Loguri JSON structured
- [ ] Logging pentru: auth events, game actions, errors
- [ ] Correlație request-response via `request_id`

**Estimare**: 1 zi

---

### 🟢 **Prioritate 3: Testing & Quality** (2 zile)

#### Task 3.1: Teste Unit Complete

**Obiectiv**: > 80% code coverage pentru business logic

**Teste necesare**:

```python
# server/tests/test_auth_service.py
def test_register_user_success()
def test_register_user_duplicate_email()
def test_login_valid_credentials()
def test_login_invalid_credentials()
def test_create_access_token()
def test_verify_token_valid()
def test_verify_token_expired()

# server/tests/test_game_service.py
def test_create_game_success()
def test_create_game_no_word_repetition()
def test_make_guess_letter_correct()
def test_make_guess_letter_wrong()
def test_make_guess_word_correct()
def test_make_guess_word_wrong()
def test_game_win_condition()
def test_game_lost_condition()
def test_abort_game()
def test_calculate_composite_score()

# server/tests/test_stats_service.py
def test_get_user_stats_all_time()
def test_get_user_stats_period_filter()
def test_get_global_stats()
def test_leaderboard_composite_score()
def test_leaderboard_period_filter()

# server/tests/test_dict_service.py
def test_list_dictionaries()
def test_create_dictionary_valid()
def test_create_dictionary_too_few_words()
def test_update_dictionary()
def test_get_dictionary_words()
def test_get_dictionary_sample()
```

**Setup pytest**:

```python
# server/tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from server.src.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_token(client):
    # Register & login test user
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "test123",
        "nickname": "tester"
    })
    token_response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "test123"
    })
    return token_response.json()["access_token"]

@pytest.fixture
def admin_token(client):
    # First user = admin
    response = client.post("/api/v1/auth/register", json={
        "email": "admin@example.com",
        "password": "admin123",
        "nickname": "admin"
    })
    token_response = client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "admin123"
    })
    return token_response.json()["access_token"]
```

**Rulare**:

```bash
pip install pytest pytest-cov
pytest server/tests/ -v --cov=server/src --cov-report=html
```

**Criterii de acceptare**:

- [ ] Minimum 30 teste unit
- [ ] Code coverage > 80% pentru services
- [ ] Toate testele trec
- [ ] CI-ready (rulare automată)

**Estimare**: 1.5 zile

---

#### Task 3.2: Teste Integrare E2E

**Obiectiv**: Validare flow-uri complete

**Scenarii**:

1. **Happy Path - Joc Complet**:

```python
def test_complete_game_flow(client):
    # 1. Register
    register_response = client.post("/api/v1/auth/register", ...)

    # 2. Login
    login_response = client.post("/api/v1/auth/login", ...)
    token = login_response.json()["access_token"]

    # 3. Create session
    session_response = client.post(
        "/api/v1/sessions",
        headers={"Authorization": f"Bearer {token}"},
        json={"max_wrong_guesses": 6, "num_games": 3}
    )
    session_id = session_response.json()["session_id"]

    # 4. Create game
    game_response = client.post(
        f"/api/v1/sessions/{session_id}/games",
        headers={"Authorization": f"Bearer {token}"}
    )
    game_id = game_response.json()["game_id"]

    # 5. Make guesses until win/lost
    for letter in "aeiou":
        client.post(
            f"/api/v1/sessions/{session_id}/games/{game_id}/guess",
            headers={"Authorization": f"Bearer {token}"},
            json={"type": "letter", "value": letter}
        )

    # 6. Check stats
    stats_response = client.get(
        f"/api/v1/users/me/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert stats_response.json()["total_games"] == 1

    # 7. Check leaderboard
    leaderboard = client.get("/api/v1/leaderboard")
    assert len(leaderboard.json()["entries"]) > 0
```

2. **Admin Flow**:

```python
def test_admin_dictionary_management(client, admin_token):
    # Create dictionary
    dict_response = client.post(
        "/api/v1/admin/dictionaries",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": "Test Dict",
            "description": "Test",
            "words": ["word1", "word2", ..., "word15"]
        }
    )
    dict_id = dict_response.json()["dictionary_id"]

    # Update dictionary
    client.patch(
        f"/api/v1/admin/dictionaries/{dict_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"active": True}
    )

    # Get words
    words_response = client.get(
        f"/api/v1/admin/dictionaries/{dict_id}/words",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert len(words_response.json()["words"]) == 15
```

3. **Error Handling**:

```python
def test_invalid_token():
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
```

**Criterii de acceptare**:

- [ ] Minimum 10 teste E2E
- [ ] Acoperire flow-uri: auth, game, stats, admin
- [ ] Teste pentru error cases
- [ ] Toate testele trec

**Estimare**: 0.5 zile

---

### 🔵 **Prioritate 4: Documentație & DevEx** (1 zi)

#### Task 4.1: Documentație API Completă

**Obiectiv**: Onboarding rapid, API explorer

**Fișiere**:

1. **`docs/API.md`** - Documentație completă:

```markdown
# Hangman Server API Documentation

## Autentificare

### Register

POST /api/v1/auth/register
Content-Type: application/json

{
"email": "user@example.com",
"password": "securepass123",
"nickname": "player1"
}

Response 201:
{
"user_id": "usr_abc123",
"email": "user@example.com",
"nickname": "player1",
"created_at": "2025-11-02T14:30:00Z"
}

Errors:

- 400 USER_ALREADY_EXISTS - Email deja înregistrat
- 422 - Validare eșuată (email invalid, parolă < 6 caractere)
```

2. **`docs/ERROR_CODES.md`** - Coduri eroare:

```markdown
# Error Codes Reference

## AUTH\_\*

- `INVALID_CREDENTIALS` (401) - Email/parolă greșite
- `USER_ALREADY_EXISTS` (400) - Email deja înregistrat
- `INVALID_TOKEN` (401) - Token JWT invalid/expirat
- `TOKEN_EXPIRED` (401) - Token expirat

## GAME\_\*

- `GAME_NOT_FOUND` (404) - Joc inexistent
- `GAME_ALREADY_FINISHED` (400) - Joc terminat
- `INVALID_GUESS` (400) - Literă/cuvânt invalid
- `SESSION_NOT_FOUND` (404) - Sesiune inexistentă
  ...
```

3. **`docs/DEVELOPMENT.md`** - Setup & workflow:

```markdown
# Development Guide

## Prerequisites

- Python 3.11+
- pip/venv

## Setup

git clone <repo>
cd hangman-server
python -m venv venv
source venv/bin/activate # Windows: venv\Scripts\activate
pip install -r server/requirements.txt

## Environment

cp .env.example .env

# Edit .env și setează SECRET_KEY

## Run

python server/src/main.py

## Test

pytest server/tests/ -v --cov

## Commit Convention

- feat: Funcționalitate nouă
- fix: Bug fix
- refactor: Refactoring
- test: Teste
- docs: Documentație
```

4. **Postman Collection**:

```json
// docs/Hangman_API.postman_collection.json
{
  "info": {
    "name": "Hangman Server API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Auth",
      "item": [
        {
          "name": "Register",
          "request": {
            "method": "POST",
            "url": "{{base_url}}/api/v1/auth/register",
            "body": {...}
          }
        },
        ...
      ]
    },
    ...
  ]
}
```

**Criterii de acceptare**:

- [ ] `docs/API.md` cu toate endpoint-urile
- [ ] `docs/ERROR_CODES.md` complet
- [ ] `docs/DEVELOPMENT.md` cu setup
- [ ] Postman collection exportat
- [ ] OpenAPI spec validat la `/docs`

**Estimare**: 1 zi

---

## 📊 Estimări Totale

| Prioritate      | Taskuri | Estimare     | Impact      |
| --------------- | ------- | ------------ | ----------- |
| P1: Arhitectură | 2       | 2.5 zile     | 🔥 Critical |
| P2: API Quality | 2       | 2 zile       | ⚡ High     |
| P3: Testing     | 2       | 2 zile       | 🎯 High     |
| P4: Docs        | 1       | 1 zi         | 📚 Medium   |
| **TOTAL**       | **7**   | **7.5 zile** |             |

---

## 🚀 Faze de Implementare

### **Săptămâna 1** (Zile 1-3): Clean Code Foundation

- [ ] Task 1.1: Refactoring în module ✅ 2 zile
- [ ] Task 1.2: Environment config ✅ 0.5 zile
- [ ] Task 2.1: Format erori standardizat ✅ 0.5 zile

### **Săptămâna 2** (Zile 4-5): Developer Experience

- [ ] Task 2.2: Middleware & logging ✅ 1 zi
- [ ] Task 3.1: Teste unit complete ✅ 1 zi

### **Săptămâna 3** (Zile 6-7): Polish & Launch

- [ ] Task 3.1 (cont): Finalizare teste ✅ 0.5 zile
- [ ] Task 3.2: Teste E2E ✅ 0.5 zile
- [ ] Task 4.1: Documentație completă ✅ 1 zi

---

## 🔮 Post-Launch (Containerizare & Producție)

### După finalizarea taskurilor de mai sus:

1. **Containerizare** (2-3 zile):

   - [ ] Validare Dockerfile
   - [ ] Docker Compose cu PostgreSQL + Redis
   - [ ] Health checks în container
   - [ ] Multi-stage build pentru optimizare

2. **Database Migration** (2-3 zile):

   - [ ] SQLAlchemy models
   - [ ] Alembic migrations
   - [ ] Migrare date in-memory → PostgreSQL
   - [ ] Connection pooling

3. **Production Features** (3-4 zile):

   - [ ] Rate limiting (slowapi/redis)
   - [ ] HTTPS setup (nginx reverse proxy)
   - [ ] CORS configuration
   - [ ] Email service (reset password) - **AICI verificare email**
   - [ ] Background tasks (Celery/Redis)

4. **Monitoring & Observability** (2 zile):

   - [ ] Prometheus metrics endpoint
   - [ ] Grafana dashboards
   - [ ] Sentry error tracking
   - [ ] APM (Application Performance Monitoring)

5. **CI/CD** (1-2 zile):
   - [ ] GitHub Actions pipeline
   - [ ] Automated tests
   - [ ] Docker build & push
   - [ ] Deployment automation

---

## 📝 Note Importante

### Pentru Local Development (Faza Curentă):

- ✅ In-memory storage suficient
- ✅ Email verification NU este necesară (amânată pentru containerizare)
- ✅ Rate limiting NU este necesar (low traffic)
- ✅ HTTPS NU este necesar (localhost)

### Pentru Producție (După Containerizare):

- ❌ In-memory storage NU este suficient → PostgreSQL
- ❌ Email verification DEVINE necesară → SMTP setup
- ❌ Rate limiting DEVINE necesar → Redis + slowapi
- ❌ HTTPS DEVINE obligatoriu → nginx + Let's Encrypt

---

**Pregătit pentru**: Senior Developer Review
**Next Step**: Implementare Task 1.1 (Refactoring Module Separation)
