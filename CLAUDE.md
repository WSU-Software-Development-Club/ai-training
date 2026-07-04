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
- **ML → GitHub Actions** (`weekly_predictions.yml`): still active. Runs
  `ml/m1/predict_upcoming.py` on a **GitHub-hosted `ubuntu-latest` runner** (not on troyster)
  every Tuesday 09:00 UTC (plus manual `workflow_dispatch`). The runner joins the tailnet via
  `tailscale/github-action` and writes predictions (upsert on `ncaa_game_id`) to the **troyster
  Postgres over Tailscale**. The API reads them back. Secrets: `CFBD_API_KEY`, `DATABASE_URL`,
  `TS_AUTHKEY`.

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

## 9. Matchup-intelligence pipeline

### 9.1 What it is
A second, newer ML subsystem living under **`ml/matchup_intel/`**, separate from the `ml/m1/`
score models of §1–§8. Instead of predicting a final score, it builds a per-game **factor
deck**: the individual tailwinds/headwinds that tilt a matchup (QB availability, weather, …),
each scored for direction/magnitude/confidence, ranked, historically grounded, and traceable
back to its source. It is surfaced at **`/matchup/:gameId`** in the SPA (a two-sided "edge
board"), served by the Flask **`/matchup/<ncaa_game_id>`** endpoint, and reuses the **same
troyster Postgres** as the rest of the app (its tables live in `db/schema.sql` alongside
`predictions`). Currently shipped as a **QB + weather vertical slice**; other categories
(OL/DL/rest/travel/…) are scaffolded but not yet populated.

**Two non-negotiable invariants** shape the whole design:
1. **The LLM is a feature EXTRACTOR/CONTEXTUALIZER, never a predictor.** It characterizes one
   factor; it never sees or emits anything about the game outcome, score, or winner.
2. **Point-in-time correctness + a sample-size guard** are enforced *structurally* (at the
   serving boundary), not by convention — see §9.7 gotchas 4–5.

### 9.2 Layered architecture
The pipeline is a linear, idempotent, re-runnable set of layers (see `flows.py` for the DAG:
`ingest → extract+ground → serve`). Each stage fails independently — one bad game does not
corrupt the others.
- **Layer 0 — ingest** (`ingest/`): raw signals land in `raw_signals` (idempotent, deduped on
  `content_hash`). Sources: bundled `seed.py`/`seed_data.json` (demo games), `seed_weather.py`,
  `polymarket_ingest.py`, plus the **prod backfills** `teams_backfill.py` (CFBD → `teams`
  dimension: coords + IANA tz), `weather_backfill.py` (real results × Open-Meteo →
  `weather_history` grounding), and `game_weather.py` (observed weather → real weather decks).
- **Layer 1 — LLM extract/contextualize** (`extract.py`): one Ollama (`gemma3`) call per raw
  signal with a **strict JSON schema** (Ollama structured outputs), validated through
  `schemas.LLMFactorOutput` (`extra="forbid"`, bounds `[0,1]`). Invalid output is **dropped**,
  never passed downstream; every call (including dropped ones) is persisted to `llm_calls` for
  audit. The hard part is judging *net* impact ("starter out, but blue-chip backup" → magnitude
  reduced) — a rubric + few-shot calibration in the prompt drive this.
- **Layer 2 — quantitative scorers** (`score/weather.py`): deterministic, **no LLM**. Weather
  magnitude comes from a calibrated severity rubric (wind/cold/heat/rain buckets), not the model.
- **Layer 3/4/5 — assemble** (`logic.py`, pure/side-effect-free): `dedupe_factors`
  (one per `(team, category)`, keep higher `magnitude×confidence`) → `rank_factors` (by
  `magnitude×confidence` desc) → `apply_sample_size_guard`.
- **Layer 4 — historical grounding** (`ground.py`): a per-category **registry** attaches
  `historical_rate` + `sample_size` ("how has this factor type performed historically?"). Weather
  → real team win-rate in that condition bucket (`weather_history`); QB → `sample_size=0` on
  purpose (no injury-outcome dataset yet, so the guard withholds any rate — intentional honesty).
- **Layer 5 — serve** (`serve.py`): reads persisted factors, applies point-in-time
  (`as_of ≤ kickoff`), assembles both teams' decks, attaches the Layer-6 reference panel, and
  materializes to `factor_decks`.
- **Layer 6 — reference panel** (`db.get_model_reference_panel`): the existing XGBoost
  prediction (`model`), the `vegas` over/under, and `polymarket` implied win-probs — framed as
  outside **inputs, not the deck's verdict**, and rendered as such in the UI.

### 9.3 Stack (additions to §2)
- **Python 3.11**: `pydantic>=2.0` (the validation boundary), `psycopg[binary]>=3.1`, `requests`,
  `python-dotenv`, `PyYAML`. **Prefect is optional** — if absent, the `@task`/`@flow` decorators
  degrade to plain functions so the pipeline still runs via `python -m ml.matchup_intel.flows`.
- **LLM**: self-hosted **Ollama** running **`gemma3`**, reached over the compose network at
  `http://ollama:11434` (internal only). No hosted-LLM / API-key dependency.
- **External data**: College Football Data (`CFBD_API_KEY`, teams/results), **Open-Meteo**
  (weather, no key), **Polymarket** Gamma + CLOB APIs (public, no key; sparse CFB coverage).
- **Config** (`config.py` + `config.yaml`): precedence **env var > `config.yaml` > defaults**.
  Secrets (`DATABASE_URL`, `CFBD_API_KEY`) come from the env/`.env` **only**, never the committed
  yaml. Tunables: `ollama_url`, `ollama_model`, `sample_size_threshold` (30), `request_timeout`
  (180s, sized for a cold `gemma3` load), `polymarket_enabled`.

### 9.4 Directory layout
```
ml/matchup_intel/
├── flows.py            # Prefect DAG (degrades to plain fns): ingest → extract+ground → serve
├── config.py/.yaml     # env > yaml > defaults; secrets env-only
├── schemas.py          # Pydantic validation boundary (LLMFactorOutput, Factor, Source, ...)
├── extract.py          # Layer 1 — Ollama/gemma3 extract+contextualize (strict JSON, drop-if-invalid)
├── ground.py           # Layer 4 — per-category historical grounding registry
├── logic.py            # Layers 3/4/5 — pure dedupe/rank/point-in-time/guard (unit-testable)
├── serve.py            # Layer 5 — assemble + materialize factor_decks
├── db.py               # psycopg3 persistence (teams/raw_signals/factors/llm_calls/decks/weather)
├── score/weather.py    # Layer 2 — deterministic weather scorer (no LLM)
├── sources/            # cfbd.py, open_meteo.py, polymarket.py (Gamma discovery + CLOB pricing)
├── ingest/             # Layer 0: seed*, *_backfill (teams/weather), game_weather, polymarket_ingest
├── tests/              # point-in-time, sample-size guard, weather, polymarket, validation, extract
└── Dockerfile          # matchup-pipeline image (copies ml/ tree; `python -m ...flows` by default)
```

### 9.5 How it runs & is surfaced
- **Compose (opt-in profile):** the `ollama` and `matchup-pipeline` services in the base
  `docker-compose.yml` are gated behind **`--profile matchup`**, so a plain `docker compose up`
  and the `deploy.yml` `up -d --build backend` **never start them**. Bring up with
  `docker compose --profile matchup up -d --build ollama matchup-pipeline`, then a one-time
  `docker compose exec ollama ollama pull gemma3`. `matchup-pipeline` is a batch job
  (`restart: "no"`) that runs the flow once.
- **Prod data backfill → GitHub Actions** (`.github/workflows/matchup_backfill.yml`,
  **manual `workflow_dispatch` only**): a GitHub-hosted runner joins the tailnet (`tag:ci`,
  `TS_AUTHKEY`) and, against the troyster Postgres, runs in order: apply `schema.sql` →
  `teams_backfill` → `weather_backfill` (optional) → `game_weather`. Deliberately **does not
  install Prefect** (so it exercises the degrade-to-plain-functions path). Secrets:
  `DATABASE_URL`, `CFBD_API_KEY`, `TS_AUTHKEY`.
- **Backend serving:** `routes/matchup.py` (`matchup_bp`, `url_prefix='/matchup'`) →
  `services/matchup_service.py` → `utils/db.py::get_factor_deck_by_game`. Response uses the
  standard `{"success": true, "data": ...}` wrapper; **404** = no deck assembled yet.
- **Frontend:** route `/matchup/:gameId` → `pages/MatchupPage.jsx`, reached from
  `PredictionPage.jsx` and `ScoreCard.jsx` (`navigate(`/matchup/${ncaaGameId}`)`). API method
  `api.getMatchup(ncaaGameId)`; endpoint registered as `appConfig.endpoints.matchup` (`/matchup/`).
  Weather is a single shared row across both teams; team-specific factors split into "Working
  for/against them"; a reference panel shows model/vegas/polymarket as context.

### 9.6 Data model & conventions
- **Tables** (all in `db/schema.sql`, auto-loaded on DB init): `teams` (UUID identity + stadium
  coords/tz), `raw_signals` (+ `ingest_watermarks`), `factors`, `llm_calls`, `weather_history`,
  `factor_decks`. (`feature_definitions`/`feature_values`/`feature_sets`/`feature_snapshots` are a
  further, separate feature-store scaffold — not part of the QB/weather serving path.)
- **Identity/joins:** the engine keys teams by **UUID `team_id`**; the older `predictions` table
  keys teams by **TEXT name**. Bridge via `normalize_team_name()` → `teams.normalized_name`
  (lowercase, punctuation collapsed), exactly as `matchup_service._norm` and `db.py` do.
- **DB access:** psycopg3, parameterized SQL only (`%s`/named), TIMESTAMPTZ + UTC. The backend
  reader degrades to `[]`/`None` when Postgres is unreachable (same graceful-degrade as §7 #5).
- **Serving read shape:** `{ncaa_game_id, home_team, away_team, reference_panels, teams:[{team_id,
  team_name, is_home, factors:[...], betting:{...}, as_of_timestamp}]}`. Both teams are always
  returned when a prediction row exists (a team with no factors still gets a column).
- **Auditability:** every factor carries `derived_from_raw_ids` + `sources`; every LLM call
  (prompt + raw response, valid/dropped) is persisted to `llm_calls`. Re-runs are idempotent —
  ingest dedupes on `content_hash`, extraction `reset_game_factors` clears a game's prior
  factors + calls first, decks upsert on `(ncaa_game_id, team_id, as_of_timestamp)`.

### 9.7 Known gotchas
1. **Ollama is internal-only and cold-starts slowly.** `http://ollama:11434` must **NOT** be
   exposed via the Cloudflare Tunnel. The **first** `gemma3` inference lazy-loads the model into
   memory — hence the deliberately generous 180s `request_timeout`. The model must be pulled once
   (`ollama pull gemma3`) or every extraction fails and its output is dropped.
2. **Prefect is optional and its presence changes execution.** With Prefect absent (the tests,
   local runs, and `matchup_backfill.yml` all run this way), `@task`/`@flow` degrade to plain
   functions. Installing the full `requirements.txt` pulls Prefect and changes how stages
   execute — do not "fix" the backfill workflow by installing Prefect.
3. **Two team-identity schemes.** UUID `team_id` (engine) vs. TEXT name (`predictions`). Joins go
   through `normalize_team_name`/`normalized_name`; a casing/punctuation drift between the two
   normalizers silently yields an unmatched team (empty factor column), not an error.
4. **Point-in-time is the #1 silent-cheat vector — but the reference panel is exempt by design.**
   `logic.filter_point_in_time` is strict: a signal is visible only if **both** `as_of_timestamp`
   **and** `published_at` are ≤ kickoff (missing `published_at` falls back to `as_of`). However
   the Layer-6 reference panel (model/vegas/**polymarket**) intentionally reads *current* state,
   not point-in-time — consistent with how `model`/`vegas` always behaved; don't "fix" it to
   filter.
5. **Sample-size guard withholds the rate, not the record.** Below `sample_size_threshold` (30)
   the headline `historical_rate` is set to `None` and `historical_rate_withheld=true` — a
   small-sample percentage physically cannot reach the UI. The `grounding` block still carries
   raw wins/total/baseline, which the frontend shows muted + flagged "thin". **QB grounding
   always returns `sample_size=0`** (no injury-outcome dataset in v1), so QB rates are *always*
   withheld — that's intentional, not a bug.
6. **Polymarket `None` is data, never an error.** Most CFB games have no market, so
   `find_game_market`/`fetch_game_odds` return `None` (and write nothing) for both "no market
   exists" and "not ingested yet" — treat identically as an explicit null; never retry/alert on
   it. Egress is to `gamma-api.polymarket.com`/`clob.polymarket.com` over the **open internet**
   (not the compose network, not the tunnel); disable with `POLYMARKET_ENABLED=false` if troyster
   egress is blocked. Price snapshots are intentionally **not** deduped across runs (prices move).
7. **A 404 from `/matchup/<id>` is expected for most games.** It means no factor deck has been
   assembled yet (only seeded/backfilled games have one). The frontend treats a 404 as an "empty"
   state, not an error — don't surface it as a failure.
8. **Shared schema & volume.** The matchup tables live in the same `db/schema.sql` and `pgdata`
   volume as `predictions`; `docker compose down -v` destroys factor decks too. Schema changes
   must stay in sync across `db/schema.sql`, `ml/matchup_intel/db.py` (writer), and
   `backend/utils/db.py` (reader).

### 9.8 Do-not-touch additions (see §8)
- **`ml/matchup_intel/config.yaml`** — the `ollama_url` is an internal compose address; never
  point it at a public/tunnelled host. Secrets belong in the env, never here.
- **`matchup_backfill.yml`** and its secrets (`DATABASE_URL`, `CFBD_API_KEY`, `TS_AUTHKEY`) —
  a manual prod migration that writes directly to the live troyster Postgres.
- **`ml/matchup_intel/ingest/seed_data.json`** — the bundled demo games the pipeline and tests
  key on; changing it shifts what the seeded decks contain.
