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

    def get_prediction_by_ncaa_game_id(self, ncaa_game_id: int, season: int, week: int) -> Optional[Dict[str, Any]]:
        """Precise lookup by NCAA game id + season + week."""
        rows = self._query(
            "SELECT * FROM predictions "
            "WHERE ncaa_game_id = %s AND season = %s AND week = %s "
            "ORDER BY prediction_made_at DESC LIMIT 1",
            (ncaa_game_id, season, week),
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


# Global instance (mirrors the old module-level supabase_client)
predictions_db = PredictionsDB()


def get_db() -> PredictionsDB:
    """Get the global PredictionsDB instance."""
    return predictions_db
