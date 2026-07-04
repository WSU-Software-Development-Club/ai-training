# Deployment & Operations

Split deployment: the **backend runs on `troyster`** (Ubuntu homelab, IPv4 `192.168.1.126`,
Tailscale `100.110.59.39`) behind a **Cloudflare Tunnel**; the **frontend is on Vercel**; a
**Postgres** container runs on troyster (LAN/Tailscale only). Public app:
**https://football.wsu-swdc.dev**.

> Related: [`github_guide.md`](../github_guide.md). Secrets/config in the do-not-touch list
> at the bottom of this doc must never be printed or committed.

## Topology

- **Ingress → Cloudflare Tunnel.** The `cloudflared-ai` container
  (`cloudflare/cloudflared:latest`) is **token-authenticated** (`--token …`), so the
  hostname → service routing lives in the **Cloudflare Zero Trust dashboard** — there is **no
  `config.yml`/ingress file** in the repo or on the host.
- **Backend container:** `ai-training-backend-1` (image `ai-training-backend`), binds
  `0.0.0.0:5000` — API-only (does not serve the SPA).
- **Postgres:** `db` compose service (`postgres:16`, `pgdata` volume, schema auto-loaded from
  `db/schema.sql`). **Not tunnel-exposed** — reachable only over Tailscale/LAN.
- **Frontend → Vercel.** Flask does not serve the SPA; the compose `frontend` service is
  dev-only. `REACT_APP_API_URL` is set at Vercel build time to the backend's tunnel URL —
  a genuine cross-origin setup, so backend `CORS_ORIGINS` must include the frontend origin.
- **Separate project on the same host:** `cloudflared-sentiment` serves the unrelated
  "Sentiment Trends" SWDC project — **out of scope, do not touch.**
- **Optional `matchup` profile:** the base compose defines `ollama` + `matchup-pipeline`
  under `profiles: ["matchup"]` — **not** started by a plain `docker compose up` or by
  `deploy.yml`. `ollama` must **not** be tunnel-exposed; `matchup-pipeline` egresses to
  Polymarket over the open internet when `POLYMARKET_ENABLED=true`.

## Compose files

**`docker-compose.yml`** (base — the prod source of truth on troyster at
`/home/troymuehlbauer/ai-training/docker-compose.yml`):
- `backend`: build `./backend`, port `${BACKEND_PORT:-5000}:5000`, `command: python app.py`, depends on healthy `db`, `restart: unless-stopped`.
- `db`: `postgres:16`, `pgdata` + `./db/schema.sql:/docker-entrypoint-initdb.d/schema.sql:ro`, `pg_isready` healthcheck.
- `frontend`: **dev-only.** ⚠️ **Quirk:** mounts **both** `./frontend:/app` and `./backend:/app`. Use the dev file instead.
- `CORS_ORIGINS` = `https://football.wsu-swdc.dev,http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT}`.
- `DATABASE_URL` = `postgresql://${POSTGRES_USER:-aitraining}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB:-aitraining}` (requires `POSTGRES_PASSWORD`).

**`docker-compose.dev.yml`** (preferred for local dev): same three core services (no matchup
profile); `frontend` mount fixed to just `./frontend:/app` + `FAST_REFRESH`/polling for hot
reload; `CORS_ORIGINS` local-only. `backend` still runs `python app.py`.

## Dockerfiles

- **`backend/Dockerfile`:** `python:3.11-slim`, `pip install -r requirements.txt`, `EXPOSE 5000`, `CMD ["python", "app.py"]`.
- **`frontend/Dockerfile`:** `node:18-alpine`, `npm install`, non-root user, `EXPOSE 3000`, `CMD ["npm", "start"]` (dev-only image; the live frontend is Vercel's own build).

> **Tech debt — dev server in production.** Both the backend Dockerfile `CMD` and the compose
> `command` run `python app.py` (Flask dev server + reloader) in prod. `gunicorn` is in
> `requirements.txt` but never invoked; there's no WSGI entrypoint. Should become
> `gunicorn -w N app:app` (module-level `app = create_app()` is the target).

## CI/CD

Four workflows in [`.github/workflows/`](../.github/workflows/):

### `ci.yml` — lint + test
Triggers: `pull_request`, `push` to `main`, `workflow_dispatch`.
- `lint`: `ruff check backend` (backend-only, per `ruff.toml`).
- `test`: spins up a `postgres:16` service, loads `db/schema.sql`, runs `pytest -v` from `backend/`.

### `deploy.yml` — deploy to troyster
Triggers: `push` to `main`, `workflow_dispatch`. `concurrency: deploy-troyster`,
`cancel-in-progress: false` (serialized — never two deploys at once).
- Joins the tailnet (`tailscale/github-action@v2`, `TS_AUTHKEY`, `tag:ci`).
- SSHes to `DEPLOY_HOST=100.110.59.39` as `troymuehlbauer` with `DEPLOY_KEY`, then:
  `git fetch origin && git reset --hard origin/main`, `docker compose up -d --build backend`,
  `docker image prune -f`. **`db`/`pgdata` are left running** (not rebuilt); frontend is on
  Vercel and untouched.

### `weekly_predictions.yml` — weekly score predictions
Triggers: `schedule: 0 9 * * 2` (Tue 09:00 UTC) + `workflow_dispatch` (optional `year`/`week`).
- GitHub-hosted runner: installs `ml/requirements.txt`, joins the tailnet, runs
  `ml/m1/predict_upcoming.py`, uploads any `predictions_*.json` fallback artifact. Writes to
  troyster Postgres over Tailscale (upsert on `ncaa_game_id`). See
  [ML → weekly job](ml-predictions.md#the-weekly-job).

### `matchup_backfill.yml` — matchup intel prod data backfill
Trigger: `workflow_dispatch` only. Inputs: `season` (default 2025), `min_week` (default 0),
`run_weather_history` (default true). `timeout-minutes: 180`. Installs a minimal dep set (no
Prefect, so `flows.py` decorators degrade to plain functions), joins the tailnet, then runs
in order: apply `db/schema.sql` (idempotent) → `teams_backfill` → (conditionally)
`weather_backfill` → `game_weather <season> <min_week>`.

## Secrets & environment

**GitHub Actions secrets:** `TS_AUTHKEY` (ephemeral, `tag:ci`), `DEPLOY_KEY` (SSH,
`deploy.yml` only), `DATABASE_URL`, `CFBD_API_KEY`.

**Env by file (names only):**
- `env.example` (compose): `BACKEND_PORT`, `FRONTEND_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` (`CORS_ORIGINS` auto-derived from `FRONTEND_PORT`).
- `backend/env.example`: `FLASK_ENV`, `FLASK_DEBUG`, `CORS_ORIGINS`, `DATABASE_URL`.
- `ml/env.example`: `CFBD_API_KEY`, `DATABASE_URL` (example uses the troyster LAN/Tailscale address).
- No `frontend/env.example`; `REACT_APP_API_URL` is set at Vercel build time.

## Local development

```bash
docker-compose -f docker-compose.dev.yml up --build   # frontend :3000, backend :5000
```

See [Development](development.md) for individual-service commands and env setup.

## Do-not-touch list

These run the live site or hold secrets — never print, commit, or casually modify:

- `.env` / `backend/.env` (gitignored — real `DATABASE_URL`/password). Edit `*env.example` instead.
- GitHub Actions secrets (`CFBD_API_KEY`, `DATABASE_URL`, `TS_AUTHKEY`, `DEPLOY_KEY`).
- The troyster prod compose file's live state and the **`cloudflared-ai` tunnel token** (passed via `--token`). Hostname routing changes in the Cloudflare Zero Trust dashboard, not the repo.
- `cloudflared-sentiment` / the "Sentiment Trends" project.
- Vercel project config (build settings, `REACT_APP_API_URL`, custom domain).
- The `weekly_predictions.yml` cron schedule and its secrets.
- The Postgres schema/`pgdata` volume — schema changes require moving `db/schema.sql` + the ML writer + the backend reader together (see [Database → schema-change protocol](database.md#schema-change-protocol)). `docker compose down -v` destroys all stored predictions and decks.
