# 📊 Logging System - Hangman GUI

Sistem complet de logging pentru debugging și troubleshooting UI.

## 🎯 Caracteristici

### ✅ Ce se loggează:

1. **🔐 Autentificare:**

   - Login attempts (email, success/fail)
   - Register attempts (email, nickname, admin status)
   - Auto-login după register
   - Logout actions

2. **🌐 API Calls:**

   - Toate request-urile (method, endpoint)
   - Response status codes
   - Erori HTTP complete cu detalii
   - Timings

3. **🖱️ Acțiuni Utilizator:**

   - Click-uri pe butoane
   - Navigare între pagini
   - Refresh logs
   - Închidere aplicație

4. **🖥️ Server Management:**

   - Pornire/oprire server
   - PID procesului
   - Timings (cât durează să pornească)
   - Health check status

5. **❌ Erori și Excepții:**
   - Stack traces complete
   - Context (în ce funcție a apărut)
   - Toate nivelurile: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 📝 Format Log

```
YYYY-MM-DD HH:MM:SS | LEVEL    | function_name        | message
```

### Exemplu:

```
2025-11-02 16:21:06 | INFO     | __init__             | 🎮 Inițializare HangmanGUI
2025-11-02 16:21:08 | ERROR    | log_api_call         | API POST /auth/login - FAILED: 401
2025-11-02 16:21:54 | INFO     | info                 | Register SUCCESS: user_id=u_1
```

## 📂 Locație Fișiere

**Path:** `client-examples/logs/`

**Format nume:** `gui_YYYYMMDD_HHMMSS.log`

**Exemple:**

- `gui_20251102_162106.log` - sesiune 02 Nov 2025, 16:21:06
- `gui_20251102_143025.log` - sesiune 02 Nov 2025, 14:30:25

## 🔍 Cum se folosește

### 1. În aplicație (GUI):

1. Deschide aplicația → log-ul se creează automat
2. Navighează la **⚙️ Setări** din menu
3. Vezi ultimele 100 linii în **Log Viewer**

**Butoane disponibile:**

- 🔄 **Reîmprospătează Log** - reload ultimele linii
- 📂 **Deschide fișier log** - deschide în Notepad/editor
- 🗑️ **Șterge console** - curăță afișajul (NU șterge fișierul)

### 2. Manual (fișier):

```bash
# Windows
notepad client-examples\logs\gui_20251102_162106.log

# Sau din File Explorer
explorer client-examples\logs
```

## 🧪 Debugging cu Logs

### Exemplu 1: Troubleshoot Login Failed

**Problema:** User nu se poate loga

**Pași:**

1. Caută în log: `LOGIN_ATTEMPT`
2. Verifică ce email a folosit
3. Caută eroarea: `API POST /auth/login - FAILED`
4. Citește stack trace-ul pentru detalii

**Exemplu găsit:**

```
2025-11-02 16:21:08 | INFO  | log_user_action  | USER_ACTION: LOGIN_ATTEMPT | email=player@test.com
2025-11-02 16:21:10 | ERROR | log_api_call     | API POST /auth/login - FAILED: 401 Unauthorized
```

**Soluție:** User-ul `player@test.com` nu există → trebuie creat mai întâi (Register)

### Exemplu 2: Server nu pornește

**Problema:** GUI se blochează la pornire

**Pași:**

1. Caută: `SERVER: START_ATTEMPT`
2. Verifică dacă apare `SERVER: PROCESS_STARTED` cu PID
3. Caută `SERVER: READY` sau `SERVER_TIMEOUT`

**Exemplu găsit:**

```
2025-11-02 16:21:06 | INFO  | log_server_event | SERVER: START_ATTEMPT
2025-11-02 16:21:06 | INFO  | log_server_event | SERVER: ALREADY_RUNNING
```

**Soluție:** Serverul deja rula → OK, nu e problemă

### Exemplu 3: Crash/Exception

**Problema:** Aplicația crashuiește

**Pași:**

1. Caută: `EXCEPTION` sau `CRITICAL`
2. Citește stack trace-ul complet
3. Verifică context-ul (în ce funcție)

**Exemplu găsit:**

```
2025-11-02 16:21:10 | ERROR | log_exception | EXCEPTION in login: 401 HTTPError
Traceback (most recent call last):
  File "gui_client_pro.py", line 60, in login
    resp.raise_for_status()
requests.exceptions.HTTPError: 401 Client Error: Unauthorized
```

**Soluție:** Verifică credențiale sau dacă user-ul există

## 📋 Niveluri de Logging

| Nivel        | Când se folosește             | Exemplu                                |
| ------------ | ----------------------------- | -------------------------------------- |
| **DEBUG**    | Detalii tehnice, debugging    | `Loading spinner displayed`            |
| **INFO**     | Evenimente normale importante | `Login SUCCESS: user_id=u_1`           |
| **WARNING**  | Atenționări, nu erori         | `Login validation failed: empty email` |
| **ERROR**    | Erori recuperabile            | `API POST /auth/login - FAILED: 401`   |
| **CRITICAL** | Erori fatale, crash           | `Application crashed`                  |

## 🔧 Configurare

### Schimbă nivelul de logging:

**În `ui_logger.py`:**

```python
# Pentru mai multe detalii în console
console_handler.setLevel(logging.DEBUG)  # default: INFO

# Pentru mai puține detalii în fișier
file_handler.setLevel(logging.INFO)  # default: DEBUG
```

### Schimbă locația log-urilor:

**În `gui_client_pro.py`:**

```python
# Schimbă path-ul
log_dir = os.path.join(os.path.dirname(__file__), "my_logs")
logger = init_logger(log_dir)
```

## 💡 Tips & Tricks

### 1. Găsește rapid erori:

```bash
# Windows PowerShell
Select-String "ERROR" client-examples\logs\*.log

# Sau filtrează în Log Viewer din GUI
```

### 2. Monitorizare live:

```bash
# Windows PowerShell (tail -f equivalent)
Get-Content client-examples\logs\gui_20251102_162106.log -Wait -Tail 20
```

### 3. Statistici sesiune:

```bash
# Numără câte apeluri API au fost
Select-String "API " client-examples\logs\gui_*.log | Measure-Object
```

### 4. Timeline evenimente:

Toate log-urile au timestamp → sortează cronologic pentru a vedea succesiunea evenimentelor

## 🎓 Best Practices

1. ✅ **Păstrează log-urile** - utile pentru reproducere bug-uri
2. ✅ **Verifică după erori** - citește log-ul când ceva nu merge
3. ✅ **Șterge periodic** - log-urile vechi ocupă spațiu
4. ✅ **Raportează cu log** - când raportezi bug, atașează log-ul relevant
5. ✅ **Nu modifica manual** - log-urile sunt pentru citire

## ❓ FAQ

**Q: Log-urile ocupă mult spațiu?**
A: Nu, un log tipic = 10-50 KB. Șterge manual dacă e necesar.

**Q: Pot șterge log-urile vechi?**
A: Da, safe să ștergi orice fișier `.log` din folder.

**Q: De ce văd "funcName" ciudate?**
A: Sunt nume interne de funcții Python - normal.

**Q: Pot exporta log-ul?**
A: Da, e text simplu. Copy-paste sau folosește butonul "📂 Deschide fișier".

**Q: Parola apare în log?**
A: NU! Doar email-ul. Parolele NU sunt loggate niciodată.

## 📞 Support

Dacă întâmpini probleme:

1. Verifică log-ul mai întâi
2. Caută erori cu `ERROR` sau `EXCEPTION`
3. Citește stack trace-ul
4. Raportează cu log-ul atașat

---

**Happy Debugging! 🐛🔨**
