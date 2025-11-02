# 🎮 Hangman Server API# Hangman Server Project

REST API complet pentru jocul Hangman (Spânzurătoarea), construit cu FastAPI.Proiect server Hangman cu API REST și client Python.

## ✨ Features## Quick Start

### Core Features```bash

- 🔐 **Autentificare JWT** - Login/Register cu token-uri securizate# Install dependencies

- 🎯 **Sesiuni multi-joc** - Management complet de sesiuni și jocuricd server

- 📚 **Dicționare multiple** - Română și engleză cu dificulăți variabilepip install -r requirements.txt

- 👤 **Profile utilizator** - Statistici, export date, ștergere cont

- 📊 **Admin panel** - Statistici globale pentru administratori# Run server

cd src

### Advanced Featurespython main.py

- 🔌 **WebSocket** - Comunicare bidirectională real-time (`/ws`)```

- 📈 **Prometheus metrics** - `/metrics` endpoint pentru monitoring

- 🔁 **Idempotency** - Protecție împotriva request-urilor duplicateServer: http://localhost:8000

- 🔒 **TLS/SSL** - Configurare opțională pentru HTTPSDocs: http://localhost:8000/docs

- 📋 **OpenAPI export** - Spec static în YAML/JSON

## Test Client

### Infrastructure

- ⏱️ **Rate limiting** - Protecție împotriva abuzului```bash

- 🆔 **Request ID tracking** - Trace complet pentru fiecare requestcd client-examples

- 📝 **Logging structurat** - JSON logspython python_client.py

- 🚨 **Error handling** - Mesaje de eroare consistente```

- 📄 **Paginare** - Link headers pentru navigare

Vezi `docs/README.md` pentru documentație completă.

## 🚀 Quick Start

```bash
# Install dependencies
cd server
pip install -r requirements.txt

# Run server
python -m uvicorn src.main:app --reload
```

Server: **http://localhost:8000**

## 📚 Documentație

- **Swagger UI**: http://localhost:8000/docs
- **Prometheus Metrics**: http://localhost:8000/metrics
- **[Implementation Report](IMPLEMENTATION_REPORT.md)** - Documentație completă
- **[Verification Report](VERIFICATION_REPORT.md)** - Conformitate KnowledgeBase

## 🧪 Teste

```bash
# Run all tests
pytest -v

# WebSocket manual test
python test_websocket.py
```

**Status**: ✅ 12/12 automated tests passing

## 🔌 WebSocket Example

```javascript
const ws = new WebSocket('ws://localhost:8000/ws?token=' + token);
ws.onmessage = (e) => console.log(JSON.parse(e.data));
ws.send(JSON.stringify({ type: 'ping', data: {} }));
```

## 📊 Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'hangman-api'
    static_configs:
      - targets: ['localhost:8000']
```

## 🔁 Idempotency

```bash
curl -X POST http://localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: unique-key-123" \
  -d '{"num_games":3,"dictionary_id":"dict_ro_basic"}'
```

---

**Status**: ✅ Production Ready | 🧪 100% Feature Complete | 📊 Monitoring Active
