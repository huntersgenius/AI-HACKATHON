# Hamroh — Backend arxitektura rejasi v2 (kengaytiriladigan)

**Trek:** Tibbiyot, Umummilliy AI Xakaton (Qarshi bosqichi)
**Stack:** Flask + Jinja2 + SQLite + Tailwind (CDN) + vanilla JS, polling 3s, auth yo'q
**Maqsad:** Bugun-ertaga ishlaydigan MVP, lekin **ertaga yangi funksiya qo'shganda hech narsa sinmasligi** uchun qurilgan.

> v1 rejadan farqi: bu yerda faqat "nima qurish" emas, **"keyin qanday kengaytirish"** ham belgilangan.
> Asosiy g'oya — yangi funksiyalar **yangi fayl qo'shish** orqali keladi, mavjud faylni o'zgartirish orqali emas.

---

## 1. Kengaytirish tamoyillari (5 ta qoida)

Bu 5 qoida butun kodbazani boshqaradi. Har bir qaror shulardan kelib chiqadi.

**1. Ma'lumot > kod.** Yangi persona, yangi savol, yangi kun — bular `checkin_templates` jadvaliga
qator qo'shish bilan hal bo'ladi. Kodga tegilmaydi. Agar yangi persona qo'shish uchun `if persona == ...`
yozish kerak bo'lsa — dizayn xato.

**2. Kengaytma nuqtalari (extension points).** Uch joyda "plagin" mexanizmi bor:
*analyzers* (xavf tahlili), *event handlers* (voqeaga reaksiya), *notifiers* (xabar yuborish).
Yangi funksiya odatda shu uchtadan biriga yangi fayl qo'shish bilan tugaydi.

**3. Migratsiyalar, `DROP TABLE` emas.** Baza sxemasi raqamlangan migratsiya fayllari bilan
o'zgaradi. Yangi ustun qo'shilganda mavjud demo ma'lumot yo'qolmaydi.

**4. Bitta API konverti (envelope).** Har bir JSON javob bir xil shaklda. Frontend'da bitta
`api()` helper bor — yangi endpoint qo'shilganda frontend'ning xato ishlash logikasi tayyor.

**5. Feature flag'lar.** Tugallanmagan funksiya `config.FEATURES` orqali o'chirilgan holda
merge qilinadi. Demo paytida yarim ishlaydigan narsa ko'rinmaydi.

---

## 2. Qatlamli arxitektura

```
  HTTP (routes/)          ← faqat so'rov/javob, validatsiya. Biznes-logika YO'Q.
        ↓
  Services (services/)    ← biznes-logika. Kengaytmalarni chaqiradi.
        ↓
  Repositories (repos/)   ← faqat SQL. Boshqa qatlamlar SQL yozmaydi.
        ↓
  SQLite
```

Yon tomonda, servislarga ulanadigan kengaytma mexanizmlari:

```
  services/  ──emit()──→  core/events.py  ──→  hooks/*.py        (voqealarga reaksiya)
             ──run()───→  analyzers/*.py                          (xavf tahlili pipeline)
             ──send()──→  notifiers/*.py                          (xabar kanallari)
```

**Nega bu muhim:** route ichida SQL yozilsa, ertaga o'sha logikani boshqa joydan chaqirish
uchun copy-paste qilinadi va ikki nusxa bir-biridan uzoqlashadi. Qatlamlar buni oldini oladi.

---

## 3. Ma'lumotlar bazasi

### 3.1 Migratsiya tizimi

```
migrations/
├── 001_init.sql
├── 002_seed_bobur.sql
├── 003_add_aziza_hasan.sql
└── 004_add_medication_tracking.sql   ← ertangi funksiya shunday qo'shiladi
```

`db.py` ichida `run_migrations()`: `schema_migrations` jadvalidan qaysi fayllar bajarilganini
o'qiydi, faqat yangilarini tartib bilan ishga tushiradi. App har start bo'lganda avtomatik chaqiriladi.

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename   TEXT PRIMARY KEY,
    applied_at TEXT DEFAULT (datetime('now'))
);
```

**Qoida:** mavjud migratsiya fayli hech qachon tahrirlanmaydi. Yangi o'zgarish = yangi raqamli fayl.

### 3.2 Sxema (001_init.sql)

```sql
CREATE TABLE doctors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name   TEXT NOT NULL,
    clinic_name TEXT NOT NULL,
    phone_sim   TEXT
);

CREATE TABLE patients (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT NOT NULL,
    persona_key    TEXT NOT NULL,
    diagnosis      TEXT,
    discharge_date TEXT,
    phone_sim      TEXT,
    doctor_id      INTEGER NOT NULL REFERENCES doctors(id),
    current_day    INTEGER DEFAULT 0,
    risk_level     TEXT    DEFAULT 'green',
    meta_json      TEXT    DEFAULT '{}',   -- kengaytma: yangi maydon migratsiyasiz
    created_at     TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE checkin_templates (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    persona_key   TEXT NOT NULL,
    day_offset    INTEGER NOT NULL,
    seq           INTEGER DEFAULT 0,        -- bir kunda bir nechta savol tartibi
    question_key  TEXT NOT NULL,            -- 'temperature' | 'pain' | 'wound' ...
    question_text TEXT NOT NULL,
    answer_type   TEXT DEFAULT 'free_text', -- 'free_text'|'number'|'scale_1_10'|'yes_no'
    config_json   TEXT DEFAULT '{}'         -- min/max, birlik, variantlar
);

CREATE TABLE checkins (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  INTEGER NOT NULL REFERENCES patients(id),
    template_id INTEGER REFERENCES checkin_templates(id),
    day_number  INTEGER NOT NULL,
    status      TEXT DEFAULT 'pending',     -- 'pending'|'answered'|'skipped'
    sent_at     TEXT DEFAULT (datetime('now')),
    answered_at TEXT
);

CREATE TABLE messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    checkin_id INTEGER REFERENCES checkins(id),
    sender     TEXT NOT NULL,               -- 'system'|'patient'|'doctor'
    text       TEXT NOT NULL,
    meta_json  TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE ai_assessments (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id         INTEGER NOT NULL REFERENCES patients(id),
    checkin_id         INTEGER REFERENCES checkins(id),
    message_id         INTEGER REFERENCES messages(id),
    risk_level         TEXT NOT NULL,        -- 'green'|'yellow'|'red'
    risk_score         INTEGER DEFAULT 0,    -- 0..100, trend grafigi uchun
    danger_signals     TEXT DEFAULT '[]',    -- JSON array
    reasoning          TEXT,
    recommended_action TEXT,
    analyzer_results   TEXT DEFAULT '{}',    -- har bir analyzer nima dedi (debug + shaffoflik)
    source             TEXT DEFAULT 'llm',   -- 'llm'|'rules'|'merged'
    created_at         TEXT DEFAULT (datetime('now'))
);

CREATE TABLE alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id    INTEGER NOT NULL REFERENCES patients(id),
    doctor_id     INTEGER NOT NULL REFERENCES doctors(id),
    assessment_id INTEGER REFERENCES ai_assessments(id),
    severity      TEXT DEFAULT 'yellow',
    title         TEXT NOT NULL,
    status        TEXT DEFAULT 'new',        -- 'new'|'seen'|'resolved'
    created_at    TEXT DEFAULT (datetime('now')),
    resolved_at   TEXT
);

CREATE TABLE event_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name TEXT NOT NULL,
    payload    TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_messages_patient  ON messages(patient_id, created_at);
CREATE INDEX idx_assess_patient    ON ai_assessments(patient_id, created_at);
CREATE INDEX idx_alerts_doctor     ON alerts(doctor_id, status);
CREATE INDEX idx_templates_lookup  ON checkin_templates(persona_key, day_offset, seq);
```

**Kengaytirishga xizmat qiladigan tafsilotlar:**

| Element | Nima beradi |
|---|---|
| `meta_json` ustunlari | Kichik yangi maydon uchun migratsiya kerak emas — JSON ichiga qo'shiladi |
| `answer_type` + `config_json` | Yangi savol turi (raqam, shkala, ha/yo'q) data orqali qo'shiladi |
| `risk_score` | Trend grafigi uchun uzluksiz qiymat — keyin chart qo'shish oson |
| `analyzer_results` | Bir nechta analyzer natijasi saqlanadi — yangisini qo'shganda tarix buzilmaydi |
| `event_log` | Debug va demo paytida "nima bo'ldi" ni ko'rsatish; audit asosi |
| `seq` | Bir kunda bir nechta savol — struktura allaqachon tayyor |

---

## 4. Kengaytma nuqtalari (eng muhim bo'lim)

### 4.1 Analyzer pipeline — xavf tahlili

`analyzers/` papkasidagi har bir modul bitta funksiya beradi:

```python
# analyzers/base.py
@dataclass
class AnalyzerResult:
    risk_level: str          # 'green'|'yellow'|'red'
    risk_score: int          # 0..100
    danger_signals: list[str]
    reasoning: str
    recommended_action: str | None = None

REGISTRY: dict[str, Callable] = {}

def analyzer(name: str, priority: int = 100):
    """Dekorator: yangi analyzer'ni ro'yxatga qo'shadi."""
    def wrap(fn):
        REGISTRY[name] = (priority, fn)
        return fn
    return wrap
```

MVP'da ikkita analyzer bo'ladi:

- `analyzers/llm_analyzer.py` — Claude API chaqiradi (asosiy)
- `analyzers/rule_analyzer.py` — kalit so'z / chegara qoidalari (fallback va qo'shimcha ishonch)

Pipeline `services/assessment_service.py` ichida: barcha ro'yxatdagi analyzerlar ishlaydi,
natijalar **eng yuqori xavf bo'yicha** birlashtiriladi (`red` > `yellow` > `green`), hammasi
`analyzer_results` ustuniga yoziladi.

**Yangi analyzer qo'shish = `analyzers/` ichiga yangi fayl + dekorator. Mavjud kod o'zgarmaydi.**
Kelajakdagi misollar: trend analyzer (3 kun ketma-ket yomonlashish), dori qabul qilish analyzer,
javob bermaslik analyzer (bemor 2 kun javob bermadi).

### 4.2 Event bus — voqealarga reaksiya

```python
# core/events.py
_handlers: dict[str, list] = defaultdict(list)

def on(event_name: str):
    def wrap(fn):
        _handlers[event_name].append(fn)
        return fn
    return wrap

def emit(event_name: str, **payload):
    log_event(event_name, payload)          # event_log jadvaliga
    for fn in _handlers[event_name]:
        try:
            fn(**payload)
        except Exception:
            current_app.logger.exception("hook failed: %s", event_name)
            # bitta hook yiqilsa asosiy oqim davom etadi
```

Standart voqealar:

| Voqea | Qachon | Payload |
|---|---|---|
| `checkin.sent` | Tizim savol yubordi | patient_id, checkin_id, day_number |
| `checkin.answered` | Bemor javob berdi | patient_id, checkin_id, message_id |
| `assessment.created` | Tahlil tugadi | patient_id, assessment_id, risk_level |
| `alert.raised` | Signal yaratildi | patient_id, alert_id, severity |
| `alert.resolved` | Shifokor yopdi | alert_id |
| `doctor.replied` | Shifokor xabar yubordi | patient_id, doctor_id, message_id |

`hooks/` papkasida handler'lar: `hooks/alert_hooks.py` (yellow/red bo'lsa alert yaratadi),
`hooks/notify_hooks.py` (notifier chaqiradi). Yangi reaksiya = yangi handler fayli.

**Bu nima uchun muhim:** "xavf aniqlansa SMS yuborilsin" degan yangi talab kelganda,
`assessment_service.py` ga tegilmaydi — `hooks/` ga yangi fayl qo'shiladi.

### 4.3 Notifier'lar — xabar kanallari

```python
# notifiers/base.py
class Notifier(Protocol):
    key: str
    def send(self, to: str, title: str, body: str) -> None: ...

REGISTRY: dict[str, Notifier] = {}
def register(n: Notifier): REGISTRY[n.key] = n
```

MVP'da faqat `notifiers/in_app.py` (bazaga yozadi, panel polling bilan ko'radi).
Keyin `sms.py`, `telegram.py`, `email.py` — interfeys bir xil, chaqiruv joyi o'zgarmaydi.

---

## 5. API konventsiyasi

Barcha `/api/*` javoblari bitta shaklda:

```json
{ "ok": true,  "data": { ... } }
{ "ok": false, "error": { "code": "not_found", "message": "Bemor topilmadi" } }
```

- Prefiks: `/api/v1/...` — keyinchalik buzuvchi o'zgarish kerak bo'lsa `/api/v2` yoniga qo'yiladi.
- Xatolar `core/errors.py` dagi `AppError` orqali; global `@app.errorhandler` uni konvertga o'raydi.
- Frontend'da bitta `static/js/api.js` helper: `await api.get('/api/v1/...')` — xato ishlash markazlashgan.

**Kengayish foydasi:** yangi endpoint qo'shganda frontend'da xato ishlash, loading holati va
JSON parse logikasi allaqachon tayyor — faqat chaqiruv yoziladi.

### Endpoint ro'yxati (MVP)

**Demo boshqaruvi**

| Method | Path | Vazifa |
|---|---|---|
| GET | `/` | Rol tanlash (bemor / shifokor) |
| POST | `/api/v1/demo/advance-day` | `{patient_id}` → keyingi kun check-in yuboriladi |
| POST | `/api/v1/demo/reset` | Bazani seed holatiga qaytarish |
| GET | `/api/v1/demo/events` | Oxirgi `event_log` yozuvlari (demo paytida "ichini ko'rsatish") |

**Bemor**

| Method | Path | Vazifa |
|---|---|---|
| GET | `/patient/<pid>/chat` | Chat sahifasi |
| GET | `/api/v1/patients/<pid>/messages?after_id=` | Yangi xabarlar (polling, inkremental) |
| POST | `/api/v1/patients/<pid>/messages` | Javob yuborish → tahlil zanjiri |
| GET | `/api/v1/patients/<pid>/status` | current_day, risk_level, kutilayotgan savol |

**Shifokor**

| Method | Path | Vazifa |
|---|---|---|
| GET | `/doctor/<did>/dashboard` | Bemorlar ro'yxati sahifasi |
| GET | `/api/v1/doctors/<did>/patients` | Ro'yxat + risk rangi + oxirgi faollik |
| GET | `/api/v1/doctors/<did>/alerts?status=new` | Faol signallar (polling) |
| GET | `/doctor/patient/<pid>` | Bemor tafsiloti sahifasi |
| GET | `/api/v1/patients/<pid>/timeline` | Xabarlar + baholashlar birlashgan tarix |
| GET | `/api/v1/patients/<pid>/trend` | `risk_score` vaqt bo'yicha (grafik uchun) |
| POST | `/api/v1/patients/<pid>/doctor-message` | Shifokordan bemorga xabar |
| POST | `/api/v1/alerts/<aid>/resolve` | Signalni yopish |

`after_id` parametri — polling'ni inkremental qiladi: har 3 soniyada butun tarix emas,
faqat yangi xabarlar keladi. Bu keyin xabarlar ko'payganda ham sekinlashmaydi.

---

## 6. Fayl strukturasi

```
hamroh/
├── app.py                      # create_app(): config, db, blueprint, hooks ro'yxati
├── config.py                   # env o'qish + FEATURES flag'lari
├── requirements.txt
├── .env.example                # ANTHROPIC_API_KEY=...
├── .gitignore                  # .env, *.db, __pycache__
├── CLAUDE.md                   # kodbaza qoidalari (AI yordamchi uchun)
│
├── core/
│   ├── db.py                   # ulanish, run_migrations(), query helperlari
│   ├── events.py               # on() / emit()
│   ├── errors.py               # AppError, error handlerlar
│   └── responses.py            # ok() / fail() konvert helperlari
│
├── migrations/
│   ├── 001_init.sql
│   └── 002_seed_demo.sql
│
├── repos/                      # FAQAT SQL shu yerda
│   ├── patient_repo.py
│   ├── message_repo.py
│   ├── checkin_repo.py
│   ├── assessment_repo.py
│   └── alert_repo.py
│
├── services/                   # biznes-logika
│   ├── checkin_service.py      # advance_day(), savol yuborish
│   ├── message_service.py      # javob qabul qilish → tahlil chaqirish
│   ├── assessment_service.py   # analyzer pipeline + merge
│   └── doctor_service.py       # dashboard ma'lumotlari, javob yuborish
│
├── analyzers/                  # ← kengaytma nuqtasi 1
│   ├── base.py                 # AnalyzerResult, REGISTRY, @analyzer
│   ├── llm_analyzer.py         # Claude API
│   └── rule_analyzer.py        # fallback qoidalar
│
├── hooks/                      # ← kengaytma nuqtasi 2
│   ├── alert_hooks.py
│   └── notify_hooks.py
│
├── notifiers/                  # ← kengaytma nuqtasi 3
│   ├── base.py
│   └── in_app.py
│
├── routes/                     # faqat HTTP
│   ├── pages.py                # Jinja2 sahifalar
│   ├── patient_api.py
│   ├── doctor_api.py
│   └── demo_api.py
│
├── prompts/
│   └── triage_v1.txt           # LLM system prompt — koddan ajratilgan, versiyalangan
│
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── patient_chat.html
│   ├── doctor_dashboard.html
│   └── doctor_patient.html
│
├── static/js/
│   ├── api.js                  # fetch helper + xato ishlash
│   ├── poll.js                 # qayta ishlatiladigan polling utility
│   ├── patient_chat.js
│   └── doctor_dashboard.js
│
└── tests/
    └── test_smoke.py           # asosiy oqim buzilmaganini tekshiradi
```

`prompts/triage_v1.txt` — prompt koddan ajratilgan. Prompt'ni yaxshilash uchun Python
faylini tahrirlash kerak emas, va `v2` yonma-yon qo'yib solishtirish mumkin.

---

## 7. Konfiguratsiya va feature flag'lar

```python
# config.py
FEATURES = {
    "llm_analyzer":    True,   # False bo'lsa faqat rule-based ishlaydi (internet yo'q demo)
    "doctor_reply":    True,
    "trend_chart":     False,  # tayyor bo'lganda True
    "sms_notifier":    False,  # roadmap
    "multi_question":  False,  # bir kunda bir nechta savol
}
```

Kod ichida: `if features.enabled("trend_chart"): ...`
Tugallanmagan funksiya asosiy oqimni buzmaydi — o'chirilgan holda turadi.

`ANTHROPIC_API_KEY` faqat `.env` faylida, `.gitignore` ichida. `.env.example` repo'da qoladi.

---

## 8. Qurish tartibi (fazalar)

Har bir faza tugagach ilova **ishlaydigan holatda** bo'lishi shart. Faza oxirida commit.

| Faza | Nima quriladi | Tekshiruv |
|---|---|---|
| **0** | Skelet: `app.py`, `config.py`, `core/*`, migratsiya runner, `/health` | `python app.py` ishga tushadi, `/health` `{"ok":true}` qaytaradi |
| **1** | `001_init.sql` + `002_seed_demo.sql` (Bobur + 1 doktor + 5 kunlik savollar), `repos/*` | Baza yaratiladi, seed ma'lumot o'qiladi |
| **2** | `checkin_service.advance_day()` + `demo_api` | `POST /api/v1/demo/advance-day` savol yaratadi |
| **3** | Bemor chat sahifasi + polling + javob yuborish (AI'siz) | Brauzerda yozish/ko'rish ishlaydi |
| **4** | `analyzers/rule_analyzer.py` + pipeline + `assessment.created` voqeasi | Javobdan keyin `ai_assessments` yozuvi paydo bo'ladi |
| **5** | `analyzers/llm_analyzer.py` (Claude API) + `prompts/triage_v1.txt` | LLM javobi JSON sifatida parse bo'ladi; API o'chirilsa rule'ga tushadi |
| **6** | `hooks/alert_hooks.py` + shifokor dashboard + rang kodlash | Red javob → dashboard'da qizil qator, 3s ichida |
| **7** | Bemor tafsilot sahifasi: timeline + shifokordan xabar | Shifokor xabari bemor chatida ko'rinadi |
| **8** | Aziza + Hasan (`003_seed_personas.sql`) | **Faqat SQL fayl** — Python kodi o'zgarmaydi (dizayn testi) |
| **9** | Sayqal: trend grafik, `demo/events` paneli, alert resolve | Demo ssenariysi boshdan-oxir uzilmasdan o'tadi |

Faza 8 — bu arxitektura testi. Agar yangi persona qo'shish uchun Python kodini o'zgartirish
kerak bo'lsa, 1-tamoyil buzilgan va uni tuzatish kerak.

---

## 9. Retseptlar: yangi funksiyani qanday qo'shish

Bu bo'lim "o'zgartirish qanchalik katta bo'ladi" degan savolga aniq javob.

| Yangi funksiya | O'zgaradi | Hajmi |
|---|---|---|
| **Yangi persona** (masalan yurak bemori) | `migrations/00X_seed_*.sql` — faqat qatorlar | ~1 fayl, kod 0 qator |
| **Yangi kunlik savol** | `checkin_templates` ga qator | 1 SQL qator |
| **Yangi savol turi** (shkala, ha/yo'q) | `answer_type` qiymati + `static/js` da bitta widget | ~30 qator |
| **Yangi xavf qoidasi** | `analyzers/` ga yangi fayl + `@analyzer` dekorator | ~40 qator, mavjud kod 0 |
| **Prompt yaxshilash** | `prompts/triage_v2.txt` + config'da nom | 0 qator Python |
| **Xavf paytida SMS** | `notifiers/sms.py` + `hooks/` da 1 handler | ~50 qator, servislar 0 |
| **Yangi shifokor ko'rsatkichi** | `repos/` ga 1 query + `doctor_api` ga 1 endpoint + JS | ~40 qator |
| **Bemor javob bermasa signal** | `analyzers/silence_analyzer.py` yoki hook | ~40 qator |
| **Yangi rol** (hamshira, admin) | `routes/nurse_api.py` + template — blueprint qo'shiladi | yangi fayllar |
| **Yangi ustun kerak** | `migrations/00X_add_*.sql` (`ALTER TABLE ADD COLUMN`) | 1 SQL qator |
| **Kichik qo'shimcha maydon** | `meta_json` ichiga — migratsiya ham kerak emas | 0 |

**Umumiy naqsh:** yangi funksiyaning 80% holatda javobi — *yangi fayl qo'shish* yoki
*SQL qator qo'shish*. Mavjud fayllarni tahrirlash faqat ro'yxatga olish (registration)
joyida bo'ladi, u ham ko'p hollarda dekorator orqali avtomatik.

**Xavfli naqshlar (qilinmasin):**
- Route ichida SQL yozish
- Service ichida `if persona_key == 'bobur'` kabi shart
- Prompt matnini Python string sifatida kod ichiga yozish
- Mavjud migratsiya faylini tahrirlash
- LLM javobini `json.loads` bilan `try/except`siz parse qilish

---

## 10. Xavfsizlik to'rlari (demo yiqilmasligi uchun)

1. **LLM fallback.** API xato / timeout / noto'g'ri JSON → `rule_analyzer` natijasi ishlatiladi.
   Demo hech qachon "AI ishlamadi" holatida to'xtamaydi.
2. **Hook izolyatsiyasi.** Bitta hook exception bersa, asosiy so'rov davom etadi (`emit` ichida try/except).
3. **Timeout.** LLM chaqiruvi ~10s timeout bilan; oshsa fallback.
4. **`POST /api/v1/demo/reset`.** Demo boshlanishidan oldin bir tugma bilan toza holat.
5. **Smoke test.** `tests/test_smoke.py`: advance-day → javob → assessment → alert zanjiri
   ishlashini tekshiradi. Har faza oxirida `pytest -q`.
6. **Feature flag.** Tayyor bo'lmagan narsa `False` — demo paytida ko'rinmaydi.

---

## 11. Hal qilinishi kerak bo'lgan savollar

- `ANTHROPIC_API_KEY` tayyormi? (yo'q bo'lsa `llm_analyzer: False` bilan ham to'liq demo ishlaydi)
- Bobur uchun 5 kunlik aniq savollar matni (harorat, og'riq darajasi, yara holati, harakat, kayfiyat)
- Qaysi javoblar `red` hisoblanadi — bu ham promptga, ham `rule_analyzer` chegaralariga kerak
