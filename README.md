# Dynamic DevTrack

**Automated Team Timeline & Task Planner** for IT development departments.

DevTrack is a web application that schedules developer work using a **rolling timeline engine**. When tasks are added, reordered, or a developer goes on leave, estimated completion dates (ECDs) recalculate automatically — accounting for weekends, holidays, and individual leave days.

Built from a full Software Requirements Specification (SRS) for real-world dev team operations.

---

## Features

| Module | Description |
|--------|-------------|
| **Dynamic Timeline Engine** | Sequential per-developer queues; 8-hour workdays; skips weekends, holidays, and leave |
| **Department Dashboard** | Side-by-side developer view with active task, backlog hours, clear date, bottleneck flags |
| **Queue Planner** | Drag-and-drop task reordering per developer (managers) |
| **User Management** | Add/edit Managers and Developers with individual login credentials |
| **My Profile** | Every user can update name, contact, bio, email, and password |
| **Developer Leaves** | Record leave per developer; timelines push forward automatically |
| **Holiday Calendar** | Company-wide holidays excluded from all timelines |
| **Email Alerts** | HTML notifications on task insert, reorder, and status changes |
| **Scheduled Reports** | Daily / weekly / monthly PDF workload reports |
| **Report Recipients** | Separate email lists for status alerts vs. scheduled reports |
| **Role-Based Access** | Executive (read-only), Manager (full control), Developer (own tasks) |
| **Estimation Audit** | Track actual vs. estimated hours per task |

---

## Tech Stack

- **Backend:** Python 3.11+, [FastAPI](https://fastapi.tiangolo.com/)
- **Database:** SQLite (local) / PostgreSQL (production)
- **ORM:** SQLAlchemy
- **Auth:** JWT + bcrypt
- **Frontend:** HTML, CSS, JavaScript (SortableJS for drag-and-drop)
- **PDF:** ReportLab
- **Email:** aiosmtplib (SMTP)
- **Scheduler:** APScheduler (cron reports)

---

## Screenshots

> Add screenshots here after deployment (Dashboard, Queue Planner, User Management).

---

## Quick Start (Local)

### Prerequisites

- Python 3.11 or newer
- `pip`

### 1. Clone the repository

```bash
git clone https://github.com/hassanziarak-png/devtrack.git
cd devtrack
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment (optional)

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Seed the database

```bash
python seed.py
```

### 5. Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

---

## Demo Accounts

After running `seed.py`, use these accounts to explore the app:

| Role | Email | Password |
|------|-------|----------|
| **Manager** | `manager@devtrack.local` | `manager123` |
| **Executive** | `exec@devtrack.local` | `exec123` |
| **Developer** | `dev1@devtrack.local` | `dev123` |
| **Developer** | `dev2@devtrack.local` | `dev123` |
| **Developer** | `dev3@devtrack.local` | `dev123` |

> Change all passwords before going to production.

---

## User Roles

| Role | Permissions |
|------|-------------|
| **Manager** | Full CRUD on tasks, reorder queues, manage users, holidays, leaves, report settings |
| **Developer** | View/update own assigned tasks, effort, status, and profile |
| **Executive** | Read-only dashboard, PDF reports, notification log |

---

## Configuration

Create a `.env` file in the project root (see `.env.example`):

```env
# Security
SECRET_KEY=change-this-to-a-long-random-string

# Database (use PostgreSQL in production)
DATABASE_URL=sqlite:///./devtrack.db

# Timeline
BOTTLENECK_THRESHOLD_DAYS=30

# Email (optional — alerts are logged locally if disabled)
EMAIL_ENABLED=false
SMTP_HOST=smtp-relay.brevo.com
SMTP_PORT=587
SMTP_USER=your-smtp-user
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=devtrack@yourcompany.com
```

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key — **must** be changed in production |
| `DATABASE_URL` | SQLite locally; PostgreSQL URL on Render/Railway |
| `EMAIL_ENABLED` | Set `true` to send real emails via SMTP |
| `SMTP_*` | SMTP credentials (Brevo, SendGrid, etc.) |
| `BOTTLENECK_THRESHOLD_DAYS` | Days of backlog before red/orange warning (default: 30) |

---

## API Documentation

With the server running:

- **Swagger UI:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/health

### Key endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/login` | Authenticate (email + password) |
| `GET` | `/api/tasks/dashboard/developers` | Department board data |
| `POST` | `/api/tasks/reorder` | Drag-and-drop queue update |
| `GET` | `/api/users` | List users (manager) |
| `POST` | `/api/users` | Create user (manager) |
| `POST` | `/api/leaves` | Add developer leave |
| `GET` | `/api/reports/pdf` | Download department PDF |
| `POST` | `/api/reports/recipients` | Add email recipient |

---

## Project Structure

```
devtrack/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Environment settings
│   ├── models.py            # Database models
│   ├── timeline_engine.py   # Business-day ECD calculations
│   ├── auth.py              # JWT authentication
│   ├── migrate.py           # SQLite schema migrations
│   ├── routers/
│   │   ├── auth.py          # Login / session
│   │   ├── tasks.py         # Tasks + dashboard
│   │   ├── users.py         # User management
│   │   ├── leaves.py        # Developer leave
│   │   ├── holidays.py      # Holiday calendar
│   │   └── reports.py       # PDF + email recipients
│   ├── services/
│   │   └── task_service.py  # Timeline recalculation, alerts
│   └── static/              # Web UI (HTML / CSS / JS)
├── seed.py                  # Demo data loader
├── requirements.txt
├── .env.example
└── README.md
```

---

## Deploy to Render (Free)

1. Push this repo to **GitHub**
2. Sign up at [render.com](https://render.com) with GitHub
3. Create a **PostgreSQL** database (Free tier) → copy the Internal URL
4. Create a **Web Service** connected to your repo:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Set environment variables (see [Configuration](#configuration))
   - Set `DATABASE_URL` to your PostgreSQL URL
   - Add `psycopg2-binary` to `requirements.txt` for PostgreSQL
6. Deploy → open your public URL (e.g. `https://devtrack-xxxx.onrender.com`)
7. Run `python seed.py` once via Render Shell to create initial users

> **Note:** Render free tier sleeps after inactivity. First visit after idle may take 30–60 seconds.

---

## What NOT to Commit

These files are listed in `.gitignore` and should **never** be pushed to GitHub:

| File | Reason |
|------|--------|
| `devtrack.db` | Local database with user data |
| `.env` | Contains secrets (SMTP password, SECRET_KEY) |
| `__pycache__/` | Python cache |

---

## Timeline Engine Logic

Tasks are scheduled as a **linear stack per developer**:

1. Task 1 starts on the next available business day
2. ECD = start date + effort hours (8h = 1 business day), skipping weekends, holidays, and leave
3. Task 2 starts when Task 1 completes
4. Reordering or adding leave triggers a **cascade recalculation** for all downstream tasks

**Example:** 16-hour task starting Wed Jul 8 normally ends Thu Jul 9. If the developer has leave on Jul 9, ECD moves to **Fri Jul 10**.

---

## License

This project is provided as-is for internal team use. Add your preferred license (MIT, Apache 2.0, etc.) if you plan to open-source it.

---

## Support

For issues or feature requests, open a **GitHub Issue** on this repository.

---

**Dynamic DevTrack** — *Plan smarter. Shift automatically.*
