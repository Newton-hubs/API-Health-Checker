# API Health Checker

[![CI](https://github.com/Newton-hubs/API-Health-Checker/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Newton-hubs/API-Health-Checker/actions/workflows/ci.yml)

A full-stack web application that checks whether a URL is reachable, measures its response time, and keeps a history with statistics. Built with **React**, **FastAPI**, **SQLite**, **SQLAlchemy 2.0**, **Alembic**, and **Docker**.

The backend makes outbound HTTP requests on behalf of the user, so it includes SSRF protection (see [Security](#security)).

## Features

- Check any public `http://` or `https://` URL and see status, HTTP code, and response time
- Handles invalid URLs, timeouts, connection failures, DNS failures, and HTTP error statuses
- Persistent check history with pagination, stored in SQLite
- Dashboard statistics: total, successful, and failed checks, and average response time
- Responsive React dashboard with loading, success, failure, empty, and error states
- SSRF protection: private, loopback, and link-local destinations are blocked, including via redirects
- Docker Compose setup with a persistent volume (no separate database container)
- Automated tests with `pytest` and no network access required

## Architecture

```
 Browser (React + Vite)
      │  fetch (JSON)
      ▼
 FastAPI ── Pydantic validation ──► SSRF check (scheme, DNS, IP ranges)
      │                                   │
      │ SQLAlchemy 2.0                    ▼
      ▼                          HTTPX request (redirects followed manually,
 SQLite file                      each hop re-validated)
 (schema managed by Alembic)
```

**Request flow for `POST /api/check`:**

1. Pydantic validates the body (must be a well-formed `http`/`https` URL).
2. URLs containing a username or password are rejected.
3. The hostname is resolved and **every** returned address must be publicly routable.
4. HTTPX sends a `GET` with redirects disabled. Only the headers are read, never the body.
5. Each redirect target goes through the same validation before it is requested.
6. The outcome (up/down, HTTP code, response time, safe error message) is saved and returned.

| Layer | Technology | Role |
|---|---|---|
| Frontend | React 19, Vite | Dashboard UI, uses the Fetch API |
| API | FastAPI, Pydantic | Routing, validation, response schemas |
| HTTP client | HTTPX | Outbound health checks with timeouts |
| Database | SQLite, SQLAlchemy 2.0 | History storage |
| Migrations | Alembic | Versioned schema changes |
| Packaging | Docker, Docker Compose | Two containers and one named volume |

## Project structure

```
API Health Checker/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, router registration
│   │   ├── api/               # health.py, checks.py, stats.py
│   │   ├── core/config.py     # settings read from environment variables
│   │   ├── db/session.py      # engine, session factory, Base, get_db
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   └── services/          # ssrf.py (validation), checker.py (HTTPX logic)
│   ├── alembic/               # migrations
│   ├── tests/                 # pytest suite
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/        # CheckForm, ResultCard, StatsPanel, HistoryTable
│   │   ├── services/api.js    # all fetch calls
│   │   ├── App.jsx, App.css, main.jsx
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

## Prerequisites

Tested with the versions below on Windows 11. Other versions or operating systems were not tested.

- Python 3.13
- Node.js 22 and npm 10
- Git
- Docker Desktop with Compose v2 (only for the Docker setup)

## Run locally (Windows PowerShell)

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload
```

The API is now at <http://127.0.0.1:8000>, with interactive docs at <http://127.0.0.1:8000/docs>.

`alembic upgrade head` creates `backend/health_checks.db`. If PowerShell blocks `Activate.ps1`, see [Troubleshooting](#troubleshooting).

### Frontend (second terminal)

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

## Run with Docker

```powershell
docker compose up -d --build
```

| Service | URL |
|---|---|
| Frontend | <http://localhost:5173> |
| Backend API | <http://localhost:8000> |

- The backend container applies migrations automatically on every start.
- The SQLite file lives in the named volume `health_data`, mounted at `/data`, and survives restarts.
- Ports are bound to `127.0.0.1`, so the app is not exposed to your network.
- The browser calls the backend through the published port, so `VITE_API_URL` is `http://localhost:8000`, not a Docker-internal name. It is baked into the frontend at **build time**; change it and rebuild.

```powershell
docker compose ps                 # status
docker compose logs -f backend    # follow logs
docker compose down               # stop and remove containers (keeps your data)
docker compose down -v            # ALSO DELETES the volume and all history
```

Local development and Docker both use ports 8000 and 5173. Run one at a time.

## Configuration

Environment variables (all optional). For Docker Compose, put them in a `.env` file next to `docker-compose.yml`; see `.env.example`.

| Variable | Default | Used by | Description |
|---|---|---|---|
| `DATABASE_URL` | `sqlite:///<backend>/health_checks.db` | backend | SQLAlchemy URL. Compose sets it to `/data/health_checks.db`. |
| `CHECK_TIMEOUT_SECONDS` | `10` | backend | Timeout per request to the target |
| `MAX_REDIRECTS` | `5` | backend | Maximum redirects followed per check |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | backend | Comma-separated browser origins allowed to call the API |
| `VITE_API_URL` | `http://127.0.0.1:8000` (local), `http://localhost:8000` (Docker) | frontend | API base URL, fixed at build time |

## Database migrations

Run from `backend/` with the virtual environment active.

```powershell
alembic upgrade head                                 # apply all migrations
alembic current                                      # show the database revision
alembic history                                      # list migrations
alembic revision --autogenerate -m "describe change" # create a migration after editing a model
alembic downgrade -1                                 # roll back one migration (destroys data in dropped tables)
```

Always read an autogenerated migration before applying it.

## Testing

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

The suite (79 tests) covers successful checks, HTTP errors, invalid URLs, timeouts, connection failures, DNS failures, SSRF protection (including redirects), history and pagination, statistics, CORS, and error responses that must not leak internals. It uses an in-memory database, fakes DNS, and mocks all HTTP, so it never touches the network or your real database file.

Not covered by automated tests: Alembic migrations, real network and TLS behavior, and the React frontend.

## API reference

Base URL: `http://localhost:8000`. Interactive docs: `/docs`.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Backend liveness |
| POST | `/api/check` | Check a URL and save the result |
| GET | `/api/checks?page=1&page_size=20` | Paginated history, newest first (`page_size` 1 to 100) |
| GET | `/api/checks/{id}` | A single check |
| GET | `/api/stats` | Aggregate statistics |

### `POST /api/check`

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/check -Method POST -ContentType "application/json" -Body '{"url":"https://example.com"}'
```

```json
{
  "id": 1,
  "url": "https://example.com/",
  "status": "up",
  "status_code": 200,
  "response_time_ms": 83.85,
  "error_message": null,
  "checked_at": "2026-10-02T17:48:04.182285Z"
}
```

A completed check always returns **201**, including when the target is down. `status` is `up` when the final response code is below 400, otherwise `down`. `status_code` and `response_time_ms` are `null` when no response was received.

| Situation | Response |
|---|---|
| Target down, 4xx/5xx, timeout, connection or DNS failure | `201`, saved with `status: "down"` and a fixed `error_message` such as `HTTP 404`, `Request timed out`, `Could not connect to host`, `Could not resolve host`, `Redirect to a restricted destination blocked`, or `Too many redirects` |
| Destination not allowed (loopback, private, link-local, ...) | `400` `{"detail": "URL destination is not allowed"}`; not saved |
| URL contains a username or password | `400`; not saved |
| Malformed URL or scheme other than http/https | `422` |

### `GET /api/checks`

```json
{ "items": [ { "id": 2, "...": "..." } ], "total": 2, "page": 1, "page_size": 20 }
```

A page past the end returns an empty `items` list. Invalid paging parameters return `422`.

### `GET /api/checks/{id}`

Returns one check, `404` `{"detail": "Check not found"}` if the id does not exist, or `422` for a non-integer id.

### `GET /api/stats`

```json
{
  "total_checks": 3,
  "successful_checks": 1,
  "failed_checks": 2,
  "average_response_time_ms": 67.94
}
```

`average_response_time_ms` is the mean over checks that received a response (including 4xx/5xx), and is `null` when there are none.

## Security

**Implemented**

- Only `http`/`https` URLs are accepted; URLs with embedded credentials are rejected so they are never stored or echoed.
- **SSRF protection:** the hostname is resolved and *every* address must be publicly routable. Loopback, private (RFC 1918), link-local (including cloud metadata `169.254.169.254`), CGNAT, multicast, unspecified, reserved, and IPv4-embedding IPv6 forms (IPv4-mapped, NAT64, 6to4, IPv4-compatible) are blocked. The rule is deny-by-default.
- Redirects are followed manually and each hop is re-validated before it is requested.
- HTTPX ignores proxy environment variables, so a proxy cannot resolve names on the app's behalf.
- Only response headers are read; response bodies are never downloaded.
- Errors are mapped to fixed messages. Raw exception text is never stored or returned, and unexpected failures return a generic 500.
- CORS uses an explicit allow-list (never `*`) and only the methods and headers the frontend uses.
- Containers run as a non-root user, and published ports are bound to `127.0.0.1`.
- No secrets are required or stored.

**Known limitations**

- **DNS rebinding:** the hostname is resolved once to validate it and again when the request is made. A hostile DNS server could answer differently the second time. Closing this requires pinning the validated IP in a custom transport; it is not implemented.
- **Slow responses:** the timeout applies per network read, not as a total deadline, so a server that trickles headers can hold a worker thread longer than `CHECK_TIMEOUT_SECONDS`.
- **Port probing:** any port on a public host is allowed, so the tool can be used to probe public hosts.
- **No authentication or rate limiting**, and history grows without bound. Do not expose this service to untrusted users without adding authentication, rate limiting, and retention limits (for example behind a reverse proxy).
- The FastAPI docs (`/docs`, `/openapi.json`) are enabled.
- The frontend is served by nginx without a Content-Security-Policy.
- Python dependencies have not been audited with a vulnerability scanner.

## Troubleshooting

**`Activate.ps1 cannot be loaded because running scripts is disabled`**
PowerShell's execution policy blocks the script. Allow scripts for your user only:
`Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`

**`[WinError 10013]` when starting uvicorn, or "port already in use"**
Another process holds port 8000 or 5173, often the Docker stack. Check with
`Get-NetTCPConnection -LocalPort 8000,5173 -State Listen` and stop one of the two setups.

**`error during connect ... dockerDesktopLinuxEngine`**
Docker Desktop is not running. Start it and wait until the engine is up.

**The page shows "Cannot reach the server"**
The backend is not running, or the browser origin is not in `CORS_ORIGINS`. Check <http://localhost:8000/health>.

**`npm create vite ... -- --template react` creates the wrong template in PowerShell**
PowerShell swallows `--`. Use `npx create-vite@latest . --template react` instead. (Only relevant when scaffolding a new frontend.)

**A URL you expect to work returns "URL destination is not allowed"**
It resolves to a private, loopback, or link-local address. This is intentional.
