# Telegram Student Result Management System

A production-ready Telegram bot for managing student examination results.
Teachers upload result sheets; students securely retrieve only their own results.

---

## Features

- **Role-based access control** — Student, Teacher, Admin
- **Secure student privacy** — Telegram account must be linked; students cannot access each other's results
- **Multi-step FSM result upload** — guided conversation with confirmation before saving
- **Photo storage** — stores Telegram `file_id` for exam sheets; no unnecessary file downloads
- **Duplicate detection** — warns before overwriting an existing result
- **Audit logging** — every write operation is recorded with user and timestamp
- **Rate limiting** — per-user request throttling
- **Admin panel** — manage teachers, students, results, and audit logs via Telegram
- **Docker support** — single `docker compose up` to run everything
- **Database migrations** — Alembic for safe schema evolution
- **Async** — fully async with aiogram 3.x and SQLAlchemy 2.x asyncpg

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
│   └── repositories/        # Data access objects
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

**Layers:**

```
Telegram Update
    → Middleware (auth, rate-limit, logging)
    → Handler (input parsing, user feedback)
    → Service (business logic, access control)
    → Repository (database queries)
    → ORM Model (SQLAlchemy)
    → PostgreSQL
```

---

## Technology Stack

| Component | Library |
|-----------|---------|
| Language | Python 3.12+ |
| Bot framework | aiogram 3.x |
| Database | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x (async) |
| Migrations | Alembic |
| Validation | Pydantic / Pydantic Settings |
| Async driver | asyncpg |
| Logging | structlog |
| Tests | pytest + pytest-asyncio |
| Container | Docker + Docker Compose |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# Telegram Bot token from BotFather
BOT_TOKEN=your_token_here

# PostgreSQL connection string
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/student_results

# Application mode
ENVIRONMENT=development
LOG_LEVEL=INFO

# Bootstrap admin accounts — comma-separated Telegram user IDs
ADMIN_TELEGRAM_IDS=123456789

# Photo size limit in MB
MAX_PHOTO_SIZE_MB=10

# Rate limit: requests per minute per user
RATE_LIMIT_PER_MINUTE=20

# Student privacy mode: "linked" (recommended) or "open"
STUDENT_LOOKUP_MODE=linked
```

**Never commit `.env` to Git.**

---

## BotFather Setup

1. Open Telegram and message [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts.
3. Copy the token and set `BOT_TOKEN=` in `.env`.
4. Optionally set the bot description and commands with `/setdescription` and `/setcommands`.

Suggested commands to register with BotFather:
```
start - Open main menu
help - Show help
cancel - Cancel current operation
```

---

## Local Development Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 16 (or use Docker)
- Git

### Install

```bash
git clone <repository-url>
cd telegram-result-bot

# Create virtual environment
python -m venv .venv

# Activate (Linux/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
# Edit .env with your BOT_TOKEN, DATABASE_URL, and ADMIN_TELEGRAM_IDS
```

### Database Setup

```bash
# Create the database (if running PostgreSQL locally)
createdb student_results

# Run migrations
alembic upgrade head
```

### Run

```bash
python -m app.main
```

---

## Running with Docker

Ensure Docker and Docker Compose are installed, then:

```bash
# Copy and configure .env
cp .env.example .env
# Edit .env — set BOT_TOKEN and ADMIN_TELEGRAM_IDS

# Build and start everything (bot + postgres + auto-migrate)
docker compose up --build

# Run with pgAdmin (development only)
docker compose --profile dev up --build

# Stop
docker compose down

# Destroy volumes (full reset)
docker compose down -v
```

The `migrate` service runs `alembic upgrade head` automatically before the bot starts.

---

## Database Migrations

```bash
# Generate a new migration after model changes
alembic revision --autogenerate -m "describe your change"

# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# View migration history
alembic history
```

---

## Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage report
pytest --cov=app --cov-report=html
```

Integration tests use SQLite in-memory — no PostgreSQL required.

---

## Admin Initialisation

1. Set `ADMIN_TELEGRAM_IDS=<your_telegram_user_id>` in `.env`.
2. Start the bot.
3. Send `/start` to the bot from your Telegram account.
4. You will see the Admin Panel automatically.

To find your Telegram user ID, message [@userinfobot](https://t.me/userinfobot).

---

## User Flows

### Student Flow
```
/start
→ Student main menu
→ "Check My Results" or "My Result History"
→ Enter student ID (in "open" mode) or auto-detected from linked account
→ Select a result from the list
→ View result details + exam sheet photo
```

### Teacher Flow
```
/start
→ Teacher Panel
→ "Upload Result"
→ Step 1: Enter student ID
→ Step 2: Enter subject
→ Step 3: Enter exam name
→ Step 4: Enter score
→ Step 5: Enter grade
→ Step 6: Upload photo
→ Review confirmation summary
→ Confirm → Result saved
```

### Admin Flow
```
/start
→ Admin Panel
→ Manage Teachers → Add / Deactivate
→ Manage Students → Add / Link Telegram / Deactivate
→ Statistics
→ Audit Logs
```

---

## Security Considerations

- All credentials are loaded from environment variables — never hardcoded.
- Student privacy is enforced at the service layer by matching `telegram_user_id` to the student profile (`STUDENT_LOOKUP_MODE=linked`).
- Role checks happen in every handler before any data is accessed.
- All write operations are recorded in the `audit_logs` table.
- SQL injection is prevented by SQLAlchemy's parameterised queries — raw SQL is never used.
- Rate limiting (20 requests/minute/user by default) prevents bot abuse.
- Detailed error messages are logged server-side; users only see friendly messages.
- No sensitive data (tokens, passwords, scores) appears in logs.
- The Docker container runs as a non-root user.

---

## Project Structure

```
telegram-result-bot/
├── app/                    # Application source code
│   ├── main.py
│   ├── config/
│   ├── bot/
│   ├── database/
│   ├── services/
│   ├── schemas/
│   └── utils/
├── migrations/             # Alembic migrations
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

## Deployment

### Production Checklist

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Set a strong `POSTGRES_PASSWORD`
- [ ] Remove the `pgAdmin` service from `docker-compose.yml`
- [ ] Remove the `ports` mapping from the `db` service
- [ ] Set `LOG_LEVEL=WARNING` or `INFO`
- [ ] Configure a process manager (systemd, supervisor) or use Docker restart policies
- [ ] Set up PostgreSQL backups
- [ ] Monitor with a log aggregation service

### Cloud Deployment (Example — any VPS)

```bash
# On the server
git clone <repository-url>
cd telegram-result-bot
cp .env.example .env
nano .env  # fill in production values
docker compose up -d --build
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `BOT_TOKEN is not configured` | Check your `.env` file has a valid `BOT_TOKEN` |
| `database_connection_failed` | Check `DATABASE_URL` and that PostgreSQL is running |
| Bot does not respond | Verify the token with BotFather; check logs |
| `Access denied` in Telegram | Your Telegram ID may not be in `ADMIN_TELEGRAM_IDS`, or your role is not set correctly |
| Alembic `Target database is not up to date` | Run `alembic upgrade head` |
| `No student profile linked` | Admin must link the student's Telegram ID first |

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
- Multi-language support (i18n)
