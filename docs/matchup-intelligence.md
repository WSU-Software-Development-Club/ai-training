# Matchup Intelligence Engine

Source: [`ml/matchup_intel/`](../ml/matchup_intel/)

The engine builds a per-game, per-team **factor deck**: a ranked list of scored,
**sourced** tailwinds/headwinds (QB status, injuries, weather, rest, travel, …), plus
a **reference panel** (the XGBoost score prediction, Vegas O/U, Polymarket odds). It
**does the fan's homework — it does not make picks.** The LLM and scorers never see or
emit anything about the game outcome.

Two scoring paths produce factors of the **same shape**:

- **Weather** → a pure, deterministic Python scorer (`score/weather.py:score_weather`) mapping conditions to a bucket/direction/magnitude/confidence via a fixed severity rubric. **No LLM.**
- **QB / injury / news** → the LLM path (`extract.py`): build a prompt, call a self-hosted **Ollama `gemma3`** model, then strictly validate the JSON response.

Both converge on the `Factor` model and the same grounding → serving pipeline.

## The layered pipeline

Layers are labeled 0–6 in the code. End to end:

| Layer | Stage | Where | What happens |
| --- | --- | --- | --- |
| 0 | **Ingest** | `ingest/*.py`, `sources/*.py` → `raw_signals` | Source-agnostic landing zone. `db.insert_raw_signal` writes a `payload` JSONB row carrying `published_at` (source truth) + `as_of_timestamp` (observed truth). Idempotent on `content_hash`. |
| 1 | **Extract** (LLM) | `extract.py` | `build_prompt` → `call_ollama` (gemma3) → `parse_llm_factor` → a `Factor` with `scoring_method="llm"`. Weather **skips** this layer. |
| 2 | **Score** (weather) | `score/weather.py` | `score_weather` deterministically buckets forecast/observed conditions. Called directly by `flows._weather_factor`. |
| 4 | **Ground** | `ground.py` | `ground_factor` dispatches by category via `_GROUNDERS`: `ground_weather_factor` queries `db.get_weather_history_rate` for the team's real win-rate in that weather bucket (bumps `scoring_method="hybrid"`); `ground_qb_factor` has no historical dataset yet (`sample_size=0`). Unknown categories → honest null. |
| 5 | **Assemble / serve** | `serve.py`, `logic.py` → `factor_decks` | `build_and_store_decks` reads persisted factors, applies point-in-time filtering, groups by team, calls `assemble_deck` (dedupe → rank → guard-render), persists via `upsert_factor_deck`. |
| 6 | **Reference panel** | `db.get_model_reference_panel` | Attaches `{model, vegas, polymarket}` alongside (not instead of) the deck. |

Orchestration across all stages lives in [`flows.py`](#orchestration-flowspy).

## The three hard guarantees (`logic.py`)

All three are pure, side-effect-free, and unit-tested in isolation.

1. **Point-in-time correctness** — `filter_point_in_time(signals, kickoff)`: a signal is
   visible only if **both** `as_of_timestamp ≤ kickoff` **and** `(published_at or
   as_of_timestamp) ≤ kickoff`. News published after kickoff is invisible at that game's
   evaluation time.
   > **Two filters exist.** `filter_point_in_time` (operates on `RawSignalRef`, also
   > checks `published_at`) is the fully-tested rule. The actual serving-time gate in
   > `serve.py` is a simpler inline `Factor.as_of_timestamp ≤ kickoff` (a `Factor` has no
   > `published_at` field). `get_model_reference_panel` is **not** point-in-time filtered —
   > it reads current `predictions` state, consistent with how that panel has always behaved.

2. **Sample-size guard** — `apply_sample_size_guard(factor, threshold)`: if
   `sample_size < threshold` (default **30**, `config.sample_size_threshold`) or
   `historical_rate is None`, the headline `historical_rate` is forced to `None` and
   `historical_rate_withheld: true` is set. **Serving is built only from this function's
   output**, so a sub-threshold rate physically cannot reach the frontend. The `grounding`
   block (wins/total/baseline) is still emitted so a dense surface can show the raw record,
   marked thin.

3. **Ranking** — `rank_factors` sorts by `Factor.score` (`= magnitude × confidence`)
   descending (stable). `dedupe_factors` keeps one factor per `(team_id, category)`,
   preferring higher score. `assemble_deck` composes all three per team.

## Schemas / validation boundary (`schemas.py`)

`schemas.py` is the validation boundary — every LLM output is parsed through
`LLMFactorOutput` (`extra="forbid"`, hard `[0,1]` bounds); anything non-conforming is
dropped (`parse_llm_factor` returns `None`, never raises).

- `Direction = "tailwind" | "headwind" | "neutral"`
- `ScoringMethod = "historical" | "model" | "llm" | "hybrid"`
- `KNOWN_CATEGORIES = (QB, OL, DL, rest, travel, coaching, momentum, weather, special_teams)` — a tuple (open set), extendable via data/config without a code change. (The DB `factors.category` column has no CHECK enumerating them.)
- `Source` (`extra="forbid"`): `url?`, `source_type` (required), `snippet?`, `published_at?`.
- `Factor`: the persistable model — `ncaa_game_id`, `team_id: UUID`, `category`, `direction`, bounded `magnitude`/`confidence`, `explanation`, `scoring_method`, optional `historical_rate`, `sample_size`, `sources`, `derived_from_raw_ids`, `grounding: dict?`, `as_of_timestamp`; `.score = magnitude × confidence`.

## Data sources (`sources/`)

| Module | Auth | What it fetches |
| --- | --- | --- |
| `cfbd.py` | `CFBD_API_KEY` (Bearer) | FBS teams + nested venue (lat/lon, IANA tz). `fetch_fbs_teams`, `team_venue`. **Fails loud** — the teams dimension is a required foundation. |
| `open_meteo.py` | none (free) | `archive_daily` (past weather, grounding backfill), `forecast_daily` (16-day upcoming), `daily_to_conditions` (adapts to the scorer's shape). |
| `polymarket.py` | none | Gamma `search_markets` (discovery) + CLOB `clob_midpoint` (live price). `find_game_market`/`fetch_game_odds` never raise — CFB market coverage is sparse by design; a miss is `None`, not an error. |

**Id spaces.** The join key everywhere in the engine is **`ncaa_game_id`** (NCAA API).
CFBD's own `game_id` and `cfbd_id` (team id) are the parallel, nullable ids — never the
cross-table key. (There is no ESPN id space in this module.) Team names bridge to
`teams.team_id` via `normalized_name` — see [Database → id spaces](database.md#the-id-spaces).

## Ingest entrypoints (`ingest/`)

| Module | Populates |
| --- | --- |
| `teams_backfill.py` | The `teams` dimension from CFBD (name, cfbd_id, conference, venue, coords, tz). **Prerequisite for weather.** |
| `weather_backfill.py` | Real `weather_history` rows by joining historical game results (`training_data.csv`) with Open-Meteo archive weather per stadium. |
| `game_weather.py` | Observed archive weather per real game → a `weather` raw_signal, then re-runs extract/ground/serve for real weather decks. |
| `seed_weather.py` | Two demo forecast signals (WSU cold, OSU rain) for offseason/demo. |
| `seed.py` | Bundled demo games from `seed_data.json` into `raw_signals` (idempotent). |
| `polymarket_ingest.py` | One game's Polymarket snapshot as a `raw_signal` (writes nothing when no market found). |

## Config (`config.py`)

`load_config()` precedence: **env vars > `config.yaml` > built-in defaults** (loads `.env`
via `python-dotenv`). Frozen `Config` dataclass:

| Field | Default | Notes |
| --- | --- | --- |
| `database_url`, `cfbd_api_key` | — | **env-only** (secrets, never from yaml) |
| `ollama_url` | `http://ollama:11434` | |
| `ollama_model` | `gemma3` | |
| `sample_size_threshold` | **30** | the guard threshold |
| `request_timeout` | 180s | generous, tolerates a cold gemma3 load |
| `polymarket_enabled` | `True` | ops kill-switch |

## Orchestration (`flows.py`)

A Prefect DAG whose `@flow`/`@task` decorators **degrade to plain functions** if Prefect
isn't installed, so it always runs via `python -m ml.matchup_intel.flows`. Stages:
`ingest_stage` → `extract_and_ground_stage` (per-game idempotent reset, routes
`source_type == "weather"` to the scorer, everything else through the LLM → ground →
`insert_factor`, always logging an `llm_calls` audit row even on drop) → `serve_stage`.
`run_pipeline()` raises if `DATABASE_URL` is unset.

## Serving contract

`factor_decks.factors` is a JSONB array; each element is exactly the guard-rendered view
object from `apply_sample_size_guard`:

```jsonc
{
  "team_id": "uuid", "category": "weather",
  "direction": "tailwind|headwind|neutral",
  "magnitude": 0.44, "confidence": 0.7, "score": 0.31,
  "explanation": "…", "scoring_method": "historical|model|llm|hybrid",
  "historical_rate": 0.85,          // null when guard withholds
  "sample_size": 39,
  "historical_rate_withheld": false, // true when sample_size < threshold
  "grounding": { "condition_bucket": "heat", "wins": 33, "total": 39,
                 "baseline": 0.72, "conditions": {...}, "is_forecast": true }, // present even when rate withheld
  "sources": [ { "url", "source_type", "snippet", "published_at" } ],
  "raw_signal": "…"
}
```

The row also carries `reference_panels` = `{model, vegas: {over_under}, polymarket}`,
keyed on `(ncaa_game_id, team_id, as_of_timestamp)`. The backend reads it via
`get_factor_deck_by_game`; see [Backend API → `/matchup`](backend-api.md#matchup--matchup).

## How the UI renders it

`frontend/src/pages/MatchupPage.jsx` (`/matchup/:gameId`):
- **`WeatherRow`** — one shared weather band above the columns; each side shows the team's
  historical rate deviation vs. baseline, record, always-on `n=`, a **thin** flag when
  withheld or `n < 30`, and the market line inline.
- **`TeamFactorDeck`** per team — betting posture + factors split into *Working for them*
  (tailwinds) / *Working against them* (headwinds). Weather is excluded here (shown once in
  the WeatherRow); each remaining factor renders as an expandable **`FactorCard`** (category
  + direction badge, magnitude meter, and on expand the sources with relative publish times).
- **`ReferencePanels`** — model / Vegas / Polymarket, framed explicitly as inputs, not the verdict.

## Tests (`ml/matchup_intel/tests/`)

| Test | Protects |
| --- | --- |
| `test_point_in_time.py` | `filter_point_in_time` (before/after/at kickoff, `published_at` fallback) |
| `test_sample_size_guard.py` | `apply_sample_size_guard` / `assemble_deck` (threshold behavior, withheld rates) |
| `test_pydantic_validation.py` | the `LLMFactorOutput` boundary (`extra="forbid"`, bounds, empty explanation) |
| `test_extract.py` | extract → validate → Factor path (invalid/unreachable responses dropped, never crash) |
| `test_weather_scoring.py` | `score_weather` (bucketing, monotonic magnitude, bounds) |
| `test_weather_backfill.py` | local-date/timezone rollback joining UTC kickoffs to stadium-local weather |
| `test_game_weather.py` | observed-weather payload builder |
| `test_polymarket.py` | the Polymarket client (matching, CLOB/Gamma fallback, graceful degradation) |

Run: `cd ml && pytest matchup_intel/tests`.

## Local data (for UI work)

The engine reads from Postgres, so a matchup page is empty until a deck exists. To populate
the local dev DB:

- **Real 2025 grounding** (prod path): run the ingest entrypoints in order —
  `teams_backfill` → `weather_backfill` → `game_weather` — with `DATABASE_URL` and
  `CFBD_API_KEY` set and `PYTHONPATH` at the repo root. This is exactly what the
  `matchup_backfill.yml` workflow does against prod. See [Deployment → CI/CD](deployment.md#cicd).
- **Mock upcoming-season decks** (design iteration): temporary generator scripts seed
  significance-gated weather factors and team-specific (injury/QB/rest/travel/momentum/
  coaching/news) factors with sourced, point-in-time timestamps so both the WeatherRow and
  the per-team columns populate. A matchup is then reachable at
  `http://localhost:3000/matchup/<ncaa_game_id>` even when the live NCAA scoreboard feed has
  no games for that season (the Home list is API-driven, so mock games are URL-reachable but
  not listed).
