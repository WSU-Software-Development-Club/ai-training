-- ai-training predictions schema (self-hosted Postgres on troyster)
-- Mounted into the postgres container's /docker-entrypoint-initdb.d/ so it runs
-- automatically on first init of an empty data volume. Also safe to run by hand:
--   psql "$DATABASE_URL" -f db/schema.sql
-- Idempotent: uses IF NOT EXISTS throughout.

CREATE TABLE IF NOT EXISTS predictions (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id              BIGINT,                       -- CFBD game id
    ncaa_game_id         BIGINT UNIQUE,                -- NCAA game id (upsert conflict key)
    season               INTEGER,
    week                 INTEGER,
    game_date            TIMESTAMPTZ,                  -- CFBD startDate (ISO 8601)
    home_team            TEXT,
    away_team            TEXT,
    neutral_site         BOOLEAN DEFAULT FALSE,
    predicted_home_score DOUBLE PRECISION,
    predicted_away_score DOUBLE PRECISION,
    predicted_winner     TEXT,
    predicted_margin     DOUBLE PRECISION,
    predicted_total      DOUBLE PRECISION,
    betting_over_under   DOUBLE PRECISION,
    over_probability     DOUBLE PRECISION,
    under_probability    DOUBLE PRECISION,
    prediction_made_at   TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for the query patterns in backend/utils/db.py
CREATE INDEX IF NOT EXISTS idx_predictions_season_week ON predictions (season, week);
CREATE INDEX IF NOT EXISTS idx_predictions_home_team   ON predictions (home_team);
CREATE INDEX IF NOT EXISTS idx_predictions_away_team   ON predictions (away_team);
CREATE INDEX IF NOT EXISTS idx_predictions_game_id     ON predictions (game_id);
-- ncaa_game_id already has a unique index from the UNIQUE constraint above.


-- ============================================================================
-- Matchup Intelligence Engine (ml/matchup_intel/)
-- ----------------------------------------------------------------------------
-- A per-game "factor deck": every factor that matters for a matchup, scored as
-- a tailwind/headwind with a plain-language why and provenance. NOT a predictor.
-- Two rules are enforced structurally, not by convention:
--   1. Sample-size guard: historical_rate is only served when sample_size meets
--      a configurable threshold (applied in serve.py at the serving boundary).
--   2. Point-in-time: everything carries as_of_timestamp; a game's deck only
--      ever sees signals with as_of_timestamp <= kickoff.
-- Additive + idempotent; apply to live troyster with `psql "$DATABASE_URL" -f db/schema.sql`.
-- ============================================================================

-- Teams dimension. New identity scheme for the engine (the predictions table
-- still keys teams by TEXT name; join via normalized_name). Stadium coords are
-- pre-positioned here for the weather factor (slice #2).
CREATE TABLE IF NOT EXISTS teams (
    team_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cfbd_id          BIGINT UNIQUE,               -- CFBD team id, when known
    name             TEXT NOT NULL,               -- display name
    normalized_name  TEXT NOT NULL UNIQUE,        -- lowercased key; matches predictions team names
    conference       TEXT,
    venue_name       TEXT,
    stadium_lat      DOUBLE PRECISION,            -- weather factor
    stadium_lon      DOUBLE PRECISION,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_teams_normalized_name ON teams (normalized_name);

-- Layer 0 raw landing. Source-agnostic: source_type + JSONB payload absorb news,
-- injuries, depth charts, weather, lines, polymarket, etc. published_at is the
-- SOURCE's timestamp (point-in-time truth); as_of_timestamp is when WE observed it.
CREATE TABLE IF NOT EXISTS raw_signals (
    raw_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type      TEXT NOT NULL,               -- news | injury_report | depth_chart | weather | line | polymarket
    source_name      TEXT,
    source_url       TEXT,
    team_id          UUID REFERENCES teams(team_id),   -- best-effort tag, nullable
    ncaa_game_id     BIGINT,                      -- best-effort tag, nullable
    payload          JSONB NOT NULL,              -- raw text / structured blob (+ any supporting context)
    content_hash     TEXT UNIQUE,                 -- idempotent ingest / dedupe
    published_at     TIMESTAMPTZ,                 -- POINT-IN-TIME truth (source publish time)
    as_of_timestamp  TIMESTAMPTZ NOT NULL,        -- when we ingested/observed it
    fetched_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_raw_signals_game ON raw_signals (ncaa_game_id);
CREATE INDEX IF NOT EXISTS idx_raw_signals_asof ON raw_signals (as_of_timestamp);

-- Per-extractor watermark for idempotent, resumable ingestion.
CREATE TABLE IF NOT EXISTS ingest_watermarks (
    extractor    TEXT PRIMARY KEY,
    last_run_at  TIMESTAMPTZ,
    last_cursor  TEXT,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The atomic unit. Full lineage retained (derived_from_raw_ids, grounding) so
-- every factor is auditable back to its raw signal and historical join.
CREATE TABLE IF NOT EXISTS factors (
    factor_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ncaa_game_id         BIGINT NOT NULL,         -- soft ref -> predictions.ncaa_game_id
    game_id              BIGINT,                  -- CFBD id, nullable
    season               INTEGER,
    week                 INTEGER,
    team_id              UUID NOT NULL REFERENCES teams(team_id),
    category             TEXT NOT NULL,           -- QB | OL | DL | rest | travel | coaching | momentum | weather | special_teams
    raw_signal           TEXT,
    direction            TEXT NOT NULL CHECK (direction IN ('tailwind','headwind','neutral')),
    magnitude            DOUBLE PRECISION NOT NULL CHECK (magnitude BETWEEN 0 AND 1),
    confidence           DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    explanation          TEXT NOT NULL,
    scoring_method       TEXT NOT NULL CHECK (scoring_method IN ('historical','model','llm','hybrid')),
    historical_rate      DOUBLE PRECISION,        -- nullable; guard-gated at serving
    sample_size          INTEGER NOT NULL DEFAULT 0,
    sources              JSONB NOT NULL DEFAULT '[]'::jsonb,   -- [{url, published_at, snippet, source_type}]
    derived_from_raw_ids UUID[] NOT NULL DEFAULT '{}',         -- raw_signal -> factor lineage
    grounding            JSONB,                   -- the historical query + params used
    as_of_timestamp      TIMESTAMPTZ NOT NULL,    -- factor known as of this instant
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_factors_game     ON factors (ncaa_game_id);
CREATE INDEX IF NOT EXISTS idx_factors_team_cat ON factors (team_id, category);
CREATE INDEX IF NOT EXISTS idx_factors_asof     ON factors (as_of_timestamp);

-- Full LLM audit trail: the exact prompt + raw model response for every
-- extraction call, INCLUDING ones whose output was invalid and dropped
-- (factor_id NULL, valid=false). Completes the raw_signal -> factor lineage.
CREATE TABLE IF NOT EXISTS llm_calls (
    call_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    raw_id      UUID REFERENCES raw_signals(raw_id),
    factor_id   UUID REFERENCES factors(factor_id) ON DELETE CASCADE,  -- NULL if dropped
    model       TEXT,
    prompt      TEXT NOT NULL,
    response    TEXT,                         -- raw model text (NULL on transport failure)
    valid       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_llm_calls_raw    ON llm_calls (raw_id);
CREATE INDEX IF NOT EXISTS idx_llm_calls_factor ON llm_calls (factor_id);

-- Historical grounding store for the WEATHER factor: a team's past results in a
-- given weather bucket. The grounder aggregates win-rate + sample_size from here;
-- the sample-size guard then decides whether the rate is served. (Seeded now;
-- later backfilled from CFBD results x Open-Meteo archive by stadium coords.)
CREATE TABLE IF NOT EXISTS weather_history (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id          UUID NOT NULL REFERENCES teams(team_id),
    condition_bucket TEXT NOT NULL,          -- cold | wind | rain | heat | clear
    season           INTEGER,
    won              BOOLEAN NOT NULL,
    source           TEXT,                   -- provenance (e.g. 'seed', 'cfbd+open-meteo')
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_weather_history_team_bucket
    ON weather_history (team_id, condition_bucket);

-- Layer 5 serving. The sample-size guard is applied when writing this table, so
-- serving physically cannot emit a sub-threshold historical_rate.
CREATE TABLE IF NOT EXISTS factor_decks (
    deck_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ncaa_game_id     BIGINT NOT NULL,
    team_id          UUID NOT NULL REFERENCES teams(team_id),
    factors          JSONB NOT NULL,              -- ranked, guard-applied factor view objects
    reference_panels JSONB,                       -- {model, vegas, polymarket} (Layer 6)
    as_of_timestamp  TIMESTAMPTZ NOT NULL,
    assembled_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (ncaa_game_id, team_id, as_of_timestamp)
);
CREATE INDEX IF NOT EXISTS idx_factor_decks_game ON factor_decks (ncaa_game_id);
