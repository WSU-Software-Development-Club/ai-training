-- ai-training predictions schema (self-hosted Postgres on troyster)
-- Mounted into the postgres container's /docker-entrypoint-initdb.d/ so it runs
-- automatically on first init of an empty data volume. Also safe to run by hand:
--   psql "$DATABASE_URL" -f db/schema.sql
-- Idempotent: uses IF NOT EXISTS throughout.

CREATE TABLE IF NOT EXISTS predictions (
    id                   BIGSERIAL PRIMARY KEY,
    game_id              BIGINT,                       -- CFBD game id
    ncaa_game_id         BIGINT UNIQUE,                -- NCAA game id (upsert conflict key)
    season               INTEGER,
    week                 INTEGER,
    game_date            TIMESTAMPTZ,                  -- CFBD startDate (ISO 8601)
    home_team            TEXT,
    away_team            TEXT,
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
