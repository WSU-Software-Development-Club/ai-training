# Database

Postgres 16, self-hosted on troyster (`db` compose service, `pgdata` volume). The schema
is the source of truth in [`db/schema.sql`](../db/schema.sql). All tables use
`IF NOT EXISTS`; UUID PKs default `gen_random_uuid()`; timestamps are `TIMESTAMPTZ`
defaulting `now()`.

## Tables at a glance

| Table | Purpose | Written by | Read by |
| --- | --- | --- | --- |
| `predictions` | Weekly ML game-score predictions (the core API-served table) | `ml/m1/predict_upcoming.py` (upsert) | `backend/utils/db.py`, matchup reference panel |
| `teams` | Teams dimension for the Matchup Intelligence Engine | `matchup_intel/db.py:upsert_team` | engine + backend deck join |
| `raw_signals` | Layer 0 source-agnostic landing zone | `matchup_intel` ingest | extract/serve |
| `factors` | Atomic scored matchup unit, with lineage | `insert_factor` | `fetch_factors_for_game` → serve |
| `llm_calls` | LLM extraction audit trail | `insert_llm_call` | (audit) |
| `weather_history` | Historical grounding store for the weather factor | `insert_weather_history_bulk` | `get_weather_history_rate` |
| `factor_decks` | Layer 5 serving table (guard already applied) | `upsert_factor_deck` | `backend/utils/db.py:get_factor_deck_by_game` |
| `ingest_watermarks` | Per-extractor resumable cursor | `set_watermark` | `get_watermark` |
| `feature_definitions`/`feature_values`/`feature_sets`/`feature_snapshots` | Point-in-time feature store (forward-looking, schema-only today) | — | — |

## Core tables

### `predictions`
The API's core table. Keyed on **`ncaa_game_id BIGINT UNIQUE`** (the upsert conflict key).

Columns: `id` (UUID PK), `game_id` (CFBD id, indexed), `ncaa_game_id` (UNIQUE),
`season`/`week` (composite index; `week` stores CFBD week, postseason as NCAA 16+ or
cfbd_week+15), `game_date` (TIMESTAMPTZ — also the "kickoff" as-of reference), `home_team`/
`away_team` (TEXT, each indexed), `neutral_site` (BOOLEAN DEFAULT FALSE — **never set by the
writer**, always reads FALSE), `predicted_home_score`/`predicted_away_score`/
`predicted_margin`/`predicted_total`/`betting_over_under`/`over_probability`/
`under_probability` (DOUBLE PRECISION), `predicted_winner` (TEXT), `prediction_made_at`,
`created_at` (DB default).

Indexes: `(season,week)`, `home_team`, `away_team`, `game_id`; unique index on
`ncaa_game_id`.

### `teams`
Dimension for the engine. `team_id` (UUID PK), `cfbd_id` (BIGINT UNIQUE), `name` (TEXT),
**`normalized_name` (TEXT UNIQUE)** — the join bridge to `predictions.home_team`/`away_team`,
`conference`, `venue_name`, `stadium_lat`/`stadium_lon` (weather coords), `stadium_timezone`
(IANA tz, added via `ALTER TABLE … ADD COLUMN IF NOT EXISTS`), timestamps. Index on
`normalized_name`.

### `raw_signals`
Layer 0. `raw_id` (UUID PK), `source_type` (news|injury_report|depth_chart|weather|line|
polymarket), `source_name`/`source_url`, `team_id` (FK, nullable), `ncaa_game_id` (nullable
soft ref, indexed), `payload` (JSONB), **`content_hash` (UNIQUE — idempotent ingest)**,
`published_at` (point-in-time truth), `as_of_timestamp` (observed, indexed), `fetched_at`.

### `factors`
The atomic scored unit with full lineage. `factor_id` (UUID PK), `ncaa_game_id` (indexed),
`game_id`/`season`/`week`, `team_id` (FK), `category`, `raw_signal`,
`direction` (**CHECK** tailwind|headwind|neutral), `magnitude`/`confidence` (**CHECK** 0..1),
`explanation`, `scoring_method` (**CHECK** historical|model|llm|hybrid), `historical_rate`
(nullable, guard-gated at serving), `sample_size` (DEFAULT 0), `sources` (JSONB DEFAULT
`[]`), `derived_from_raw_ids` (UUID[] — raw→factor lineage), `grounding` (JSONB),
`as_of_timestamp` (indexed). Indexes: `(ncaa_game_id)`, `(team_id, category)`,
`(as_of_timestamp)`.

### `llm_calls`
Full audit trail. `call_id` (UUID PK), `raw_id` (FK, indexed), `factor_id` (FK
`ON DELETE CASCADE`, NULL if the output was dropped), `model`, `prompt`, `response` (NULL on
transport failure), `valid` (BOOLEAN DEFAULT FALSE).

### `weather_history`
Grounding store. `id` (UUID PK), `team_id` (FK), `condition_bucket` (cold|wind|rain|heat|
clear), `season`, `won` (BOOLEAN), `source` (provenance). Index on
`(team_id, condition_bucket)`. Read as a wins/total aggregate by `get_weather_history_rate`.

### `factor_decks`
Layer 5 serving table (the guard is applied at **write** time). `deck_id` (UUID PK),
`ncaa_game_id` (indexed), `team_id` (FK), `factors` (JSONB — ranked, guard-applied view
objects), `reference_panels` (JSONB — `{model, vegas, polymarket}`), `as_of_timestamp`,
`assembled_at`. **`UNIQUE (ncaa_game_id, team_id, as_of_timestamp)`** is the upsert key.

### Feature store (forward-looking)
`feature_definitions` (catalog; `point_in_time_safe` flag — FALSE ⇒ leaky, reader must
exclude), `feature_values` (long/EAV observations with `as_of_timestamp`; idempotent upsert
via `UNIQUE NULLS NOT DISTINCT (feature_name, ncaa_game_id, team_id, as_of_timestamp)`),
`feature_sets` (named/versioned column lists), `feature_snapshots` (reproducible
training-matrix manifests). The canonical as-of read (`DISTINCT ON (feature_name) … WHERE
as_of_timestamp ≤ kickoff AND point_in_time_safe`) is documented inline in `schema.sql`. **No
in-repo code path writes or reads these tables yet** — schema-only.

## The id spaces

| Id | Type | Role |
| --- | --- | --- |
| **`ncaa_game_id`** | BIGINT | The cross-table join key (NCAA API). Used by `predictions` (UNIQUE), `factors`, `raw_signals`, `factor_decks`, `feature_values`. |
| `game_id` / `cfbd_id` | BIGINT | CFBD game id / CFBD team id (UNIQUE). Always the parallel/nullable id, never the join key. |
| `teams.team_id` | UUID | FK target for all engine tables. **`predictions` does not use it** — it keys teams by TEXT name. |

**Name → UUID bridge:** `predictions.home_team`/`away_team` (TEXT) join to
`teams.normalized_name`. Two `normalize_team_name` implementations must agree: the engine's
simple `re.sub(r"[^a-z0-9]+", " ", name.lower()).strip()` (`matchup_intel/db.py`), and the
much larger CFBD↔NCAA reconciler with an abbreviation dict in `ml/m1/predict_upcoming.py`
(which produces the names stored in `predictions`).

## `factor_decks.factors` JSONB shape

See the [serving contract in the Matchup Intelligence doc](matchup-intelligence.md#serving-contract)
— it's the guard-rendered view object array produced by `apply_sample_size_guard`, already
deduped and ranked. The sample-size guard is the structural choke point: because serving is
built only from that function's output, a sub-threshold `historical_rate` is nulled + flagged
and physically cannot reach the frontend.

## Schema-change protocol

Three files move together for any column add/rename/type change:

1. **`db/schema.sql`** — the DDL (source of truth).
2. **Writer** — `ml/m1/predict_upcoming.py` (`PREDICTION_COLUMNS`) for `predictions`;
   `ml/matchup_intel/db.py` INSERT/upsert functions for the engine tables.
3. **Reader** — `backend/utils/db.py` (`PredictionsDB`, `get_factor_deck_by_game`). Readers
   largely use `SELECT *`, so a **column addition** surfaces automatically; a **rename/type
   change** must be mirrored.

**Idempotency pattern.** `CREATE TABLE IF NOT EXISTS` is skipped on the live DB (tables
already exist), so a **new column on an existing table must use**
`ALTER TABLE <t> ADD COLUMN IF NOT EXISTS <col> <type>;` (as done for
`teams.stadium_timezone`) or it will never apply. Apply to a live DB with
`psql "$DATABASE_URL" -f db/schema.sql` (the whole file is safe to re-run) — over
Tailscale/LAN, **never** through the Cloudflare tunnel.

## Auto-init, volume, silent degrade

- **Auto-init:** `db/schema.sql` is mounted into `/docker-entrypoint-initdb.d/` and runs
  **only on first init of an empty data volume** — not on an existing volume (hence the
  `ALTER … IF NOT EXISTS` lines and manual `psql -f` for live changes).
- **`pgdata` volume:** holds all predictions + engine data. `docker compose down -v` (or any
  drop of `pgdata`) **destroys everything** — call it data loss before proposing it.
- **Silent degrade (reader):** if `psycopg` is missing, `DATABASE_URL` is unset, or the pool
  can't open, `backend/utils/db.py` logs a warning and every read returns `[]`/`None`. A "no
  data" UI usually means a DB/config problem, not an empty table. The **writer**
  (`save_to_postgres`) degrades differently — on any exception it dumps predictions to a
  local timestamped JSON file and returns `False`.
