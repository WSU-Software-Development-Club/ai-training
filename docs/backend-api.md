# Backend API Reference

The backend is a **Flask 2.3 JSON API** (Python 3.11) using the app-factory +
blueprint pattern. It proxies live NCAA data and serves model output from Postgres.
It is **API-only** — it does not serve the React SPA (that's on Vercel).

- Source: [`backend/`](../backend/)
- Onboarding walkthrough: [`backend_guide.md`](../backend_guide.md)
- Route-testing patterns: [`backend_route_testing_guide.md`](../backend_route_testing_guide.md)
- Interactive API docs: **`/apidocs`** (Swagger UI, backed by hand-authored `backend/openapi.yaml`)

## App structure

`backend/app.py` — `create_app(config_name=None)`:
- Resolves `config_name` from `FLASK_ENV` (default `development`), loads `config[config_name]` from `config.py`.
- Sets up logging (`utils/helpers.setup_logging`), enables `CORS(app, origins=app.config['CORS_ORIGINS'])`.
- Registers blueprints: `main`, `api`, `history`, `rankings`, `stats`, `scoreboard`, `team`, `matchup`, plus `docs` + Swagger UI at `/apidocs`.
- Module-level `app = create_app()` is the WSGI target a `gunicorn app:app` would import.

`backend/config.py` — env-driven `Config` base + `Development`/`Production` subclasses, selected by `FLASK_ENV`. Loads `.env` via `python-dotenv` at import. Reads `FLASK_DEBUG`, `FLASK_RUN_HOST`, `FLASK_RUN_PORT`, `CORS_ORIGINS` (comma-split), `DATABASE_URL`.

**Convention:** one blueprint per domain in `routes/*.py`, each with its own `url_prefix`. Handlers are thin and delegate to `services/*.py`; no business logic in routes.

## Response envelope

**Domain routes** wrap their payload:

```jsonc
// success
{ "success": true, "data": <payload>, /* + metadata: stat_name, team_name, count, data_type, message */ }
// failure
{ "success": false, "error": "<msg>" }   // HTTP 404 (named resource not found) or 500 (upstream/service error)
```

**Documented exceptions — no `success` key** (bare objects): `GET /`, `GET /about`,
`GET /api/health`, `GET /api/status`. Don't assume the wrapper is universal.

## Routes

### `main` — no prefix (`routes/main.py`)
| Method | Path | Returns |
| --- | --- | --- |
| GET | `/` | `{message, app_name, version, timestamp}` — API root (not the SPA) |
| GET | `/about` | `{name, version, description, status}` |

### `api` — `/api` (`routes/api.py`)
| Method | Path | Returns |
| --- | --- | --- |
| GET | `/api/health` | `{status, timestamp, version}` — bare object |
| GET | `/api/status` | `{name, version, status, uptime, database: {connected}}` — bare object; `connected` from `db.is_connected` |

### `history` — `/history`
| GET | `/history/champions` | FBS championship winners (NCAA API). `{success, data, count, message}`; 500 on failure |

### `rankings` — `/rankings`
| GET | `/rankings/ap-top25` | AP Top 25 (NCAA API). `{success, data, data_type}`; 500 on failure |

### `stats` — `/stats`
| Method | Path | Notes |
| --- | --- | --- |
| GET | `/stats/stat/<int:stat_id>` | All teams for a stat id. `{success, data, stat_name}` |
| GET | `/stats/stat/<int:stat_id>/team/<team_name>` | One team's stat. **404** if not found |
| GET | `/stats/offense` | stat id 21 |
| GET | `/stats/offense/rushing` | stat id 23 |
| GET | `/stats/defense` | stat id 22 |
| GET | `/stats/defense/rushing` | stat id 24 |
| GET | `/stats/offense/team/<team_name>` | **404** if not found |
| GET | `/stats/defense/team/<team_name>` | **404** if not found |

> `stats_service.py` defines ~50 per-category helpers (for every `STAT_CATEGORIES`
> id), but only the routes above are wired up. Other categories are reachable
> generically via `/stats/stat/<id>`.

### `scoreboard` — `/scoreboard`
| GET | `/scoreboard/week/<int:week>?year=<int>` | NCAA scoreboard **merged with** Postgres predictions by `ncaa_game_id`. `year` optional (falls back to CFB-season-aware current year). `{success, data, data_type}` |

### `team` — `/team`
| Method | Path | Notes |
| --- | --- | --- |
| GET | `/team/<team_name>/record` | Team standings/record (NCAA API). **404** if not found |
| GET | `/team` and `/team/` | All FBS teams. `{success, data, data_type, count}` |

### `matchup` — `/matchup`
| GET | `/matchup/<int:ncaa_game_id>` | Postgres-only. **404** if no deck (also returned when Postgres is unreachable) |

`data` shape (the two-sided factor board — see [Matchup Intelligence Engine](matchup-intelligence.md)):

```jsonc
{
  "ncaa_game_id": 401856888,
  "home_team": "Texas A&M", "away_team": "Tennessee",
  "reference_panels": { "model": {...}, "vegas": {...}, "polymarket": {...} | null },
  "teams": [
    { "team_id", "team_name", "is_home": true,
      "factors": [ /* guard-rendered factor view objects */ ],
      "betting": { "predicted_points", "spread", "over_under" },
      "as_of_timestamp" }
    /* ...away */
  ]
}
```

### `docs`
| GET | `/openapi.yaml` | Raw OpenAPI spec (`backend/openapi.yaml`) |
| GET | `/apidocs` | Swagger UI |

## Services layer (`backend/services/`)

| Module | Source | Key functions |
| --- | --- | --- |
| `history_service` | NCAA API | `get_championship_winners()` |
| `rankings_service` | NCAA API | `get_ap_rankings()` |
| `stats_service` | NCAA API (paginated) | `get_stat_category_name`, `get_all_teams_stats`, `get_team_stats`, + ~50 per-category wrappers |
| `scoreboard_service` | NCAA API **+ Postgres** | `get_scoreboard_data(week, year)`, `process_games(...)` — merges predictions by `ncaa_game_id` |
| `team_service` | NCAA API | `normalize_team_name`, `get_team_record`, `get_all_teams` |
| `matchup_service` | Postgres only | `get_matchup_deck(ncaa_game_id)`, `_betting(is_home, pred)`, `_norm(name)` |

## Utilities

- **`utils/db.py`** — `PredictionsDB` wraps a `psycopg_pool.ConnectionPool` (`dict_row`, size 1–5), connects via `DATABASE_URL`. Read methods: `get_predictions`, `get_prediction_by_game_id`, `get_predictions_by_week`, `get_prediction_by_ncaa_game_id`, `get_predictions_by_team`, `get_latest_predictions`, `get_factor_deck_by_game`. Module singleton exposed via `get_db()`.
  > **Silent degrade:** if `psycopg` is missing, `DATABASE_URL` is unset, or the pool fails to init, `is_connected` is `False` and every read returns `[]`/`None` (logged, never raised). A "no data" UI usually means a DB/config problem, not an empty table.
- **`utils/helpers.py`** — `setup_logging()`, `get_current_season_year()` (Jan–Jul rolls back to the prior CFB season; mirrors `frontend/src/utils/helpers.js`).
- **`api_vars.py`** — `NCAA_API_BASE_URL = "https://ncaa-api.henrygd.me"` (hardcoded constant), and `STAT_CATEGORIES` — the ~50-entry stat-id → name map.

## Environment variables

| Var | Purpose |
| --- | --- |
| `FLASK_ENV` | selects config class |
| `FLASK_DEBUG` | `Config.DEBUG` (Production forces `False`) |
| `FLASK_RUN_HOST` / `FLASK_RUN_PORT` | dev-server bind (`0.0.0.0` / `5000`) |
| `CORS_ORIGINS` | comma-separated allowed origins; prod must list the Vercel / `football.wsu-swdc.dev` origin |
| `DATABASE_URL` | Postgres DSN; unset → silent degrade |

## Gotchas

- **Duplicated stat map.** `api_vars.STAT_CATEGORIES` (backend) and `STAT_NAME_TO_ID` in `frontend/src/services/api.js` are maintained independently with slightly different label casing. Mirror any change in both.
- **Dev server in production (tech debt).** Both `backend/Dockerfile` `CMD` and the compose `command` run `python app.py` (Flask dev server + reloader). `gunicorn` is in `requirements.txt` but unused; there's no WSGI entrypoint wired up. Should become `gunicorn -w N app:app`.
- **Scoreboard match quirk.** Prediction attachment matches on `ncaa_game_id` alone (season/week intentionally not gated), because the ML writer's CFBD week numbering can diverge from the NCAA display week.
