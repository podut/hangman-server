# 🎮 Hangman GUI - Workflow Complet și Ordine Sigură

## 📋 Ordinea Corectă a Operațiilor (Pentru a evita crash-uri)

### ✅ WORKFLOW OBLIGATORIU (Această ordine previne erori!)

```
1. AUTENTIFICARE
   ├─ Register (prima dată)
   │  └─ POST /api/v1/auth/register
   └─ Login (mereu)
      └─ POST /api/v1/auth/login

2. CREARE SESIUNE
   └─ POST /api/v1/sessions
      ├─ num_games (1, 3, 100, sau custom)
      ├─ difficulty (easy/normal/hard/auto)
      ├─ max_misses (1-10)
      └─ seed (opțional)

3. CREARE JOC (în sesiune)
   └─ POST /api/v1/sessions/{session_id}/games
      ├─ Returnează: game_id, pattern, status=IN_PROGRESS
      └─ ⚠️ IMPORTANT: Trebuie creat înainte de a ghici!

4. JOACĂ JOCUL
   ├─ GET /api/v1/sessions/{session_id}/games/{game_id}/state
   │  └─ Vezi pattern, wrong_letters, guessed_letters
   └─ POST /api/v1/sessions/{session_id}/games/{game_id}/guess
      ├─ Body: {"guess": "a"} sau {"guess": "cuvant"}
      └─ Repeat până când status=WON sau LOST

5. VEZI REZULTATE
   ├─ GET /api/v1/sessions/{session_id}/stats
   └─ GET /api/v1/sessions/{session_id}/games
```

---

## 🔴 ERORI COMUNE (Ce NU trebuie făcut)

### ❌ GREȘEALĂ 1: Ghici fără să creezi joc

```python
# GREȘIT ❌
session = api.create_session(num_games=3)
api.make_guess(session['session_id'], "???", "a")  # CRASH! game_id invalid

# CORECT ✅
session = api.create_session(num_games=3)
game = api.create_game(session['session_id'])  # Creează joc MAI ÎNTÂI!
api.make_guess(session['session_id'], game['game_id'], "a")
```

### ❌ GREȘEALĂ 2: Acces fără autentificare

```python
# GREȘIT ❌
api.create_session(num_games=3)  # 401 Unauthorized

# CORECT ✅
api.login("user@test.com", "pass123")  # Login MAI ÎNTÂI!
api.create_session(num_games=3)
```

### ❌ GREȘEALĂ 3: Dificultate invalidă

```python
# GREȘIT ❌
api.create_session(num_games=3, difficulty="medium")  # 422 Validation Error

# CORECT ✅
api.create_session(num_games=3, difficulty="normal")  # Valorile: easy/normal/hard/auto
```

### ❌ GREȘEALĂ 4: Creezi mai multe jocuri decât num_games

```python
# GREȘIT ❌
session = api.create_session(num_games=3)
for i in range(10):  # Vrei 10, dar ai declarat doar 3!
    game = api.create_game(session['session_id'])  # CRASH după al 3-lea!

# CORECT ✅
session = api.create_session(num_games=10)  # Declară corect de la început!
for i in range(10):
    game = api.create_game(session['session_id'])
```

---

## 🎯 Implementare în GUI

### Workflow în GUI (IMPLEMENTAT ✅)

#### 1. **Login Page** → Pagina de start

- Tab "🔐 Login" sau Tab "📝 Înregistrare"
- După succes → Dashboard

#### 2. **Dashboard** → Hub principal

- Butoane quick actions:
  - ✅ "🎯 Creează Sesiune Nouă" → Create Session Page
  - "🎲 Joacă Acum" → Game Page (verifică sesiune activă)
  - "📊 Vezi Statistici" → Stats Page
  - "🏆 Leaderboard" → Leaderboard Page

#### 3. **Create Session Page** → Configurare sesiune

- Form cu date mock pre-completate:
  - num_games = 3 (demo)
  - difficulty = "normal"
  - max_misses = 6
  - seed = 42
- Butoane:
  - ✅ "✅ Creează Sesiune" → API POST /sessions → Game Page
  - "🔄 Reset Mock" → Resetează la valori inițiale
  - "❌ Anulează" → Sessions Page

#### 4. **Game Page** → Joc activ

**CAZUL A: Nicio sesiune activă**

- Mesaj: "⚠️ Nu ai o sesiune activă!"
- Butoane:
  - "➕ Creează Sesiune Nouă" → Create Session Page
  - "📋 Vezi Sesiuni" → Sessions Page

**CAZUL B: Sesiune activă, fără joc**

- Afișează info sesiune
- Buton: ✅ "🎲 Creează Joc Nou" → API POST /sessions/{id}/games
- După creare → Refresh page (CAZUL C)

**CAZUL C: Joc activ (IN_PROGRESS)**

- Afișează:
  - Pattern (ex: "s\*\*\*\*t")
  - Litere corecte
  - Litere greșite
  - Greșeli rămase
- Input: literă sau cuvânt
- Buton: ✅ "✅ Trimite Ghicire" → API POST /guess → Refresh page
- Butoane extra:
  - "🔄 Reîmprospătează"
  - "🚫 Abandonează Joc" → API POST /abort

**CAZUL D: Joc terminat (WON/LOST)**

- Afișează rezultat:
  - "🎉 AI CÂȘTIGAT!" sau "💔 AI PIERDUT!"
  - Cuvântul complet (dacă LOST)
  - Scor, timp, ghiciri
- Butoane:
  - "🎲 Joc Următor" → Creează alt joc (CAZUL B)
  - "📊 Statistici Sesiune" → Dialog cu stats
  - "📋 Vezi Toate Sesiunile" → Sessions Page

#### 5. **Sessions Page** → Lista sesiuni

- Tabel cu toate sesiunile
- Click pe sesiune → Dialog detalii
- Butoane:
  - "➕ Creează Sesiune Nouă" → Create Session Page
  - "🔄 Reîmprospătează Listă"

#### 6. **Stats/Leaderboard/Settings** → Pagini auxiliare

- Statistici utilizator
- Clasament global
- Setări și log viewer

---

## 🔒 Validări și Siguranță

### 1. **Verificări obligatorii în UI**

```python
# Verificare token înainte de orice request
if not self.api.token:
    messagebox.showerror("Eroare", "Trebuie să fii autentificat!")
    self.show_login_page()
    return

# Verificare sesiune activă înainte de creare joc
if not self.current_session:
    messagebox.showwarning("Atenție", "Creează o sesiune mai întâi!")
    self.show_create_session_page()
    return

# Verificare joc activ înainte de ghicire
if not self.current_game:
    messagebox.showwarning("Atenție", "Creează un joc mai întâi!")
    return
```

### 2. **Try-Catch pe toate API calls**

```python
try:
    result = self.api.create_session(num_games=3)
    self.current_session = result
    logger.info(f"✅ Session created: {result['session_id']}")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 422:
        error_detail = e.response.json().get('detail', 'Validation error')
        messagebox.showerror("Eroare Validare", f"Date invalide:\n{error_detail}")
    else:
        messagebox.showerror("Eroare", f"HTTP {e.response.status_code}: {str(e)}")
    logger.log_exception(e, "create_session")
except Exception as e:
    messagebox.showerror("Eroare", f"Eroare neașteptată:\n{str(e)}")
    logger.log_exception(e, "create_session")
```

### 3. **Logging pe toate acțiunile critice**

```python
# ÎNAINTE de acțiune
logger.log_user_action("CREATE_SESSION", f"num_games={num_games}, difficulty={difficulty}")

# DUPĂ succes
logger.info(f"✅ Session created: {result['session_id']}")

# DUPĂ eroare
logger.log_exception(e, "create_session")
```

---

## 📊 State Management în GUI

### Variabile de stare (current state)

```python
class HangmanGUI:
    def __init__(self):
        self.api = HangmanAPI()           # API wrapper
        self.current_session = None       # Sesiune activă
        self.current_game = None          # Joc activ
        self.server_process = None        # Proces server
```

### Reguli pentru state:

1. **current_session** se setează când:

   - ✅ Creezi sesiune nouă
   - ✅ Selectezi sesiune din listă
   - ❌ Se șterge când: Abandonezi sesiune / Logout

2. **current_game** se setează când:

   - ✅ Creezi joc nou
   - ✅ Jocul se termină (WON/LOST) → se șterge automat
   - ❌ Se șterge când: Abandonezi joc / Creezi joc nou

3. **Tranziții între pagini** (safe navigation):

   ```python
   # Game Page verifică current_session
   if not self.current_session:
       # Afișează mesaj + butoane redirect
       return

   # Active Game Interface verifică current_game
   if not self.current_game:
       # Afișează "Creează Joc Nou" interface
       return
   ```

---

## 🧪 Scenarii de Testare

### ✅ Scenariu Happy Path (Totul merge bine)

```
1. Pornește GUI → Auto-start server
2. Register: newuser@test.com / parola123 / Player
3. Auto-login după register
4. Dashboard → Click "Creează Sesiune Nouă"
5. Lasă date mock (3 jocuri, normal, 6 greșeli, seed 42)
6. Click "Creează Sesiune" → SUCCESS
7. Game Page → Click "Creează Joc Nou" → SUCCESS
8. Joc activ → Ghicește "a" → SUCCESS
9. Ghicește "e" → SUCCESS
10. Continuă până la WON sau LOST
11. Click "Joc Următor" → Repeat 7-10
12. După 3 jocuri → "Toate jocurile create!"
13. Click "Statistici Sesiune" → Vezi rezultate
```

### 🔴 Scenariu cu Erori (Testare robustețe)

```
1. Dashboard → "Joacă Acum" FĂRĂ sesiune activă
   → ⚠️ Mesaj: "Nu ai sesiune activă" + redirect buttons ✅

2. Create Session → difficulty="medium"
   → ❌ 422 Validation Error: "Invalid difficulty" ✅

3. Game Page → Ghicește fără să creezi joc
   → ⚠️ Afișează "Creează Joc Nou" interface ✅

4. Creează 4 jocuri când num_games=3
   → ❌ API error: "Session limit reached" (handled in backend)

5. Server down → Orice request
   → ❌ Connection error → Messagebox + logging ✅
```

---

## 🎓 Best Practices pentru Dezvoltare

### 1. **Folosește Loading Spinners pentru operații async**

```python
self.show_loading("Se creează jocul...")
try:
    game = self.api.create_game(session_id)
finally:
    self.hide_loading()
```

### 2. **Refresh UI după modificări**

```python
# După creare joc
self.current_game = game
self.show_game_page()  # Refresh pentru a vedea pattern nou
```

### 3. **Confirmări pentru acțiuni distructive**

```python
if not messagebox.askyesno("Confirmare", "Sigur vrei să abandonezi?"):
    return
```

### 4. **Logging consistent**

```python
logger.log_navigation("PAGE_OLD", "PAGE_NEW")  # Tracking pages
logger.log_user_action("ACTION", "details")     # User interactions
logger.log_api_call("METHOD", "/endpoint")      # API calls
logger.log_exception(e, "context")              # Errors
```

---

## 📝 Checklist Implementare

### Backend Endpoints (Server) - ✅ TOATE IMPLEMENTATE

- [x] POST /auth/register
- [x] POST /auth/login
- [x] POST /auth/refresh
- [x] POST /sessions
- [x] GET /sessions/{id}
- [x] POST /sessions/{id}/abort
- [x] GET /sessions/{id}/games
- [x] GET /sessions/{id}/stats
- [x] POST /sessions/{id}/games (Creare joc)
- [x] GET /sessions/{id}/games/{gid}/state
- [x] POST /sessions/{id}/games/{gid}/guess
- [x] GET /sessions/{id}/games/{gid}/history
- [x] POST /sessions/{id}/games/{gid}/abort
- [x] GET /users/{id}/stats
- [x] GET /stats/global
- [x] GET /leaderboard
- [x] GET /admin/dictionaries
- [x] POST /admin/dictionaries
- [x] PATCH /admin/dictionaries/{id}
- [x] DELETE /admin/dictionaries/{id}

### Frontend GUI (Client) - ✅ WORKFLOW COMPLET IMPLEMENTAT

- [x] Login/Register Pages (cu tabs)
- [x] Dashboard (cu quick actions)
- [x] Create Session Page (cu date mock)
- [x] Sessions List Page (cu detalii)
- [x] Game Page - COMPLET:
  - [x] Verificare sesiune activă
  - [x] Interface creare joc nou
  - [x] Interface joc activ (ghicire)
  - [x] Display pattern și status
  - [x] Rezultat final (WON/LOST)
  - [x] Buton "Joc Următor"
  - [x] Dialog statistici sesiune
  - [x] Abandonare joc/sesiune
- [x] Stats Page
- [x] Leaderboard Page
- [x] Settings Page (cu log viewer)
- [x] Loading Spinners
- [x] Error Handling
- [x] Logging System
- [x] Auto Server Start/Stop

### Validări și Siguranță - ✅ IMPLEMENTATE

- [x] Verificare autentificare pe toate requests
- [x] Verificare sesiune activă înainte de creare joc
- [x] Try-catch pe toate API calls
- [x] Validare input utilizator (guess non-empty)
- [x] Confirmări pentru acțiuni distructive
- [x] Logging comprehensiv (toate acțiunile)
- [x] Display friendly error messages

---

## 🚀 Status Final: GATA DE PRODUCȚIE! ✅

**Workflow-ul este COMPLET și SIGUR:**

- ✅ Ordinea corectă a operațiilor
- ✅ Toate validările în loc
- ✅ Error handling robust
- ✅ Logging comprehensiv
- ✅ UI intuitiv cu ghidare clară
- ✅ State management corect
- ✅ Toate endpoint-urile backend acoperite

**Poți folosi GUI-ul în siguranță fără crash-uri!** 🎉
