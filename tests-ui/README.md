# 🧪 Teste UI - Hangman GUI Client

Acest folder conține teste pentru interfața grafică (GUI) și componente client.

## 📋 Teste Disponibile

### 1. `test_server_startup.py`

Testează pornirea serverului și conectivitatea de bază.

**Ce testează:**

- ✅ Verifică dacă serverul deja rulează
- ✅ Pornește serverul dacă nu rulează
- ✅ Așteaptă până devine disponibil (max 30s)
- ✅ Testează endpoint-uri esențiale (healthz, docs, API)
- ✅ Testează fluxul de autentificare (register + login)

**Rulare:**

```bash
python tests-ui/test_server_startup.py
```

**Output așteptat:**

```
🧪 TESTE UI - PORNIRE SERVER ȘI CONECTIVITATE
============================================================
🔍 Test 1: Verifică server existent...
✅ Serverul deja rulează!

🔌 Test 3: Testez endpoint-uri API...
  ✅ Health check: OK (200)
  ✅ OpenAPI docs: OK (200)
  ✅ API root: OK (200)

🔐 Test 4: Testez autentificare...
  📝 Înregistrez user: test_ui_1234@test.com
  ✅ User creat: u_123
  🔓 Login cu user: test_ui_1234@test.com
  ✅ Login OK, token: eyJhbGciOiJIUzI1NiIs...

============================================================
✅ TOATE TESTELE AU TRECUT!
============================================================
```

### 2. `test_gui_components.py`

Testează componentele GUI fără a lansa interfața grafică.

**Ce testează:**

- ✅ Inițializare HangmanAPI wrapper
- ✅ Verifică că toate metodele API există
- ✅ Verifică structura clasei HangmanGUI
- ✅ Verifică import-urile necesare

**Rulare:**

```bash
python tests-ui/test_gui_components.py
```

**Output așteptat:**

```
🧪 TESTE UI - COMPONENTE GUI
============================================================

📦 Test 4: Verifică import-uri...
  ✅ Toate cele 8 module sunt disponibile

🧩 Test 1: Inițializare HangmanAPI...
  ✅ HangmanAPI inițializat corect

🔧 Test 2: Verifică metode API...
  ✅ Toate cele 17 metode există

🎨 Test 3: Verifică structura HangmanGUI...
  ✅ Toate cele 17 metode GUI există

============================================================
✅ TOATE TESTELE AU TRECUT! (4/4)
============================================================
```

## 🚀 Rulare Rapidă

**Test complet:**

```bash
# Test 1: Componente
python tests-ui/test_gui_components.py

# Test 2: Server + API
python tests-ui/test_server_startup.py
```

**Test înainte de lansare GUI:**

```bash
# Verifică că totul e OK
python tests-ui/test_server_startup.py && python client-examples/gui_client_pro.py
```

## 🔧 Debugging

Dacă testele eșuează:

1. **Server nu pornește:**

   - Verifică că portul 8000 nu e folosit: `netstat -ano | findstr :8000`
   - Verifică logs: output-ul va arăta STDOUT/STDERR al serverului

2. **Import errors:**

   - Verifică că ai toate dependențele: `pip install -r server/requirements.txt`
   - Verifică că tkinter e instalat (vine cu Python pe Windows)

3. **API errors:**
   - Verifică că serverul rulează: `curl http://localhost:8000/healthz`
   - Verifică swagger docs: `http://localhost:8000/docs`

## 📊 Rezultate

| Test                     | Scop                           | Durată Medie |
| ------------------------ | ------------------------------ | ------------ |
| `test_gui_components.py` | Verifică cod GUI               | ~0.5s        |
| `test_server_startup.py` | Pornește server + testează API | ~5-10s       |

## 🎯 Next Steps

După ce testele trec:

1. ✅ Lansează GUI: `python client-examples/gui_client_pro.py`
2. ✅ Testează manual workflow-ul complet
3. ✅ Raportează orice bug găsit
