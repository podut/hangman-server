# Hangman Server

Server pentru jocul Hangman cu API REST.

## Setup Rapid

### 1. Instalare dependințe

```bash
cd server
pip install -r requirements.txt
```

### 2. Pornire server

```bash
cd server/src
python main.py
```

Serverul va rula pe `http://localhost:8000`

### 3. Testare API

Accesează documentația interactivă:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 4. Client Python

```bash
cd client-examples
python python_client.py
```

## API Endpoints Principale

### Autentificare

- `POST /api/v1/auth/register` - Înregistrare utilizator
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/users/me` - Profil utilizator

### Sesiuni & Jocuri

- `POST /api/v1/sessions` - Creare sesiune
- `GET /api/v1/sessions/{session_id}` - Detalii sesiune
- `POST /api/v1/sessions/{session_id}/games` - Creare joc
- `GET /api/v1/sessions/{session_id}/games/{game_id}/state` - Stare joc
- `POST /api/v1/sessions/{session_id}/games/{game_id}/guess` - Ghicire
- `GET /api/v1/sessions/{session_id}/games/{game_id}/history` - Istoric

### Statistici

- `GET /api/v1/sessions/{session_id}/stats` - Statistici sesiune
- `GET /api/v1/leaderboard` - Clasament global

### Utilități

- `GET /healthz` - Health check
- `GET /version` - Versiune
- `GET /time` - Timp server

## Exemplu Flux Complet

```python
from python_client import HangmanClient

client = HangmanClient()

# 1. Înregistrare și login
client.register("user@test.com", "pass123", "Player1")
client.login("user@test.com", "pass123")

# 2. Creare sesiune
session = client.create_session(num_games=10)

# 3. Creare joc
game = client.create_game(session["session_id"])

# 4. Ghiciri
client.guess_letter(session["session_id"], game["game_id"], "a")
client.guess_letter(session["session_id"], game["game_id"], "e")

# 5. Verificare stare
state = client.get_game_state(session["session_id"], game["game_id"])
print(state["pattern"])

# 6. Statistici
stats = client.get_session_stats(session["session_id"])
```

## Caracteristici

✓ API REST complet funcțional
✓ Autentificare JWT
✓ Suport pentru sesiuni de 1, 100 sau N jocuri
✓ Ghicire literă și cuvânt
✓ Statistici detaliate
✓ Clasament global (leaderboard)
✓ Suport diacritice românești
✓ Storage in-memory (ușor de extins la PostgreSQL/Redis)

## Extinderi Viitoare

- [ ] PostgreSQL pentru persistență
- [ ] Redis pentru cache
- [ ] WebSocket pentru notificări real-time
- [ ] Rate limiting cu Redis
- [ ] Administrare dicționare (admin)
- [ ] Export/import statistici
- [ ] Containerizare Docker

## Structură Proiect

```
hangman-server/
├── server/
│   ├── src/
│   │   ├── main.py              # Server FastAPI
│   │   └── dict_ro_basic.txt    # Dicționar cuvinte
│   ├── requirements.txt
│   └── .env
├── client-examples/
│   └── python_client.py         # Client Python
└── docs/
    └── README.md
```
