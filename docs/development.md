# Development

How to run the stack locally, configure environment variables, and run the test
suites. For the production picture see [Deployment & Operations](deployment.md).

## Prerequisites

- **Docker** + Docker Compose (the preferred path — runs all three services with hot reload).
- **Python 3.11** (backend + ML, if running services individually).
- **Node 18** (frontend; see `.nvmrc`).
- A **Postgres** instance if you run the backend outside Compose.
- `CFBD_API_KEY` (College Football Data API) — required only for the ML pipeline.

## Quick start (Docker, recommended)

Runs frontend + backend + Postgres with hot reload for both services:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

- Frontend → http://localhost:3000
- Backend  → http://localhost:5000

> Use `docker-compose.dev.yml`, not the base `docker-compose.yml`. The base file
> has a quirk where the `frontend` service mounts **both** `./frontend` and
> `./backend` into `/app`; the dev file fixes this and enables `FAST_REFRESH`.

## Running services individually

**Backend**
```bash
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python app.py
```

**Frontend**
```bash
cd frontend && npm install && npm start
```

**ML pipeline**
```bash
cd ml && pip install -r requirements.txt
cd m1 && python predict_upcoming.py [year] [week]   # args optional; auto-detects
```

## Environment variables

Names only — copy the relevant `*env.example` and fill values locally. **Never
commit real values** (see the do-not-touch list in [Deployment](deployment.md)).

| Scope | Vars | Notes |
| --- | --- | --- |
| Backend / ML | `DATABASE_URL`, `CFBD_API_KEY` (ML only), `FLASK_ENV`, `FLASK_DEBUG`, `CORS_ORIGINS` | See `backend/env.example`, `ml/env.example`. |
| Compose | `BACKEND_PORT` (5000), `FRONTEND_PORT` (3000), `POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` | Backend derives `DATABASE_URL` from the `POSTGRES_*` values; `CORS_ORIGINS` is auto-derived from `FRONTEND_PORT`. |
| Frontend | `REACT_APP_API_URL` | Build-time; falls back to `http://localhost:5000`. |

Reference files: `env.example`, `backend/env.example`, `ml/env.example`.

> **DB degrades silently.** If `DATABASE_URL` is unset or Postgres is unreachable,
> `backend/utils/db.py` logs a warning and prediction queries return `[]`/`None`
> instead of erroring. A "no data" UI usually means a missing/incorrect
> `DATABASE_URL`, not an empty database.

## Database

The Postgres schema in [`db/schema.sql`](../db/schema.sql) is auto-loaded when the
`db` container initializes (into the `pgdata` volume). See [Database](database.md)
for the full table reference.

> `docker compose down -v` drops the `pgdata` volume and **destroys all stored
> predictions and factor decks.** Use `down` without `-v` to keep data.

## Running tests

**Backend** (pytest, against a Postgres with `db/schema.sql` loaded):
```bash
cd backend && pytest
```
See [`backend_route_testing_guide.md`](../backend_route_testing_guide.md) for route-test patterns.

**Matchup Intelligence Engine** (pure-logic + validation tests):
```bash
cd ml && pytest matchup_intel/tests
```

**Frontend** (Jest / React Testing Library):
```bash
cd frontend && npm test
```

CI runs `ruff` (lint, backend only — see `ruff.toml`) and `pytest` on every PR and
push to `main`. See [Deployment → CI/CD](deployment.md#cicd).

## Loading local mock data (matchup intel)

The Matchup Intelligence Engine reads from Postgres. To populate the local DB with
real 2025 grounding and (optionally) mock upcoming-season factor decks for UI work,
see [Matchup Intelligence Engine → Local data](matchup-intelligence.md). A matchup
page is reachable at `http://localhost:3000/matchup/<ncaa_game_id>` once a deck
exists for that game.
