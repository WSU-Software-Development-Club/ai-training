# Known Issues & Tech Debt

A running register of tech debt, drift, and dead code across the codebase — surfaced while
writing this documentation set. Each item notes where it lives and a suggested fix. This is a
map for cleanup, not a list of blockers; nothing here breaks the live site today.

Severity is a rough triage: **High** = correctness or production risk · **Med** = misleading
/ drift that costs future dev time · **Low** = cosmetic / dead code.

## Backend & infrastructure

| # | Sev | Issue | Where | Suggested fix |
| --- | --- | --- | --- | --- |
| 1 | High | **Flask dev server runs in production.** Both the Dockerfile `CMD` and the compose `command` run `python app.py` (dev server + reloader). `gunicorn` is in `requirements.txt` but never invoked; no WSGI entrypoint is wired. | `backend/Dockerfile`, `docker-compose.yml` | Switch to `gunicorn -w N app:app` (module-level `app = create_app()` is the target). |
| 2 | Low | **~50 unrouted stat helpers.** `stats_service.py` defines `get_*_stats`/`get_team_*_stats` for every `STAT_CATEGORIES` id, but only 7 stats routes are wired. The rest are reachable only via the generic `/stats/stat/<id>`. | `backend/services/stats_service.py`, `routes/stats.py` | Route the ones the UI needs, or drop the dead wrappers. |
| 3 | Low | **Hardcoded NCAA base URL.** `NCAA_API_BASE_URL` is a literal constant, inconsistent with the otherwise env-driven config. | `backend/api_vars.py` | Move to config/env if it ever needs to vary; otherwise leave with a comment. |

## Data & ML

| # | Sev | Issue | Where | Suggested fix |
| --- | --- | --- | --- | --- |
| 4 | Med | **`predictions.neutral_site` is never written.** The column exists but isn't in the writer's `PREDICTION_COLUMNS`, so it always reads back as its default `FALSE`, even for real neutral-site games. | `ml/m1/predict_upcoming.py`, `db/schema.sql` | Add `neutral_site` to the writer (CFBD exposes it) or drop the column. |
| 5 | Med | **Games with no NCAA match are silently dropped.** `predict_upcoming.py` skips any CFBD game it can't match to an NCAA game — no row is written, no error. Low-match weeks look "empty." | `ml/m1/predict_upcoming.py` (`match_cfbd_to_ncaa`) | Log/emit a count of unmatched games per run so the loss is visible. |
| 6 | Med | **Two `normalize_team_name` implementations.** The engine's simple regex (`matchup_intel/db.py`) and the large CFBD↔NCAA reconciler (`predict_upcoming.py`) must agree for the `predictions.home_team` → `teams.normalized_name` join to land. | `ml/matchup_intel/db.py`, `ml/m1/predict_upcoming.py` | Consolidate to one shared normalizer, or add a test asserting they agree on the team list. |
| 7 | Low | **Live-DB schema changes need `ALTER … IF NOT EXISTS`.** `CREATE TABLE IF NOT EXISTS` is skipped on an existing volume, so a new column on an existing table only applies via an explicit `ALTER TABLE … ADD COLUMN IF NOT EXISTS`. Easy to forget. | `db/schema.sql` | Keep the pattern; see [Database → schema-change protocol](database.md#schema-change-protocol). |

## Matchup Intelligence Engine

| # | Sev | Issue | Where | Suggested fix |
| --- | --- | --- | --- | --- |
| 8 | Med | **Two point-in-time filters.** `logic.filter_point_in_time` (checks both `as_of_timestamp` and `published_at`, fully tested) is *not* the filter that actually gates serving — `serve.py` uses a simpler inline `Factor.as_of_timestamp ≤ kickoff` because `Factor` has no `published_at`. They can drift. | `ml/matchup_intel/logic.py`, `serve.py` | Carry `published_at` onto `Factor` and route serving through the tested filter, or document the split as intentional. |
| 9 | Low | **Reference panel isn't point-in-time filtered.** `get_model_reference_panel` reads current `predictions` state (not as-of kickoff) — consistent with how that panel has always behaved, but worth knowing when reasoning about leakage. | `ml/matchup_intel/db.py` | Leave as-is (documented), or filter if the panel ever becomes an input rather than context. |
| 10 | Low | **QB factors have no historical grounding yet.** `ground_qb_factor` has no dataset, so `sample_size = 0` always → the sample-size guard withholds any rate. Expected for the current slice. | `ml/matchup_intel/ground.py` | Wire a QB historical store when that slice is built. |

## Frontend

| # | Sev | Issue | Where | Suggested fix |
| --- | --- | --- | --- | --- |
| 11 | Med | **Duplicated stat map.** `STAT_NAME_TO_ID` (frontend) must mirror `STAT_CATEGORIES` (backend) by hand, with slightly different label casing; adding a stat also touches `utils/appData.js` and `utils/mockData.js`. | `frontend/src/services/api.js`, `backend/api_vars.py` | Generate one from the other, or expose the map from an endpoint. |
| 12 | Low | **Dead page: `ScoresPage.jsx`.** Not registered in any route, renders a duplicate `<Header>`, reads `utils/mockData.js` — a pre-API-integration draft superseded by `HomePage`. | `frontend/src/pages/ScoresPage.jsx` | Delete. |
| 13 | Low | **Stale JS design tokens.** `constants/{colors,spacing,css}.js` still hold the old React-blue palette, not the "Electric Night" tokens in `index.css` (which marks them legacy/unused). | `frontend/src/constants/` | Delete the stale JS token files; `index.css` `var(--…)` is the source of truth. |
| 14 | Med | **Stale Render cold-start rationale.** `api.js`'s 90s timeout / 3 retries and `App.jsx`'s "Backend warming up…" health ping date from Render hosting. The backend is now always-on on troyster; the retry wrapper is harmless but the comments mislead. | `frontend/src/services/api.js`, `App.jsx` | Rewrite the comments (keep the retry for real transient blips). |
| 15 | Low | **Untyped 404 handling.** `apiRequest` throws a generic `Error("HTTP error! status: 404")`; `MatchupPage` string-matches `"404"` to route to its empty state. | `frontend/src/services/api.js`, `pages/MatchupPage.jsx` | Introduce a typed error carrying the status code. |

## `backend/env.example` — status

CLAUDE.md §7 notes stale Render references in `backend/env.example`; the infra audit found the
current file no longer contains them. If any remain in a given checkout, clean them up (Vercel
references are **not** stale — that's the live frontend host).
