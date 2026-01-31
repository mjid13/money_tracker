<div align="center">

# 🏦 Bank Email Parser & Account Tracker

Automatically parse bank emails, track accounts, and analyze spending from a single Flask app.

[ additionally includes Gmail OAuth, PDF statement upload, budgets, and RTL/Arabic UI ]

</div>

---

## Overview
'Ghwazi' is the Arabic-Omani word for 'Money'.

This repository contains a Flask-based personal finance app focused on parsing bank transaction emails and turning them into structured accounts, transactions, and insights. It supports both IMAP (manual email configs) and Gmail OAuth, includes PDF statement parsing, and provides dashboards, budgets, and category tools.

The primary application lives in `ghwazi/` and runs via `ghwazi/main.py` (see `Procfile`).

---

## Features

- Email ingestion via IMAP with configurable sender/subject filters
- Gmail OAuth integration + Gmail API sync (labels, sender/subject filters)
- Transaction parsing and categorization (including counterparty matching)
- Multi-account tracking with balances and dashboards
- Budget setup and budget dashboards
- PDF statement upload and parsing
- CSV export for account transactions
- Health endpoints (`/health`, `/health/ready`, `/health/live`)
- RTL/Arabic UI with Flask-Babel (English also supported)
- Security basics: CSRF protection, rate limiting, secure sessions, security headers

---

## Tech Stack

- Flask 3.x, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF
- SQLAlchemy ORM (SQLite by default; PostgreSQL in production)
- Flask-Babel (i18n + RTL)
- Gmail API + Google OAuth
- IMAP email ingestion
- PDF parsing (pymupdf, pdfplumber, pypdf)

---

## Project Structure

```
money_tracker/
├── ghwazi/
│   ├── main.py                 # App entry point + CLI commands
│   ├── app/
│   │   ├── __init__.py          # App factory + middleware
│   │   ├── config/              # Base/dev/prod/test config
│   │   ├── models/              # SQLAlchemy models + repositories
│   │   ├── services/            # Email parsing, Gmail OAuth, budgeting
│   │   ├── views/               # Blueprints/routes
│   │   ├── templates/           # Jinja templates
│   │   ├── static/              # CSS/JS/images
│   │   └── utils/               # Helpers, decorators, validators
│   ├── translations/            # i18n catalogs (Arabic/English)
│   └── tests/
├── scripts/                     # Utility scripts
├── requirements.txt             # Production requirements (delegates)
├── Procfile                     # gunicorn ghwazi.main:app
├── runtime.txt                  # Python runtime for deployment
└── transactions.db              # Default SQLite database (local)
```

---

## Quick Start

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
# or for development tooling
pip install -r ghwazi/requirements/development.txt
```

### 3) Set required environment variables

At minimum, you must set a `SECRET_KEY`.

```bash
export SECRET_KEY="your-secret"
```

(Optional but recommended):

```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
```

### 4) Run the app

```bash
python ghwazi/main.py
```

App runs at `http://127.0.0.1:5000` by default.

---

## Configuration

Settings are loaded from environment variables (see `ghwazi/app/config/base.py`).

### Required
- `SECRET_KEY` — required for sessions and encryption

### Database
- `DATABASE_URL` — defaults to `sqlite:///transactions.db`


### Gmail OAuth
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REDIRECT_URI` (must match your Google OAuth app)

### Sessions / Redis (optional)
- `REDIS_URL` or `REDISCLOUD_URL`
- `PERMANENT_SESSION_LIFETIME`
- `SESSION_IDLE_TIMEOUT`

### Health checks
- `HEALTHCHECK_TOKEN` (optional; locks down `/health` endpoints)

### Production Gmail sync (optional)
- `GMAIL_FIRST_SYNC_DAYS`
- `GMAIL_SYNC_STUCK_MINUTES`
- `GMAIL_SYNC_COOLDOWN_SECONDS`

---

## Usage Guide

1) Register and log in at `/auth/register` and `/auth/login`
2) Add a bank account at `/account/accounts/add`
3) Configure email ingestion:
   - IMAP: add email configs in `/email`
   - Gmail: connect OAuth via `/oauth/google/login` and configure `/oauth/gmail/settings`
4) Trigger email syncing from the dashboard or account pages
5) Upload PDF statements via `POST /api/upload_pdf`
6) Manage categories and budgets in `/category` and `/budget`

---

## CLI Commands

The main app provides a simple CLI via `ghwazi/main.py`:

```bash
python ghwazi/main.py init-db
python ghwazi/main.py drop-db
python ghwazi/main.py test
python ghwazi/main.py lint
python ghwazi/main.py format-code
```

---

## Tests

```bash
pytest ghwazi/tests
```

---

## Deployment

### Gunicorn

```bash
gunicorn ghwazi.main:app
```

### Procfile

```
web: gunicorn ghwazi.main:app
```

---

## Health Endpoints

- `GET /health/` — basic status
- `GET /health/ready` — readiness checks (DB + session manager)
- `GET /health/live` — liveness checks

---

## Localization

- Default locale: Arabic (RTL)
- English support included
- Change language via `/i18n-set-lang?lang=en` or `/i18n-set-lang?lang=ar`

---

## Notes

- Default currency and bank presets focus on Omani banks (see `ghwazi/app/models/database.py`).
- SQLite is used by default for local development; PostgreSQL is recommended for production.

---

## License

MIT (see `LICENSE` if present).
