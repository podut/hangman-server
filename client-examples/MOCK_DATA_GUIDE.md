# 📋 Ghid Date Mock - Creare Sesiune

## 🎯 Ce sunt datele mock?

Formularul de creare sesiune vine **pre-completat** cu valori de exemplu (mock data) pentru a testa rapid aplicația fără să completezi manual fiecare câmp.

## 📊 Valori Mock Implicite

Când deschizi pagina "Creează Sesiune Nouă", vei găsi următoarele valori pre-completate:

| **Parametru**         | **Valoare Mock** | **Explicație**                              |
| --------------------- | ---------------- | ------------------------------------------- |
| 🎲 **Număr jocuri**   | `3 jocuri`       | Demo - suficient pentru testare rapidă      |
| 🎯 **Dificultate**    | `normal`         | Cuvinte 6-8 litere (balansat)               |
| ❌ **Greșeli maxime** | `6`              | Standard Hangman (6 încercări greșite)      |
| 🌱 **Seed**           | `42`             | Seed popular în testing (reproducibilitate) |
| 📝 **Custom games**   | `5`              | Valoare pentru opțiunea personalizată       |

## 🔄 Cum să folosești datele mock

### Varianta 1: Folosește direct valorile mock

1. Deschide GUI-ul (`python client-examples\gui_client_pro.py`)
2. Login/Register
3. Click pe **"🎯 Creează Sesiune Nouă"** (din Dashboard sau meniu Sesiuni)
4. **Formularul va fi deja completat!**
5. Click direct pe **"✅ Creează Sesiune"**
6. Sesiunea se creează instant cu parametrii mock

### Varianta 2: Modifică valorile mock

1. Deschide formularul (va fi pre-completat)
2. Schimbă ce dorești:
   - Selectează `1 joc` pentru test rapid
   - Sau `100 jocuri` pentru batch
   - Schimbă dificultatea la `hard` (cuvinte 9+ litere)
   - Crește greșelile maxime la `10` pentru mod ușor
   - Șterge seed-ul dacă vrei random
3. Click pe **"✅ Creează Sesiune"**

### Varianta 3: Resetează la mock după modificări

1. Dacă ai modificat ceva și vrei să revii la exemplu
2. Click pe **"🔄 Reset Mock"**
3. Toate valorile se resetează la datele mock inițiale

## 💡 Cazuri de Utilizare

### 🏃 Test Rapid (1 joc)

```
✓ Pre-completat: 3 jocuri → Schimbă la: 1 joc
✓ Pre-completat: normal → Lasă: normal
✓ Pre-completat: 6 greșeli → Lasă: 6
✓ Pre-completat: seed 42 → Lasă: 42
→ Click "Creează" → Joacă imediat!
```

### 📊 Demo Complet (valorile mock)

```
✓ Pre-completat: 3 jocuri → Lasă: 3 jocuri
✓ Pre-completat: normal → Lasă: normal
✓ Pre-completat: 6 greșeli → Lasă: 6
✓ Pre-completat: seed 42 → Lasă: 42
→ Click "Creează" → Perfect pentru demonstrație!
```

### 🎲 Test Batch (100 jocuri)

```
✓ Pre-completat: 3 jocuri → Schimbă la: 100 jocuri
✓ Pre-completat: normal → Schimbă la: auto (mix)
✓ Pre-completat: 6 greșeli → Lasă: 6
✓ Pre-completat: seed 42 → Șterge (pentru random)
→ Click "Creează" → Statistici masive!
```

### 🔬 Test Reproducibilitate (seed fix)

```
✓ Pre-completat: 3 jocuri → Lasă: 3 jocuri
✓ Pre-completat: normal → Lasă: normal
✓ Pre-completat: 6 greșeli → Lasă: 6
✓ Pre-completat: seed 42 → IMPORTANT: Lasă 42!
→ Click "Creează" de 2 ori → Vei primi EXACT aceleași cuvinte!
```

## 🎨 Unde găsești formularul?

### Metoda 1: Din Dashboard

1. Login → Dashboard
2. Click **"🎯 Creează Sesiune Nouă"** (buton mare verde)
3. Formularul se deschide pre-completat

### Metoda 2: Din Meniu Sesiuni

1. Login → Meniu: **"🎯 Sesiuni"**
2. Click **"➕ Creează Sesiune Nouă"** (buton sus-dreapta)
3. Formularul se deschide pre-completat

## 📝 Exemplu de Workflow Complet

```bash
# 1. Pornește GUI
python client-examples\gui_client_pro.py

# 2. Register/Login (GUI)
Email: newuser@test.com
Password: parola123

# 3. Dashboard → "Creează Sesiune Nouă"
# Formularul vine cu:
- 3 jocuri (demo) ✓
- normal difficulty ✓
- 6 greșeli max ✓
- seed 42 ✓

# 4. Click "✅ Creează Sesiune"
# Rezultat:
✅ Sesiune creată!
ID: ses_abc123
Jocuri: 3
Dificultate: normal
Status: active

# 5. Joacă jocurile sau vezi statistici!
```

## 🔧 Personalizare Date Mock

Dacă vrei să schimbi valorile mock implicite, editează în `gui_client_pro.py`:

```python
# Linia ~738
num_games_var = tk.IntVar(value=3)  # Schimbă 3 cu alta

# Linia ~758
num_games_custom.insert(0, "5")  # Schimbă 5 cu alta

# Linia ~770
difficulty_var = tk.StringVar(value="normal")  # Schimbă normal cu easy/hard/auto

# Linia ~783
max_misses_var = tk.IntVar(value=6)  # Schimbă 6 cu alt număr (1-10)

# Linia ~795
seed_entry.insert(0, "42")  # Schimbă 42 cu alt seed sau șterge linia
```

## ✅ Beneficii Date Mock

| **Beneficiu**            | **Descriere**                                      |
| ------------------------ | -------------------------------------------------- |
| 🚀 **Test Rapid**        | Nu mai completezi formulare manual de fiecare dată |
| 🎓 **Învățare**          | Vezi exemple concrete pentru fiecare parametru     |
| 🔄 **Reproducibilitate** | Seed 42 garantează aceleași rezultate              |
| 🧪 **Testing**           | Valori consistente pentru teste                    |
| 📚 **Documentație Live** | Valorile sunt exemple practice                     |

## 🆘 Întrebări Frecvente

### Q: De ce seed 42?

**A:** Este un număr popular în testing (din "Hitchhiker's Guide to the Galaxy"). Orice seed funcționează!

### Q: Pot șterge valorile mock?

**A:** Da! Șterge orice câmp și completează manual. Butonul "Reset Mock" le restaurează.

### Q: Valorile mock sunt obligatorii?

**A:** Nu! Sunt doar pentru confort. Poți folosi orice valori dorești.

### Q: Ce se întâmplă dacă las seed gol?

**A:** API-ul va alege cuvinte random (fără seed = non-deterministic).

### Q: Pot crea sesiuni fără GUI?

**A:** Da! Folosește `python_client.py` sau `demo_client.py` pentru CLI.

---

**💡 TIP PRO:** Pentru testing rapid, lasă tot pre-completat și apasă direct "Creează Sesiune"! 🚀
