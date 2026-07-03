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
    stadium_timezone TEXT,                        -- IANA tz of the venue; UTC->local date join for weather_history
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Additive backfill for DBs created before stadium_timezone existed (the live
-- troyster DB already has a teams table, which CREATE ... IF NOT EXISTS skips).
ALTER TABLE teams ADD COLUMN IF NOT EXISTS stadium_timezone TEXT;
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


-- ============================================================================
-- Point-in-time FEATURE STORE (stacked-ensemble ML: training + inference)
-- ----------------------------------------------------------------------------
-- Long/EAV feature store the ensemble models read from. The hard requirement is
-- POINT-IN-TIME correctness (no leakage): a feature carries as_of_timestamp = the
-- instant it BECAME KNOWN, and a game's feature vector may ONLY use rows whose
-- as_of_timestamp <= that game's kickoff. This mirrors the raw_signals/factors
-- discipline above (as_of_timestamp filtered at the serving boundary).
--
-- ENTITY KEYS (soft refs, same scheme as the rest of the schema):
--   * game        -> ncaa_game_id  (== predictions.ncaa_game_id / factors.ncaa_game_id);
--                    game_id is the parallel CFBD id (== predictions.game_id), nullable.
--   * team        -> team_id        (FK teams.team_id; predictions keys teams by TEXT
--                    name, so join predictions.home_team/away_team -> teams.normalized_name
--                    via normalize_team_name(), exactly as the matchup engine does).
--   * team-in-game-> both ncaa_game_id AND team_id set (e.g. a home-team rolling stat
--                    computed for one specific game context).
-- A row must attach to at least one entity (CHECK below).
--
-- KICKOFF for the as-of filter = predictions.game_date (CFBD startDate, TIMESTAMPTZ/UTC).
-- ============================================================================

-- Catalog of every feature the store may hold. feature_name is the stable key the
-- ML side references (mirrors the training_data.csv column names, e.g. 'home_sp_rating',
-- 'matchup_elo_diff', 'betting_over_under', 'away_rolling_win_pct').
-- point_in_time_safe = FALSE flags features that are NOT leakage-safe (e.g. a
-- season-aggregate rating only finalized post-hoc); the reader filters on this.
CREATE TABLE IF NOT EXISTS feature_definitions (
    feature_name        TEXT PRIMARY KEY,           -- stable ML-facing key
    description         TEXT,
    dtype               TEXT NOT NULL DEFAULT 'numeric'
                        CHECK (dtype IN ('numeric','text','boolean','categorical')),
    entity_level        TEXT NOT NULL DEFAULT 'team_game'
                        CHECK (entity_level IN ('game','team','team_game')),
    unit                TEXT,                       -- optional (e.g. 'points','rating','pct')
    source              TEXT,                       -- provenance (e.g. 'cfbd:ratings/sp', 'derived')
    point_in_time_safe  BOOLEAN NOT NULL DEFAULT TRUE,   -- FALSE => may leak; reader must exclude
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The feature values themselves (long/EAV form so new features need no DDL).
-- One row = one (feature, entity, as_of) observation. Numeric OR text value is set
-- (booleans/categoricals stored as 0/1 in value_num or a label in value_text).
CREATE TABLE IF NOT EXISTS feature_values (
    feature_value_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_name      TEXT NOT NULL REFERENCES feature_definitions(feature_name),
    ncaa_game_id      BIGINT,                       -- soft ref -> predictions.ncaa_game_id (nullable)
    game_id           BIGINT,                       -- CFBD id -> predictions.game_id (nullable)
    team_id           UUID REFERENCES teams(team_id),   -- FK teams.team_id (nullable)
    season            INTEGER,                      -- denormalized for training-set slicing
    week              INTEGER,
    value_num         DOUBLE PRECISION,             -- numeric/boolean(0|1) value
    value_text        TEXT,                         -- text/categorical value
    as_of_timestamp   TIMESTAMPTZ NOT NULL,         -- POINT-IN-TIME: when this value became known
    source            TEXT NOT NULL,                -- provenance (e.g. 'cfbd:ratings/sp@2024', 'collect_data')
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (value_num IS NOT NULL OR value_text IS NOT NULL),
    CHECK (ncaa_game_id IS NOT NULL OR team_id IS NOT NULL),
    -- Idempotent upsert key: re-ingesting the same (feature, entity, as_of) UPDATES
    -- rather than duplicates. NULLS NOT DISTINCT (PG15+) so a null team_id/ncaa_game_id
    -- collides as expected for game-only / team-only rows.
    UNIQUE NULLS NOT DISTINCT (feature_name, ncaa_game_id, team_id, as_of_timestamp)
);

-- Indexes tuned for the as-of read: "latest value per (entity, feature_name) with
-- as_of_timestamp <= kickoff". The DESC on as_of_timestamp lets DISTINCT ON take the
-- newest qualifying row per feature without a separate sort.
CREATE INDEX IF NOT EXISTS idx_feature_values_game_asof
    ON feature_values (ncaa_game_id, feature_name, as_of_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_feature_values_team_asof
    ON feature_values (team_id, feature_name, as_of_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_feature_values_season_week
    ON feature_values (season, week);   -- training-set slicing by season/week

-- Reproducible training: a named, versioned set fixes WHICH features a model reads
-- (the column list); a snapshot records HOW a specific training matrix was built
-- (the set + the as-of rule + season span + a content hash), pointing back to
-- feature_values rather than copying them. To reproduce a run, re-issue the as-of
-- query below for feature_names at each game's kickoff over the snapshot's seasons.
CREATE TABLE IF NOT EXISTS feature_sets (
    feature_set_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    description     TEXT,
    feature_names   TEXT[] NOT NULL,               -- ordered feature_definitions.feature_name keys
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (name, version)
);

CREATE TABLE IF NOT EXISTS feature_snapshots (
    snapshot_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature_set_id  UUID REFERENCES feature_sets(feature_set_id),
    name            TEXT,
    as_of_rule      TEXT NOT NULL DEFAULT 'kickoff',   -- 'kickoff' | ISO ts | rule name
    season_from     INTEGER,
    season_to       INTEGER,
    row_count       INTEGER,
    content_hash    TEXT UNIQUE,                   -- idempotent build dedupe
    manifest        JSONB,                         -- {feature_names, params, git_sha, ...}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_feature_snapshots_set ON feature_snapshots (feature_set_id);

-- ----------------------------------------------------------------------------
-- AS-OF READ PATTERN (the ML side MUST use this to avoid leakage)
-- ----------------------------------------------------------------------------
-- For one game, kickoff := predictions.game_date. Pull the newest value known at or
-- before kickoff, per feature. GAME-level features:
--
--   SELECT DISTINCT ON (fv.feature_name)
--          fv.feature_name, fv.value_num, fv.value_text
--   FROM feature_values fv
--   JOIN feature_definitions fd USING (feature_name)
--   WHERE fv.ncaa_game_id = %(ncaa_game_id)s
--     AND fv.as_of_timestamp <= %(kickoff)s     -- point-in-time cutoff
--     AND fd.point_in_time_safe                 -- never serve leaky features
--   ORDER BY fv.feature_name, fv.as_of_timestamp DESC;   -- newest wins
--
-- TEAM-level features (run once per team; map name -> team_id via teams.normalized_name):
--
--   SELECT DISTINCT ON (fv.feature_name)
--          fv.feature_name, fv.value_num, fv.value_text
--   FROM feature_values fv
--   JOIN feature_definitions fd USING (feature_name)
--   WHERE fv.team_id = %(team_id)s
--     AND fv.as_of_timestamp <= %(kickoff)s
--     AND fd.point_in_time_safe
--   ORDER BY fv.feature_name, fv.as_of_timestamp DESC;
--
-- Leakage guardrails: (1) the cutoff is STRICTLY the game's own kickoff, never now();
-- (2) as_of_timestamp is the KNOWN-AT time, so a value stamped after kickoff is
-- invisible to that game; (3) point_in_time_safe=FALSE features are excluded here,
-- so post-hoc season aggregates can be stored for analysis without polluting training.
-- ============================================================================
