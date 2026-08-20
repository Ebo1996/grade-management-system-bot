# 🎓 Telegram Student Result Management System

A production-ready Telegram bot for managing student examination results.
Authorized teachers upload result sheets; students securely retrieve only their own results.

> **Live Bot:** [@resultmanagementsystem_bot](https://t.me/resultmanagementsystem_bot)

---

## Features

- 🔐 **Role-based access control** — Student, Teacher, Admin
- 🔒 **Secure student privacy** — Telegram account must be linked; students cannot access each other's results
- 📋 **Multi-step FSM result upload** — guided conversation with confirmation before saving
- 📸 **Photo storage** — stores Telegram `file_id` for exam sheets; no unnecessary file downloads
- ⚠️ **Duplicate detection** — warns before overwriting an existing result
- 📝 **Audit logging** — every write operation is recorded with user and timestamp
- ⏳ **Rate limiting** — per-user request throttling (20 requests/min)
- 🛠️ **Admin panel** — manage teachers, students, results, and audit logs via Telegram
- 🐳 **Docker support** — single `docker compose up` to run everything
- 🗄️ **Database migrations** — Alembic for safe schema evolution
- ⚡ **Fully async** — aiogram 3.x and SQLAlchemy 2.x with asyncpg

---

## Technology Stack

| Component | Library |
|-----------|---------|
| Language | Python 3.12+ |
| Bot framework | aiogram 3.13.x |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Validation | Pydantic / Pydantic Settings |
| Async driver | asyncpg |
| Logging | structlog |
| Tests | pytest + pytest-asyncio |
| Container | Docker + Docker Compose |

---

## Architecture

```
app/
├── main.py                  # Entry point
├── config/
│   └── settings.py          # Pydantic Settings (env vars)
├── bot/
│   ├── handlers/            # Telegram message/callback handlers
│   │   ├── start.py         # /start, /help, role routing
│   │   ├── student.py       # Student flows
│   │   ├── teacher.py       # Teacher upload FSM
│   │   └── admin.py         # Admin management
│   ├── keyboards/           # InlineKeyboardMarkup builders
│   ├── states/              # FSM StatesGroups
│   └── middlewares/         # Auth, logging, rate-limiting
├── database/
│   ├── connection.py        # Engine, session factory
│   ├── models/              # SQLAlchemy ORM models
│   └── repositories/        # Data access layer
├── services/                # Business logic
│   ├── auth_service.py
│   ├── student_service.py
│   ├── result_service.py
│   ├── teacher_service.py
│   └── admin_service.py
├── schemas/                 # Pydantic DTOs
└── utils/
    ├── validators.py        # Input validation
    └── logger.py            # Structured logging
```

**Request flow:**

```
Telegram Update
    → Middleware (auth, rate-limit, logging)
    → Handler (input parsing, user feedback)
    → Service (business logic, access control)
    → Repository (database queries)
    → PostgreSQL
```

---

## User Flows

### Student
```
/start → Student Menu
→ Check My Results → enter student ID
→ Select result from list
→ View details + exam sheet photo
```

### Teacher
```
/start → Teacher Panel
→ Upload Result
→ Student ID → Subject → Exam Name → Score → Grade → Photo
→ Confirm summary → Saved ✅
```

### Admin
```
/start → Admin Panel
→ Manage Teachers  (add / deactivate)
→ Manage Students  (add / link Telegram / deactivate)
→ Manage Results   (view / delete)
→ Audit Logs
→ Statistics
```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_TOKEN` | Telegram bot token from BotFather | `123456:ABC...` |
| `DATABASE_URL` | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@host/db` |
| `ADMIN_TELEGRAM_IDS` | Comma-separated admin Telegram user IDs | `7721510666` |
| `ENVIRONMENT` | `development` or `production` | `production` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `STUDENT_LOOKUP_MODE` | `linked` (secure) or `open` | `linked` |
| `MAX_PHOTO_SIZE_MB` | Max upload size in MB | `10` |
| `RATE_LIMIT_PER_MINUTE` | Requests per user per minute | `20` |

Copy `.env.example` to `.env` — **never commit `.env` to Git.**

---

## Local Setup

### Prerequisites
- Python 3.12+
- PostgreSQL 16

### Install

```bash
git clone https://github.com/Ebo1996/grade-management-system-bot.git
cd grade-management-system-bot

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env — set BOT_TOKEN, DATABASE_URL, ADMIN_TELEGRAM_IDS
```

### Database

```bash
# Create database
createdb student_results

# Run migrations
alembic upgrade head
```

### Run

```bash
python -m app.main
```

---

## Docker Setup

```bash
cp .env.example .env
# Edit .env

docker compose up --build
```

The `migrate` service runs `alembic upgrade head` automatically before the bot starts.

```bash
# With pgAdmin (dev only)
docker compose --profile dev up --build

# Stop
docker compose down

# Full reset
docker compose down -v
```

---

## Deployment on Render

1. Push code to GitHub
2. Go to [render.com](https://render.com) → **New** → **Background Worker**
3. Connect your GitHub repo
4. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `alembic upgrade head && python -m app.main`
5. Create a **PostgreSQL** database on Render and copy the Internal Database URL
6. Add environment variables (change `postgresql://` → `postgresql+asyncpg://` in DATABASE_URL)
7. Deploy

---

## BotFather Setup

1. Message [@BotFather](https://t.me/BotFather) → `/newbot`
2. Copy the token → set `BOT_TOKEN` in `.env`
3. Register commands with `/setcommands`:

```
start - Open main menu
help - Show help
cancel - Cancel current operation
```

---

## Admin Initialisation

1. Get your Telegram ID from [@userinfobot](https://t.me/userinfobot)
2. Set `ADMIN_TELEGRAM_IDS=<your_id>` in `.env`
3. Start the bot and send `/start` — you will see the Admin Panel

---

## Testing

```bash
# All tests
pytest

# Verbose
pytest -v

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With coverage
pytest --cov=app --cov-report=html
```

Integration tests use SQLite in-memory — no PostgreSQL needed.

---

## Security

- All credentials loaded from environment variables — never hardcoded
- Student privacy enforced at service layer via `telegram_user_id` matching
- Role checks in every handler before data access
- All write operations recorded in `audit_logs`
- SQL injection prevented by SQLAlchemy parameterised queries
- Rate limiting prevents abuse
- Friendly error messages to users; detailed errors in server logs only
- Docker container runs as non-root user

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `BOT_TOKEN is not configured` | Check `.env` has a valid token |
| `database_connection_failed` | Check `DATABASE_URL` and PostgreSQL is running |
| Bot does not respond | Verify token with BotFather; check logs |
| `Access denied` | Your Telegram ID may not be in `ADMIN_TELEGRAM_IDS` |
| `No student profile linked` | Admin must link the student's Telegram ID first |
| Alembic `not up to date` | Run `alembic upgrade head` |

---

## Project Structure

```
grade-management-system-bot/
├── app/
│   ├── main.py
│   ├── config/
│   ├── bot/
│   ├── database/
│   ├── services/
│   ├── schemas/
│   └── utils/
├── migrations/
│   └── versions/
├── tests/
│   ├── unit/
│   └── integration/
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Future Roadmap

- FastAPI REST API + React admin dashboard
- PDF result report generation
- Bulk CSV/Excel import
- Multi-school support
- Parent accounts
- Push notifications when results are published
- OCR for reading result sheets
- S3-compatible photo storage
- Multi-language support

---

## Author

Built by **Ebisa Berhanu**

---

## License

MIT © [Ebisa Berhanu](https://github.com/Ebo1996)
