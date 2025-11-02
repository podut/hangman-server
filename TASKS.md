# Hangman Server - Task List

## Status de implementare a cerințelor

Legendă:

- ✅ **Implementat complet**
- ⚠️ **Implementat parțial**
- ❌ **Nu este implementat**

---

## 1. Autentificare & Conturi

| Cerință                 | Status | Endpoint                     | Note                                     |
| ----------------------- | ------ | ---------------------------- | ---------------------------------------- |
| Înregistrare utilizator | ✅     | `POST /api/v1/auth/register` | Email, parolă, nickname opțional         |
| Login                   | ✅     | `POST /api/v1/auth/login`    | Returnează JWT access & refresh tokens   |
| Refresh token           | ✅     | `POST /api/v1/auth/refresh`  | Regenerare access token cu refresh token |
| Profil utilizator       | ✅     | `GET /api/v1/users/me`       | Returnează datele utilizatorului curent  |
| Reset parolă            | ❌     | -                            | Nu este implementat                      |
| Ștergere cont (GDPR)    | ❌     | -                            | Nu este implementat                      |

**Rezumat**: ⚠️ **4/6 funcționalități implementate**

---

## 2. Sesiuni & Seturi de Jocuri

| Cerință                   | Status | Endpoint                                   | Note                                                                                             |
| ------------------------- | ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------ |
| Creare sesiune            | ✅     | `POST /api/v1/sessions`                    | Suport pentru 1, 100 sau N jocuri                                                                |
| Parametri sesiune         | ✅     | -                                          | `num_games`, `dictionary_id`, `difficulty`, `language`, `max_misses`, `allow_word_guess`, `seed` |
| Obținere detalii sesiune  | ✅     | `GET /api/v1/sessions/{session_id}`        | Include progres (jocuri finalizate/totale)                                                       |
| Sumar sesiune             | ✅     | `GET /api/v1/sessions/{session_id}/stats`  | Win rate, medii ghiciri, statistici                                                              |
| Listă jocuri în sesiune   | ✅     | `GET /api/v1/sessions/{session_id}/games`  | Cu paginare (page, page_size)                                                                    |
| Închidere/abandon sesiune | ✅     | `POST /api/v1/sessions/{session_id}/abort` | Închide sesiunea și toate jocurile IN_PROGRESS                                                   |

**Rezumat**: ✅ **6/6 funcționalități implementate**

---

## 3. Joc Hangman

| Cerință                    | Status | Endpoint                                                    | Note                                                      |
| -------------------------- | ------ | ----------------------------------------------------------- | --------------------------------------------------------- |
| Creare joc                 | ✅     | `POST /api/v1/sessions/{session_id}/games`                  | Cuvânt secret ales automat de server                      |
| Pattern inițial            | ✅     | -                                                           | Pattern cu `*` pentru litere ascunse                      |
| Obținere stare joc         | ✅     | `GET /api/v1/sessions/{session_id}/games/{game_id}/state`   | Pattern, litere ghicite/greșite, încercări rămase, status |
| Ghicire literă             | ✅     | `POST /api/v1/sessions/{session_id}/games/{game_id}/guess`  | Body: `{"letter": "a"}`                                   |
| Ghicire cuvânt             | ✅     | `POST /api/v1/sessions/{session_id}/games/{game_id}/guess`  | Body: `{"word": "student"}`                               |
| Istoric ghiciri            | ✅     | `GET /api/v1/sessions/{session_id}/games/{game_id}/history` | Lista completă de ghiciri cu timpi                        |
| Închidere/abandon joc      | ✅     | `POST /api/v1/sessions/{session_id}/games/{game_id}/abort`  | Setează status=ABORTED                                    |
| Suport diacritice          | ✅     | -                                                           | Normalizare ăâîșț                                         |
| Potrivire case-insensitive | ✅     | -                                                           | Toate comparațiile sunt lowercase                         |
| Status joc                 | ✅     | -                                                           | `IN_PROGRESS`, `WON`, `LOST`, `ABORTED`                   |

**Rezumat**: ✅ **10/10 funcționalități implementate**

---

## 4. Statistici & Ierarhii

| Cerință                      | Status | Endpoint                                         | Note                                                                                                 |
| ---------------------------- | ------ | ------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| Statistici per sesiune       | ✅     | `GET /api/v1/sessions/{session_id}/stats`        | Win rate, medii ghiciri, scor compozit                                                               |
| Statistici per utilizator    | ✅     | `GET /api/v1/users/{user_id}/stats`              | Cu filtrare perioadă: all, 30d, 7d, 1d                                                               |
| Filtrare perioadă statistici | ✅     | `?period=all\|30d\|7d\|1d`                       | Implementat pentru user stats și global stats                                                        |
| Leaderboard                  | ✅     | `GET /api/v1/leaderboard`                        | Suport metric & period cu filtrare reală                                                             |
| Metrică leaderboard          | ✅     | `?metric=win_rate\|avg_guesses\|composite_score` | Toate 3 metrice implementate                                                                         |
| Perioadă leaderboard         | ✅     | `?period=all\|30d\|7d\|1d`                       | Filtrare funcțională pe toate perioadele                                                             |
| Statistici globale           | ✅     | `GET /api/v1/stats/global`                       | Cu filtrare perioadă                                                                                 |
| Scor compozit                | ✅     | -                                                | Formula calculată și stocată: 1000*won - 10*guesses - 5*wrong - 40*wrong_words - 0.2*time + 2*length |

**Rezumat**: ✅ **8/8 funcționalități implementate complet**

---

## 5. Administrare Dicționare

| Cerință                    | Status | Endpoint                                    | Note                                                                 |
| -------------------------- | ------ | ------------------------------------------- | -------------------------------------------------------------------- |
| Listă dicționare           | ✅     | `GET /api/v1/admin/dictionaries`            | Returnează toate dicționarele (fără cuvinte)                         |
| Import dicționar           | ✅     | `POST /api/v1/admin/dictionaries`           | Creează dicționar nou cu validare (min 10 cuvinte)                   |
| Activare/editare dicționar | ✅     | `PATCH /api/v1/admin/dictionaries/{id}`     | Actualizare nume și status active                                    |
| Eșantion cuvinte           | ✅     | `GET /api/v1/admin/dictionaries/{id}/words` | Cu parametru sample pentru eșantion aleatoriu                        |
| Rol admin                  | ✅     | -                                           | Primul user înregistrat devine admin, verificare cu get_admin_user() |
| Dicționar implicit         | ✅     | -                                           | `dict_ro_basic.txt` cu 20 cuvinte românești                          |
| Evitare repetare cuvinte   | ✅     | -                                           | Fiecare cuvânt folosit o singură dată per sesiune                    |

**Rezumat**: ✅ **7/7 funcționalități implementate**

---

## 6. Sănătate & Utilitare

| Cerință      | Status | Endpoint       | Note                         |
| ------------ | ------ | -------------- | ---------------------------- |
| Health check | ✅     | `GET /healthz` | Returnează `{"ok": true}`    |
| Versiune API | ✅     | `GET /version` | Returnează versiune și build |
| Timp server  | ✅     | `GET /time`    | Returnează UTC ISO 8601      |

**Rezumat**: ✅ **3/3 funcționalități implementate**

---

## 7. Cerințe Non-Funcționale

| Cerință                | Status | Note                                                              |
| ---------------------- | ------ | ----------------------------------------------------------------- |
| **Securitate**         |        |                                                                   |
| HTTPS obligatoriu      | ❌     | Server rulează HTTP (config deploy)                               |
| JWT autentificare      | ✅     | Implementat cu Jose                                               |
| Rate limiting          | ❌     | Nu este implementat                                               |
| Protecție brute-force  | ❌     | Nu este implementat                                               |
| CORS                   | ❌     | Nu este configurat                                                |
| Hash parolă securizat  | ✅     | bcrypt via passlib                                                |
| **Performanță**        |        |                                                                   |
| P95 < 200ms            | ❓     | Nu este măsurat                                                   |
| P99 < 400ms            | ❓     | Nu este măsurat                                                   |
| Throughput 300 req/s   | ❓     | Nu este testat                                                    |
| **Disponibilitate**    |        |                                                                   |
| 99.5% uptime           | ❓     | Nu este monitorizat                                               |
| **Scalabilitate**      |        |                                                                   |
| Stateless design       | ❌     | In-memory storage (nu este stateless)                             |
| Cache                  | ❌     | Redis în requirements dar nefolosit                               |
| **Internaționalizare** |        |                                                                   |
| Suport română          | ✅     | Dicționar RO, diacritice                                          |
| Extensibil EN          | ⚠️     | Parametru `language` există dar doar RO implementat               |
| **Observabilitate**    |        |                                                                   |
| Loguri structurate     | ❌     | Loguri implicite Uvicorn                                          |
| Metrici                | ❌     | Nu sunt colectate                                                 |
| Tracing (X-Request-ID) | ❌     | Nu este implementat                                               |
| Audit                  | ❌     | Nu este implementat                                               |
| **Persistență**        |        |                                                                   |
| Bază de date           | ❌     | In-memory dictionaries (PostgreSQL în requirements dar nefolosit) |
| Migrații               | ❌     | Nu există                                                         |
| **Portabilitate**      |        |                                                                   |
| Dockerfile             | ✅     | Există în repo                                                    |
| Container deployment   | ⚠️     | Dockerfile există dar nevalidat                                   |

**Rezumat**: ⚠️ **Multe cerințe non-funcționale lipsesc sau nu sunt măsurate**

---

## 8. API Design & Standards

| Cerință                  | Status | Note                                                                      |
| ------------------------ | ------ | ------------------------------------------------------------------------- |
| Bază `/api/v1`           | ✅     | Toate endpoint-urile sunt sub `/api/v1`                                   |
| Authorization header     | ✅     | `Bearer <JWT>`                                                            |
| Content-Type JSON        | ✅     | FastAPI default                                                           |
| Idempotency-Key          | ❌     | Nu este implementat                                                       |
| Paginare                 | ✅     | Query params `?page=&page_size=` implementate pentru list_session_games   |
| Link headers             | ❌     | Nu sunt implementate                                                      |
| Coduri HTTP corecte      | ✅     | 200, 201, 400, 401, 403, 404, 409, 422                                    |
| Format eroare structurat | ⚠️     | FastAPI default (nu urmeaza formatul cerut cu `error.code`, `request_id`) |

**Rezumat**: ⚠️ **5/8 standarde implementate**

---

## 9. Modele de Date

| Model        | Status | Note                                                                                                                  |
| ------------ | ------ | --------------------------------------------------------------------------------------------------------------------- |
| User         | ✅     | `user_id`, `email`, `nickname`, `password`, `created_at`                                                              |
| Session      | ✅     | `session_id`, `user_id`, `num_games`, `params`, `status`, timestamps                                                  |
| Game         | ✅     | `game_id`, `session_id`, `status`, `pattern`, `guessed_letters`, `wrong_letters`, `remaining_misses`, `total_guesses` |
| Guess        | ✅     | `index`, `type`, `value`, `correct`, `pattern_after`, `timestamp`                                                     |
| SessionStats | ⚠️     | Calculat dinamic (nu este stocat)                                                                                     |
| Result       | ⚠️     | Încorporat în `game.result`                                                                                           |

**Rezumat**: ✅ **Modelele de bază sunt implementate**

---

## 10. Reguli de Joc & Scor

| Cerință                  | Status | Note                                                                            |
| ------------------------ | ------ | ------------------------------------------------------------------------------- |
| Selecție cuvânt server   | ✅     | Random choice din dicționar                                                     |
| Seed reproducibil        | ✅     | Parametru `seed` în sesiune                                                     |
| Pattern actualizare      | ✅     | Litera corectă dezvăluită în poziții                                            |
| Ghicire literă           | ✅     | Actualizare pattern, wrong_letters                                              |
| Ghicire cuvânt           | ✅     | Win instant sau penalitate                                                      |
| Penalitate cuvânt greșit | ✅     | -2 misses pentru cuvânt greșit                                                  |
| Condiție WON             | ✅     | Pattern fără `*` sau cuvânt corect                                              |
| Condiție LOST            | ✅     | `remaining_misses <= 0`                                                         |
| Condiție ABORTED         | ✅     | Status ABORTED adăugat pentru jocuri/sesiuni abandonate                         |
| Scor compozit formula    | ✅     | Formula: 1000*won - 10*guesses - 5*wrong - 40*wrong_words - 0.2*time + 2*length |
| Stocarea scorului        | ✅     | Scorul calculat automat și stocat la finalizarea jocului (WON/LOST)             |

**Rezumat**: ✅ **11/11 reguli implementate complet**

---

## 11. Testare & Validare

| Cerință                 | Status | Note                                                                                                 |
| ----------------------- | ------ | ---------------------------------------------------------------------------------------------------- |
| Teste unit              | ✅     | `tests/test_game_logic.py` cu 9 teste pentru normalize, update_pattern, calculate_score (toate trec) |
| Teste integrare         | ❌     | Nu există                                                                                            |
| Contracte API (OpenAPI) | ⚠️     | FastAPI generează automat dar fără validare explicită                                                |
| Teste Postman/CI        | ❌     | Nu există                                                                                            |
| Teste load (300 req/s)  | ❌     | Nu există                                                                                            |
| Seed determinism        | ✅     | Parametru seed funcțional                                                                            |

**Rezumat**: ⚠️ **2/6 cerințe implementate**

---

## 12. Documentație

| Cerință                     | Status | Note                                                              |
| --------------------------- | ------ | ----------------------------------------------------------------- |
| README.md (root)            | ✅     | Există în repo                                                    |
| docs/README.md              | ✅     | Există în repo                                                    |
| OpenAPI spec (openapi.yaml) | ⚠️     | Generat automat de FastAPI la `/docs` dar nu există fișier static |
| Client examples             | ✅     | `client-examples/python_client.py`                                |
| Postman collection          | ❌     | Nu există                                                         |

**Rezumat**: ⚠️ **3/5 documente prezente**

---

## 📊 Sumar General

### Funcționalități Implementate

| Categorie                    | Implementat | Total | Procent |
| ---------------------------- | ----------- | ----- | ------- |
| **Autentificare & Conturi**  | 4           | 6     | 67%     |
| **Sesiuni & Jocuri**         | 6           | 6     | 100%    |
| **Joc Hangman**              | 10          | 10    | 100%    |
| **Statistici & Leaderboard** | 8           | 8     | 100%    |
| **Admin Dicționare**         | 7           | 7     | 100%    |
| **Sănătate & Utilitare**     | 3           | 3     | 100%    |
| **API Standards**            | 5           | 8     | 63%     |
| **Reguli Joc & Scor**        | 11          | 11    | 100%    |
| **Testare**                  | 2           | 6     | 33%     |
| **Documentație**             | 3           | 5     | 60%     |

### Top Priorități pentru Completare

#### � Completate În Această Sesiune

1. ✅ **Scor compozit**: Calculat și stocat automat (formula: 1000*won - 10*guesses - 5*wrong - 40*wrong_words - 0.2*time + 2*length)
2. ✅ **Statistici utilizator**: `GET /api/v1/users/{user_id}/stats` cu filtrare perioadă
3. ✅ **Filtrare perioadă**: Implementat pentru stats/leaderboard (all, 30d, 7d, 1d)
4. ✅ **Abort operations**: Închidere sesiune/joc cu status ABORTED
5. ✅ **Admin dicționare**: CRUD complet (list/create/update/get words)
6. ✅ **Teste**: Unit tests pentru normalize, update_pattern, calculate_score (9/9 passing)
7. ✅ **Paginare**: Pentru list_session_games (page, page_size)
8. ✅ **Word uniqueness**: Fără repetare cuvinte în aceeași sesiune

#### 🔴 Critice pentru Producție (Nu Implementate)

1. **Persistență**: Migrare de la in-memory la PostgreSQL/SQLAlchemy
2. **Rate limiting**: Protecție împotriva abuzului
3. **HTTPS & CORS**: Configurare producție
4. **Observabilitate**: Loguri structurate, metrici, tracing (X-Request-ID)

#### � Nice-to-Have (Nu în Scope Local)

5. **Reset parolă**: Flow complet cu email
6. **Ștergere cont**: GDPR compliance
7. **Idempotency**: Suport pentru operații duplicate
8. **Format eroare structurat**: Cu `error.code` și `request_id`
9. **Teste integrare**: E2E și load testing

---

## 💡 Recomandări Arhitecturale

### Urgent

- [ ] Separare logică în module (auth, game, stats, admin)
- [ ] Service layer pentru business logic
- [ ] Repository pattern pentru acces date
- [ ] Environment variables pentru config (`.env`)

### Mediu Termen

- [ ] Migration de la in-memory la PostgreSQL
- [ ] Redis pentru cache (session state, leaderboard)
- [ ] Background tasks pentru calculul scorurilor
- [ ] WebSocket pentru notificări real-time (opțional)

### Long Term

- [ ] Microservices split (auth, game engine, stats)
- [ ] Event sourcing pentru audit trail
- [ ] Message queue pentru procesare asincronă
- [ ] Kubernetes deployment cu autoscaling

---

**Data generării**: 2025-11-02  
**Versiune server analizată**: 1.0.0  
**Autor**: GitHub Copilot
