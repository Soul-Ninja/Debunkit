<div align="center">

<img src="Static/Images/debunkit-logo.png" alt="DEBUNK.IT logo" width="88"/>

# DEBUNK.IT

### Can we really trust the media? Check before you share.

AI-assisted misinformation detection with live web evidence, transparent verdicts and an editorial-dispatch interface.

<br>

[![Live Demo](https://img.shields.io/badge/LIVE_DEMO-Open_the_scanner-C8423B?style=for-the-badge&logo=railway&logoColor=white)](https://debunkit-production.up.railway.app)
[![Python](https://img.shields.io/badge/Python-3.10+-1B1B1B?style=for-the-badge&logo=python&logoColor=E4E0D3)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-1B1B1B?style=for-the-badge&logo=flask&logoColor=E4E0D3)](https://flask.palletsprojects.com)
[![Cohere](https://img.shields.io/badge/Cohere-command--r-1B1B1B?style=for-the-badge)](https://cohere.com)
[![Tests](https://img.shields.io/badge/tests-48_passing-4EA874?style=for-the-badge)](tests)
[![License](https://img.shields.io/badge/License-MIT-A88B4A?style=for-the-badge)](LICENSE)

<br>

<img src="docs/screenshots/landing-hero.jpg" alt="DEBUNK.IT landing page: Can we really trust the media?" width="100%"/>

</div>

<br>

## Contents

[Live demo](#-live-demo) · [What it does](#-what-it-does) · [Screenshots](#-screenshots) · [How it works](#-how-it-works) · [Design](#-design-language) · [Quick start](#-quick-start) · [Security](#-security) · [API](#-api) · [Testing](#-testing) · [Deployment](#-deployment) · [Roadmap](#-roadmap)

---

## 🚀 Live demo

**[debunkit-production.up.railway.app](https://debunkit-production.up.railway.app)**: no sign-up needed to scan a headline. Create an account to keep a searchable history and telemetry.

> The first request after a quiet period can take a few seconds while the instance wakes up.

---

## 🎯 What it does

Misinformation spreads faster than fact-checking can keep up. DEBUNK.IT gives anyone a quick, evidence-backed read on a **headline**, an **article URL** or a block of **full text**, and shows its reasoning instead of just a score.

| | |
|---|---|
| 🧠 **Hybrid AI pipeline** | Cohere LLM reasoning, a trained TF-IDF + Logistic Regression model and a local NLP engine, so there is always an assessment, even offline |
| 🌐 **Live web evidence (RAG)** | Multi-query DuckDuckGo search with fact-check source detection feeds every verdict |
| 🔗 **URL scraper** | Pulls the article body and uses it as primary evidence |
| 🧾 **Transparent verdicts** | Verdict stamp, confidence meter, written reasoning and source receipts |
| 📚 **History and telemetry** | Searchable ledger of past scans plus verdict, confidence and engine-mode breakdowns |
| 📋 **Export** | Copy a report or download a receipt as `.txt` |
| 💬 **Community reviews** | Visitors can leave and read reviews on the landing page |
| 🛡️ **Security first** | CSRF, SSRF blocking, XSS sanitisation, rate limiting, hashed passwords |
| 🌗 **Light and dark themes** | Newsprint paper by day, warm charcoal by night |

### Verdicts

| Verdict | Meaning |
|---|---|
| ✅ `SUPPORTED` | Credible evidence confirms the central claim |
| ❌ `REFUTED` | Credible sources contradict the claim |
| ⚠️ `MISLEADING` | Partly true, but missing context, old media or misrepresented |
| 🔍 `INSUFFICIENT EVIDENCE` | Sources neither clearly confirm nor deny |
| 🚩 `LOW CREDIBILITY` | Suspicious language or weak sourcing, but not directly refutable |

---

## 📸 Screenshots

<table>
  <tr>
    <td width="50%" align="center">
      <img src="docs/screenshots/scanner-verdict.jpg" alt="Live scanner showing a verdict stamp, confidence meter and reasoning"/>
      <br><sub><b>Live scanner</b>: verdict stamp, confidence meter and written reasoning</sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/screenshots/landing-dark.jpg" alt="Landing page in dark mode"/>
      <br><sub><b>Dark mode</b>: warm charcoal with the same editorial type</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <img src="docs/screenshots/history.jpg" alt="Ledger history of past analyses"/>
      <br><sub><b>Ledger history</b>: every scan, searchable and filterable</sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/screenshots/telemetry.jpg" alt="Bureau telemetry with verdict breakdown"/>
      <br><sub><b>Telemetry</b>: verdict breakdown, average confidence and engine mode</sub>
    </td>
  </tr>
  <tr>
    <td width="50%" align="center">
      <img src="docs/screenshots/login.jpg" alt="Login page with editorial collage"/>
      <br><sub><b>Sign in</b>: editorial split layout with inline validation</sub>
    </td>
    <td width="50%" align="center">
      <img src="docs/screenshots/mobile.jpg" alt="Landing page on a phone" width="240"/>
      <br><sub><b>Mobile</b>: stacked layout with 44px touch targets</sub>
    </td>
  </tr>
</table>

<details>
<summary><b>See the full landing page</b></summary>
<br>
<img src="docs/screenshots/landing-full.jpg" alt="Full DEBUNK.IT landing page" width="100%"/>
</details>

---

## 🔬 How it works

```mermaid
flowchart TD
    A["Headline, URL or text"] --> B["Input validation<br/>length limits, SSRF guard, sanitising"]
    B -- "URL mode" --> C["Article scraper"]
    B -- "Headline or text" --> D["Live web search (RAG)"]
    C --> D
    D --> E["Cohere reasoning<br/>with source-aware prompts"]
    E -- "AI unavailable" --> F["Local ML + NLP fallback"]
    E --> G["Verdict + confidence + receipts"]
    F --> G
    G --> H[("Database<br/>history and cache")]

    classDef ink fill:#1B1B1B,stroke:#1B1B1B,color:#E4E0D3;
    classDef red fill:#C8423B,stroke:#1B1B1B,color:#fff;
    classDef paper fill:#E4E0D3,stroke:#1B1B1B,color:#1B1B1B;
    class A,G ink;
    class B red;
    class C,D,E,F,H paper;
```

Results are cached per user (6 hours for URLs, 24 hours for text) so repeat checks are instant.

---

## ⚡ Quick start

```bash
git clone https://github.com/Soul-Ninja/Debunkit.git
cd Debunkit
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
COHERE_API_KEY=your_cohere_api_key
SECRET_KEY=a_long_random_string
DATABASE_URL=sqlite:///debunkit.db
FLASK_ENV=development
```

> A free Cohere key is available at [cohere.com](https://cohere.com). Without one, DEBUNK.IT falls back to the local ML and NLP engines.

```bash
python debunkit_app.py
```

Open **http://127.0.0.1:5000**.

**Optional: retrain the local model.** Put `WELFake_Dataset.csv` in the project root, then run `python training.py`.

---

## 🗂️ Project structure

```
Debunkit/
├── debunkit_app.py        Flask app: routes and API
├── config.py              Dev / Prod / Test config
├── serve.py               Waitress production server
├── training.py            TF-IDF + Logistic Regression training
├── Dockerfile             Container image (gunicorn)
│
├── Core/
│   ├── ai_engine.py       Cohere reasoning + hybrid pipeline
│   ├── rag_engine.py      Live search + article scraper
│   ├── nlp_engine.py      Offline pattern engine
│   ├── database.py        SQLAlchemy models
│   └── user_model.py      Auth model (Flask-Login)
│
├── utils/                 validators.py (SSRF) · sanitizer.py (XSS)
├── Template/              landing · index (scanner, ledger, telemetry) · auth · profile · settings
├── Static/                CSS · JS (landing, main, canvas) · Images
├── tests/                 pytest suite
└── docs/screenshots/      README images
```

---

## 🛠️ Tech stack

| Layer | Tools |
|---|---|
| **Backend** | Flask, Flask-Login, Flask-Limiter, Flask-SQLAlchemy, Flask-CORS |
| **AI / ML** | Cohere `command-r-08-2024`, scikit-learn (TF-IDF + Logistic Regression), DuckDuckGo search (`ddgs`), BeautifulSoup4 |
| **Frontend** | Jinja2, vanilla JS, CSS custom properties, HTML5 canvas. No framework, no build step |
| **Data** | SQLite for development, PostgreSQL via `DATABASE_URL` |
| **Serving** | Gunicorn or Waitress, Docker, GitHub Actions CI |

---

## 🔐 Security

| Layer | Protection |
|---|---|
| `validators.py` | Length limits, null-byte stripping, URL scheme enforcement, **SSRF blocking** via DNS resolution |
| `sanitizer.py` | **XSS prevention**: HTML escaping, script removal, `javascript:` / `data:` blocking |
| `debunkit_app.py` | **CSRF token** required on every `POST`, `PUT`, `PATCH` and `DELETE` |
| `main.js` | Sends `X-CSRFToken`; refuses non-HTTP source URLs in the DOM |
| `config.py` | Rate limiting, password complexity rule, secure session cookies |

---

## 📡 API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/analyze` | Run an analysis |
| `GET` | `/api/history` | The signed-in user's history |
| `GET` | `/api/analysis/<id>` | One analysis in detail |
| `GET` | `/api/search?q=` | Search past analyses |
| `GET` | `/api/stats` | Verdict statistics |
| `POST` | `/api/clear-database` | Delete all of the user's analyses |
| `GET` `PUT` | `/api/user/profile` | View or update profile |
| `PUT` | `/api/user/settings` | Theme, password, preferences |
| `DELETE` | `/api/user/delete` | Delete account and data |
| `GET` `POST` | `/api/reviews` | Read or submit community reviews |
| `GET` | `/api/health` | Health check |

---

## 🧪 Testing

```bash
pip install -r requirements-dev.txt
pytest -q
```

48 tests cover the API, the AI engine, input validation and sanitising. They run on every push through GitHub Actions on Python 3.12.

**Local ML baseline:** on 1,000 held-out samples from WELFake, the TF-IDF + Logistic Regression fallback scores about **93% accuracy** at roughly **1.6 ms** per query (see [debunkit_metrics_summary.md](debunkit_metrics_summary.md)). That figure covers the local classifier only, not the full Cohere + RAG pipeline.

---

## 🌍 Deployment

The live site runs on **Railway**. Any host that runs a Python web service or a container works.

```bash
# Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 debunkit_app:app

# Waitress (the included serve.py; pair with a tunnel or reverse proxy)
python serve.py

# Docker
docker build -t debunkit .
docker run -p 8080:8080 --env-file .env debunkit
```

Production environment:

```env
FLASK_ENV=production
SECRET_KEY=<strong-random-secret>
COHERE_API_KEY=<your-key>
DATABASE_URL=postgresql://user:pass@host/dbname
SESSION_COOKIE_SECURE=True
RATELIMIT_ENABLED=True
```

---

## ⚠️ Limitations

- **Not a final authority.** DEBUNK.IT is an assistant, not a replacement for human judgment.
- Breaking news, satire, AI-generated images and conflicting sources may still need manual checking.
- The local ML model detects writing patterns, not factual truth.
- Full AI analysis needs a Cohere API key; without one it falls back to local analysis.
- Search quality depends on DuckDuckGo availability and can drop for very recent events.

---

## 🗺️ Roadmap

- [x] Hybrid analysis pipeline (AI + ML + NLP)
- [x] Accounts, history and telemetry
- [x] Security hardening (CSRF, SSRF, XSS, rate limiting)
- [x] Docker support and CI
- [x] Editorial redesign with light and dark themes
- [x] Signature motion layer
- [ ] Custom domain
- [ ] Browser extension
- [ ] Image and video misinformation detection
- [ ] Multilingual support
- [ ] Public API with keys

---

## 🤝 Contributing

1. Fork the repository
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "feat: your feature"`
4. Push and open a Pull Request

---

<div align="center">

**MIT License** · Built by **[Soul-Ninja](https://github.com/Soul-Ninja)**

*Analyze claims before they spread.*

⭐ Star the repo if it helped you

</div>
