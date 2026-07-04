# Architecture

A college-football **analytics and predictions** web app. A React SPA talks to a Flask JSON
API, which proxies live NCAA data and serves model output from a self-hosted Postgres
database. Two offline pipelines feed that database.

## The three subsystems

| Subsystem | Lives in | Produces | Doc |
| --- | --- | --- | --- |
| **Web app** | `frontend/` (SPA) + `backend/` (API) | The public site: rankings, stats, scoreboards, team pages, predictions, matchup pages | [Frontend](frontend.md), [Backend API](backend-api.md) |
| **Score models** | `ml/m1/`, `ml/training_data/` | Weekly home/away score predictions → `predictions` table | [ML — Score Predictions](ml-predictions.md) |
| **Matchup Intelligence Engine** | `ml/matchup_intel/` | Per-game scored, sourced factor decks → `factor_decks` table | [Matchup Intelligence Engine](matchup-intelligence.md) |

The two ML pipelines are **independent** and share only the Postgres database (both key games
on `ncaa_game_id`). Neither calls the backend API — they write to Postgres directly, and the
API reads it back.

## System map

```
                 ┌─────────────────────────────────────────────┐
   Browser  ───▶ │  React SPA (Vercel)   football.wsu-swdc.dev  │
                 └───────────────┬─────────────────────────────┘
                                 │  HTTPS (cross-origin, CORS)
                                 ▼
                 ┌─────────────────────────────────────────────┐
                 │  Cloudflare Tunnel (cloudflared-ai, token)   │
                 └───────────────┬─────────────────────────────┘
                                 ▼
                 ┌─────────────────────────────────────────────┐
                 │  Flask JSON API  (troyster, :5000)           │
                 │  proxies NCAA API  +  reads Postgres         │
                 └───────┬───────────────────────────┬─────────┘
             live data   │                           │  reads
                         ▼                           ▼
              ┌────────────────────┐      ┌───────────────────────────┐
              │  NCAA API          │      │  Postgres (troyster)       │
              │  ncaa-api.henrygd  │      │  predictions, factor_decks │
              └────────────────────┘      └───────▲──────────▲─────────┘
                                       writes │          │ writes
                          ┌────────────────────┘          └──────────────────────┐
              ┌───────────────────────────┐          ┌───────────────────────────┐
              │  Score models (ml/m1)      │          │  Matchup Intel (matchup_  │
              │  weekly GitHub Actions     │          │  intel) — CFBD/Open-Meteo/ │
              │  XGBoost home/away scores  │          │  Polymarket + Ollama LLM   │
              └───────────────────────────┘          └───────────────────────────┘
```

## Request flow (a page load)

1. The **SPA** (Vercel) issues a GET through `services/api.js` to the API's tunnel URL.
   `fetchWithRetry` handles transient blips; a session `responseCache` + `prefetchService`
   make most navigations render instantly from cache.
2. The request reaches the **Cloudflare Tunnel** → the **Flask API** on troyster.
3. A **blueprint** route delegates to a **service**, which either proxies the **NCAA API**
   (rankings/stats/scoreboards/records) or reads **Postgres** (predictions, factor decks).
4. The API returns the `{success, data, …}` envelope (see [Backend API](backend-api.md#response-envelope)).
   If Postgres is unreachable it **degrades silently** to empty results rather than erroring.

## Data flow (how the database gets populated)

- **Score predictions** — `weekly_predictions.yml` (Tue 09:00 UTC) runs `predict_upcoming.py`
  on a GitHub runner: pull CFBD data → rebuild the training feature schema → XGBoost predict →
  upsert into `predictions` on `ncaa_game_id`. See [ML → weekly job](ml-predictions.md#the-weekly-job).
- **Matchup factor decks** — the engine ingests raw signals (CFBD teams/venues, Open-Meteo
  weather, Polymarket odds), extracts factors (weather via a Python scorer, QB/injury/news via
  an Ollama LLM), grounds them against historical win-rates, then assembles guard-checked,
  ranked decks into `factor_decks`. See the [pipeline](matchup-intelligence.md#the-layered-pipeline).

## The id spaces

Games live in more than one id namespace — a frequent source of confusion:

- **`ncaa_game_id`** (NCAA API) is the **cross-table join key** — `predictions`, `factors`,
  `raw_signals`, `factor_decks` all key on it.
- **CFBD `game_id` / `cfbd_id`** are parallel, nullable ids (the ML/engine ingest matches
  CFBD games → NCAA games to obtain the `ncaa_game_id`).
- **`teams.team_id`** (UUID) is the FK target for the engine tables; `predictions` instead
  keys teams by **TEXT name**, bridged to `teams.normalized_name`.

Full detail: [Database → id spaces](database.md#the-id-spaces).

## Deployment at a glance

- **Frontend:** Vercel (build-time `REACT_APP_API_URL` → the backend tunnel URL).
- **Backend + Postgres:** the `troyster` homelab node; the API is exposed via a
  **Cloudflare Tunnel** (routing in the Zero Trust dashboard, no repo config), Postgres is
  LAN/Tailscale-only.
- **CI/CD:** GitHub Actions — `ci.yml` (lint + test), `deploy.yml` (push to `main` → SSH to
  troyster → rebuild the backend container), `weekly_predictions.yml`, `matchup_backfill.yml`.

Full detail: [Deployment & Operations](deployment.md).

## Tech stack

| Layer | Stack |
| --- | --- |
| Frontend | React 18.2, react-router-dom 7.9.4, CRA (react-scripts 5), papaparse, react-icons; Node 18 |
| Backend | Python 3.11, Flask 2.3.3, Flask-CORS, `psycopg[binary,pool]`, gunicorn (present, unused); app-factory + blueprints |
| ML | Python 3.11, XGBoost ≥2, scikit-learn, pandas/numpy/scipy, optuna; pydantic + (optional) Prefect + Ollama for the matchup engine |
| Data | Self-hosted Postgres 16; NCAA API, College Football Data API, Open-Meteo, Polymarket |

## Known cross-cutting gotchas

- **Silent DB degrade** — a "no data" UI usually means a missing/incorrect `DATABASE_URL`, not an empty database.
- **Duplicated stat map** — `backend/api_vars.py` `STAT_CATEGORIES` and `frontend/.../api.js` `STAT_NAME_TO_ID` are maintained by hand in parallel.
- **Dev server in production** — the backend runs the Flask dev server (`python app.py`) in prod; `gunicorn` is present but unwired (tech debt).
- **Stale Render assumptions** — retry/timeout comments in the frontend reference Render cold starts; the backend is now always-on on troyster.

See each domain doc for the full gotcha list.
