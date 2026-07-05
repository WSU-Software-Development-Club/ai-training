"""
Postgres client for the predictions database (self-hosted on troyster).

Replaces the previous Supabase client. Keeps the same method interface
(get_predictions, get_predictions_by_week, get_prediction_by_ncaa_game_id,
is_connected, ...) so callers (routes/services) need no logic changes.

Connection is configured via the DATABASE_URL env var, e.g.
    postgresql://aitraining:PASSWORD@db:5432/aitraining      (backend on the compose network)
If DATABASE_URL is unset or the DB is unreachable, methods degrade gracefully
(return [] / None) exactly as the old Supabase client did.
"""

import os
from typing import Optional, List, Dict, Any

try:
    from psycopg_pool import ConnectionPool
    from psycopg.rows import dict_row
    PSYCOPG_AVAILABLE = True
except ImportError:
    PSYCOPG_AVAILABLE = False
    print("Warning: psycopg not installed. Install with: pip install 'psycopg[binary,pool]'")


class PredictionsDB:
    """Wrapper around a Postgres connection pool for prediction reads."""

    def __init__(self):
        self._pool = None

        if not PSYCOPG_AVAILABLE:
            return

        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            print("Warning: DATABASE_URL not set in environment")
            return

        try:
            self._pool = ConnectionPool(
                dsn,
                min_size=1,
                max_size=5,
                kwargs={"row_factory": dict_row},
                open=True,
            )
        except Exception as e:
            print(f"Error initializing Postgres pool: {e}")
            self._pool = None

    @property
    def is_connected(self) -> bool:
        """Check the DB is reachable (mirrors the old client's is_connected)."""
        if self._pool is None:
            return False
        try:
            with self._pool.connection() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            print(f"Postgres connection check failed: {e}")
            return False

    def _query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Run a SELECT and return a list of dict rows; [] on any failure."""
        if self._pool is None:
            return []
        try:
            with self._pool.connection() as conn:
                cur = conn.execute(sql, params)
                return cur.fetchall()
        except Exception as e:
            print(f"Query error: {e}")
            return []

    def get_predictions(self,
                        limit: int = 100,
                        season: Optional[int] = None,
                        week: Optional[int] = None,
                        team: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get predictions with optional season/week/team filters."""
        clauses, params = [], []
        if season is not None:
            clauses.append("season = %s")
            params.append(season)
        if week is not None:
            clauses.append("week = %s")
            params.append(week)
        if team is not None:
            clauses.append("(home_team = %s OR away_team = %s)")
            params.extend([team, team])

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        return self._query(
            f"SELECT * FROM predictions {where} ORDER BY game_date ASC LIMIT %s",
            tuple(params),
        )

    def get_prediction_by_game_id(self, game_id: int) -> Optional[Dict[str, Any]]:
        """Most recent prediction for a CFBD game id."""
        rows = self._query(
            "SELECT * FROM predictions WHERE game_id = %s "
            "ORDER BY prediction_made_at DESC LIMIT 1",
            (game_id,),
        )
        return rows[0] if rows else None

    def get_predictions_by_week(self, season: int, week: int) -> List[Dict[str, Any]]:
        """All predictions for a given season + week."""
        return self._query(
            "SELECT * FROM predictions WHERE season = %s AND week = %s "
            "ORDER BY game_date ASC",
            (season, week),
        )

    def get_prediction_by_ncaa_game_id(self, ncaa_game_id: int, season: Optional[int] = None,
                                        week: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Lookup by NCAA game id alone.

        `ncaa_game_id` is UNIQUE (db/schema.sql), so this is a precise match on
        its own — no season/week predicate needed (and requiring one is
        actively wrong, since the ML writer's week numbering (CFBD week, with
        postseason stored as cfbd_week+15) doesn't match the NCAA scoreboard's
        display week (e.g. NCAA folds "Week 0" into "week 01")). `season` and
        `week` are accepted-but-ignored for backward compatibility with
        existing callers.
        """
        rows = self._query(
            "SELECT * FROM predictions WHERE ncaa_game_id = %s LIMIT 1",
            (ncaa_game_id,),
        )
        return rows[0] if rows else None

    def get_predictions_by_team(self, team_name: str, season: Optional[int] = None) -> List[Dict[str, Any]]:
        """All predictions involving a team, optionally filtered by season."""
        clauses = ["(home_team = %s OR away_team = %s)"]
        params: List[Any] = [team_name, team_name]
        if season is not None:
            clauses.append("season = %s")
            params.append(season)
        return self._query(
            f"SELECT * FROM predictions WHERE {' AND '.join(clauses)} "
            "ORDER BY game_date ASC",
            tuple(params),
        )

    def get_latest_predictions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Most recently created predictions."""
        return self._query(
            "SELECT * FROM predictions ORDER BY created_at DESC LIMIT %s",
            (limit,),
        )

    def get_factor_deck_by_game(self, ncaa_game_id: int) -> List[Dict[str, Any]]:
        """Serving read for the Matchup Intelligence Engine: both teams' factor
        decks for a game (guard already applied at write time), newest first,
        joined to team names. [] if none / DB unreachable (graceful degrade)."""
        return self._query(
            """
            SELECT fd.team_id, t.name AS team_name, t.normalized_name,
                   fd.factors, fd.reference_panels, fd.as_of_timestamp
            FROM factor_decks fd
            JOIN teams t ON t.team_id = fd.team_id
            WHERE fd.ncaa_game_id = %s
            ORDER BY fd.as_of_timestamp DESC
            """,
            (ncaa_game_id,),
        )

    def get_polymarket_history(self, ncaa_game_id: int) -> List[Dict[str, Any]]:
        """Full Polymarket implied-win-probability time series for a game.

        Each pipeline run persists its own (non-deduped) snapshot to
        raw_signals, so ordering by as_of_timestamp ascending yields the market
        history that `get_latest_polymarket_odds` only reports the tail of.
        Returns rows shaped {as_of, home_win_prob, away_win_prob, question,
        source_url}; [] if no market/DB unreachable (graceful degrade)."""
        rows = self._query(
            """
            SELECT as_of_timestamp,
                   (payload->>'home_win_prob')::float8 AS home_win_prob,
                   (payload->>'away_win_prob')::float8 AS away_win_prob,
                   payload->>'question'   AS question,
                   payload->>'source_url' AS source_url
            FROM raw_signals
            WHERE source_type = 'polymarket' AND ncaa_game_id = %s
            ORDER BY as_of_timestamp ASC
            """,
            (ncaa_game_id,),
        )
        return [
            {
                "as_of": r["as_of_timestamp"].isoformat() if r.get("as_of_timestamp") else None,
                "home_win_prob": r.get("home_win_prob"),
                "away_win_prob": r.get("away_win_prob"),
                "question": r.get("question"),
                "source_url": r.get("source_url"),
            }
            for r in rows
        ]


# Global instance (mirrors the old module-level supabase_client)
predictions_db = PredictionsDB()


def get_db() -> PredictionsDB:
    """Get the global PredictionsDB instance."""
    return predictions_db
