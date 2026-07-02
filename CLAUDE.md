# CLAUDE.md — CFB Analytics & Predictions

## 1. Project summary
A college-football analytics and predictions web app: a React SPA frontend backed by a
Flask JSON API, with an offline ML pipeline that produces weekly game-score predictions.
The API proxies live NCAA data (rankings, stats, scoreboards) and serves model predictions
stored in a self-hosted Postgres database on troyster. It is the WSU Software Development Club's training/teaching project
(repo `WSU-Software-Development-Club/ai-training`, default branch `main`), deployed publicly
at **https://football.wsu-swdc.dev**. The **backend is self-hosted on `troyster`** (an Ubuntu
homelab node) and exposed via a **Cloudflare Tunnel**; the **frontend is deployed on Vercel**;
the score models retrain/predict weekly via a **GitHub Actions** cron. (Render is no longer
used — see §5 and the tech-debt note in §7.)

## 2. Stack
- **Backend:** Python 3.11, Flask 2.3.3, Flask-CORS 4.0.0, python-dotenv, requests,
  `psycopg[binary,pool]>=3.1`, gunicorn 21.2.0. App-factory + blueprints. Package manager: pip.
- **Frontend:** React 18.2, react-router-dom **7.9.4**, react-scripts 5.0.1 (Create React App),
  papaparse, react-icons. Node 18 (`.nvmrc`). Package manager: npm.
- **ML (`ml/`):** Python 3.11, xgboost ≥2.0, scikit-learn, pandas, numpy, scipy, optuna,
  matplotlib, seaborn, `psycopg`. Models are XGBoost regressors (separate home/away score models).
- **Data stores / external APIs:** self-hosted Postgres on troyster (`predictions` table), NCAA API
  (`ncaa-api.henrygd.me`), College Football Data API (`collegefootballdata.com`, needs `CFBD_API_KEY`).

## 3. Directory layout
```
├── backend/                 # Flask API (app-factory pattern)
│   ├── app.py               # create_app(): registers all blueprints, CORS, logging
│   ├── config.py            # Config classes (dev/prod) from env vars
│   ├── api_vars.py          # NCAA_API_BASE_URL + STAT_CATEGORIES id→name map
│   ├── routes/              # One blueprint per domain (api, main, history,
│   │                        #   rankings, stats, scoreboard, team)
│   ├── services/            # Data-fetch logic called by routes (NCAA/Postgres)
│   ├── utils/               # helpers.py (logging), db.py (Postgres client, psycopg)
│   ├── tests/               # test_routes.py, test_services.py
│   └── Dockerfile
├── frontend/                # React SPA (CRA)
│   ├── src/
│   │   ├── pages/           # Route-level pages (Home, Rankings, Stats, Teams, Team,
│   │   │                    #   Comparison, Prediction)
│   │   ├── components/      # Reusable UI (tables, cards, nav, logos)
│   │   ├── services/api.js  # Central fetch wrapper (retry + timeout)
│   │   ├── constants/       # appConfig (apiUrl, endpoints), colors, spacing, css
│   │   ├── data/            # csvLoader + teamDataService (cached team CSV)
│   │   ├── branding/, matching/, hooks/, utils/
│   │   └── App.jsx          # Router + route table
│   ├── public/              # index.html, cfb_teams.csv (team branding source), logo
│   └── Dockerfile
├── ml/
│   ├── m1/                  # "Model 1": train_model.py, predict_upcoming.py, pr_all.py
│   │   ├── models/          # Trained XGBoost artifacts + metrics/feature importance
│   │   └── results/
│   └── training_data/       # collect_data.py + training_data.csv
├── db/                      # schema.sql — Postgres predictions schema (auto-loaded on init)
├── .github/workflows/       # ci.yml (lint+test), deploy.yml (push→troyster), weekly_predictions.yml
├── ruff.toml                # lint config (backend; ml excluded for now)
├── docker-compose.yml       # Base compose (see gotcha #4)
├── docker-compose.dev.yml   # Dev compose with hot reload (preferred)
└── *_guide.md               # backend/frontend/github/testing guides (onboarding docs)
```

## 4. Local development
Preferred (Docker, hot reload for both services):
```bash
docker-compose -f docker-compose.dev.yml up --build
# Frontend → http://localhost:3000   Backend → http://localhost:5000
```
Run services individually:
```bash
# Backend
cd backend && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt && python app.py
# Frontend
cd frontend && npm install && npm start
```
ML pipeline locally:
```bash
cd ml && pip install -r requirements.txt
cd m1 && python predict_upcoming.py [year] [week]   # args optional; auto-detects
```
Env vars (names only — see `env.example`, `backend/env.example`, `ml/env.example`):
- Backend/ML: `DATABASE_URL`, `CFBD_API_KEY` (ML only),
  `FLASK_ENV`, `FLASK_DEBUG`, `CORS_ORIGINS`.
- Ports/CORS/DB (compose): `BACKEND_PORT` (5000), `FRONTEND_PORT` (3000),
  `POSTGRES_DB`/`POSTGRES_USER`/`POSTGRES_PASSWORD` (backend derives `DATABASE_URL` from these);
  `CORS_ORIGINS` is auto-derived from `FRONTEND_PORT` in the compose files.
- Frontend: `REACT_APP_API_URL` (build-time; falls back to `http://localhost:5000`).

## 5. Deployment topology
Split deployment: the **backend runs on `troyster`** (Ubuntu homelab node, IPv4
`192.168.1.126`, reachable over Tailscale) behind a Cloudflare Tunnel, and the **frontend is
hosted on Vercel**. Compose files are the source of truth for what runs on troyster:
`/home/troymuehlbauer/ai-training/docker-compose.yml` (prod) and `docker-compose.dev.yml`
(local dev).
- **Public routing → Cloudflare Tunnel.** The `cloudflared-ai` container
  (`cloudflare/cloudflared:latest`) is **token-authenticated** (`--token …`), so the
  hostname→service mapping lives in the **Cloudflare Zero Trust dashboard**, not in any local
  file. There is **no `config.yml`/ingress file** in the repo or on the host — do not add or
  look for one. (A separate `cloudflared-sentiment` container on troyster serves an unrelated
  SWDC project, "Sentiment Trends" — don't touch or confuse it with this one.)
- **Backend container:** `ai-training-backend-1`, built from local image `ai-training-backend`,
  listening on `0.0.0.0:5000` on the host. This is an **API-only** service (see §6 — Flask
  returns JSON at `/`; it does **not** serve the SPA).
- **Backend start command — PRODUCTION ISSUE:** both the `Dockerfile` CMD and the compose
  `command` run **`python app.py`**, i.e. the **Flask development server with the reloader**.
  `gunicorn` is in `requirements.txt` but unused. This should be switched to a WSGI server
  (e.g. `gunicorn -w N app:app`) for production. Flagged as tech debt.
- **Frontend → Vercel.** The SPA is built and hosted on Vercel (the Flask backend does **not**
  serve it, and the compose `frontend` service is a dev-only convenience — it does not run in
  production on troyster). `REACT_APP_API_URL` is set at Vercel build time to the backend's
  public (tunnel) URL. This is a genuine cross-origin setup, so the backend `CORS_ORIGINS`
  must include the Vercel frontend origin (see §7 gotcha 1).
- **Public hostnames:** `https://football.wsu-swdc.dev` is the app. Which host maps to the
  Vercel frontend vs. the tunnel-exposed backend API (e.g. an `api.*` subdomain, or a
  path-based split) is not derivable from the repo — TODO: fill in the exact frontend URL and
  backend API URL.
- **Database → Postgres container** on troyster (`postgres:16`, `db` compose service, `pgdata`
  volume; schema auto-initialized from `db/schema.sql`). The backend reaches it at `db:5432` via
  `DATABASE_URL`. Not exposed through the Cloudflare Tunnel — reachable over Tailscale/LAN only.
- **CI/CD → GitHub Actions.** Three workflows in `.github/workflows/`:
  - `ci.yml` — on PRs and push to `main`: `lint` (ruff, backend only — see `ruff.toml`) and
    `test` (pytest against a `postgres:16` service container, schema loaded from `db/schema.sql`).
  - `deploy.yml` — on push to `main`: joins the tailnet (Tailscale auth key, `tag:ci`), SSHes to
    troyster with `DEPLOY_KEY`, then `git pull` + `docker compose up -d --build backend`.
    Serialized via a `concurrency` group; `db`/`pgdata` are left running.
  - `weekly_predictions.yml` — Tue 09:00 UTC (+ manual): joins the tailnet (auth key) and runs
    `ml/m1/predict_upcoming.py` on a **GitHub-hosted runner**, writing predictions (upsert on
    `ncaa_game_id`) to the **troyster Postgres over Tailscale**. The API reads them back.
- **GitHub Actions secrets:** `TS_AUTHKEY` (ephemeral, tagged `tag:ci`), `DEPLOY_KEY` (SSH),
  `DATABASE_URL`, `CFBD_API_KEY`.

## 6. Conventions
- **Routes:** one Blueprint per file in `backend/routes/`, each with a `url_prefix`
  (`/api`, `/rankings`, `/stats`, `/scoreboard`, `/team`, `/history`; `main` has none),
  all registered in `create_app()`. Routes are thin and delegate to `services/`.
- **API response shape (domain routes):** success →
  `{"success": true, "data": <payload>, ...metadata}` (e.g. `stat_name`, `team_name`);
  failure → `{"success": false, "error": "<msg>"}` with HTTP `404` (not found) or `500`
  (upstream fetch failed). **Exception:** `/api/health` and `/api/status` return plain
  objects **without** a `success` key — don't assume the wrapper is universal.
- **Frontend API calls:** all go through `src/services/api.js` → `apiRequest()`, which uses
  `fetchWithRetry` (3 retries, exponential backoff, 90s timeout) against
  `appConfig.apiUrl`. Add new endpoints to `appConfig.endpoints` (`constants/index.js`) and
  expose a method on the `api` object rather than calling `fetch` directly.
- **State:** no Redux/global store. Local component state + module-level caches
  (e.g. `data/teamDataService.js` caches the parsed team CSV; call `preloadTeamData()` on boot).
- **Team branding:** sourced from `frontend/public/cfb_teams.csv` (parsed with papaparse),
  not from the API.

## 7. Known gotchas
1. **CORS:** the API only allows origins in `CORS_ORIGINS`. Locally this is auto-set from
   `FRONTEND_PORT`; in production it must explicitly list the Vercel/`football.wsu-swdc.dev`
   origin or browser calls will fail.
2. **Stale Render assumptions (tech debt):** `frontend/src/services/api.js` still uses a 90s
   timeout + 3 retries "to handle Render spin-up" and pings `/api/health` on load ("Backend
   warming up…"). The Render cold-start rationale is **obsolete** now that the backend is an
   always-on container on troyster; the retry wrapper is harmless but the comments mislead.
   `backend/env.example` also references Render (`PORT` auto-set, `FLASK_ENV=production` on
   Render) — that is decommissioned and should be cleaned up. **Vercel is NOT stale** — it is the
   live frontend host; its CORS-origin note in `env.example` still applies.
3. **Stat map duplicated:** the stat-name→id table exists in **both** `backend/api_vars.py`
   (`STAT_CATEGORIES`) and `frontend/src/services/api.js` (`STAT_NAME_TO_ID`). Changes must be
   mirrored in both, and the two use slightly different casing for some labels.
4. **`docker-compose.yml` (base) quirk:** the `frontend` service mounts **both** `./frontend`
   and `./backend` into `/app`. Use `docker-compose.dev.yml` for development (it fixes this and
   enables `FAST_REFRESH`).
5. **DB client degrades silently:** if `DATABASE_URL` is unset or Postgres is unreachable,
   `backend/utils/db.py` prints a warning and prediction queries return `[]`/`None` rather than
   erroring — a "no data" UI often means a missing/incorrect `DATABASE_URL`, not an empty DB.
6. **CRA + react-router-dom 7:** router v7 in a `react-scripts` 5 app; watch for version-specific
   API differences when adding routes.
7. **Weekly job needs Tailscale:** the GitHub-hosted runner reaches troyster Postgres only after
   `tailscale/github-action` joins the tailnet (auth key, `tag:ci`). If `TS_AUTHKEY` expires
   or the ACL `tag:ci` loses
   access to `tcp:5432`, the save fails and the job falls back to writing a local JSON artifact.

## 8. Do-not-touch list
- **`/.env`, `backend/.env`** and any real env values — contain the Postgres password / `DATABASE_URL`. They are
  gitignored (not tracked); never commit them or paste values into code/docs. Edit
  `*env.example` files instead.
- **GitHub Actions secrets** (`CFBD_API_KEY`, `DATABASE_URL`, `TS_AUTHKEY`, `DEPLOY_KEY`) — configured in
  the repo settings, not in code.
- **`ml/m1/models/`** — committed trained model artifacts (`*_model.json`, metrics,
  feature-importance, `optimized_params.json`). Regenerate via `train_model.py`; don't hand-edit.
- **troyster production compose** (`/home/troymuehlbauer/ai-training/docker-compose.yml`) and the
  **Cloudflare Tunnel token** for `cloudflared-ai` — these run the live site. The tunnel token is
  a secret passed via `--token`; never print or commit it. Hostname routing is changed in the
  Cloudflare Zero Trust dashboard, not in the repo.
- **`cloudflared-sentiment`** and anything for the "Sentiment Trends" project — a *different*
  SWDC deployment sharing the troyster host. Out of scope for this repo.
- **Vercel project config** for the frontend (build settings, `REACT_APP_API_URL`, custom
  domain) — lives in the Vercel dashboard, not the repo; changes here affect the live site.
- **`weekly_predictions.yml` schedule** and its GitHub Actions secrets — changing the cron or
  secrets affects the live weekly prediction run.
- **Postgres `predictions` table / schema** (`db/schema.sql`) and the **`pgdata` volume** — written
  by the ML pipeline and read by the API; schema changes require updating `db/schema.sql`,
  `ml/m1/predict_upcoming.py` (writer), and `backend/utils/db.py` (reader) together. Dropping
  `pgdata` (e.g. `docker compose down -v`) destroys all stored predictions.
