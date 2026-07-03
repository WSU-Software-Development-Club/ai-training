"""Point-in-time feature-store reader/writer for the stacked ensemble.

READER (the leakage-critical half): assembles a per-game or per-team feature
vector using the exact AS-OF pattern documented in db/schema.sql — newest
``feature_values`` row per ``feature_name`` with ``as_of_timestamp <= kickoff``,
restricted to ``feature_definitions.point_in_time_safe``. Kickoff is ALWAYS an
explicit argument (``predictions.game_date`` for the game in question) — this
module never calls ``now()`` to decide what's visible, which is what would
silently reintroduce leakage.

WRITER: catalog-first (a ``feature_definitions`` row must exist before a value
is written; ``write_feature_value``/``write_feature_values_bulk`` create it if
missing) and idempotent, upserting on the same
``UNIQUE NULLS NOT DISTINCT (feature_name, ncaa_game_id, team_id, as_of_timestamp)``
key the schema defines.

Anti-leakage measures (structural, not just convention):
  1. Every read takes ``kickoff`` as a required argument — there is no
     "current" read path that defaults to ``now()``.
  2. The SQL filters ``as_of_timestamp <= kickoff`` AND
     ``feature_definitions.point_in_time_safe`` in the same query — a caller
     cannot accidentally see a leaky or future-dated row.
  3. ``DISTINCT ON (feature_name) ... ORDER BY feature_name, as_of_timestamp DESC``
     takes the newest *qualifying* value, never the newest overall.
  4. The pure ``_latest_asof_by_feature`` helper (no DB) implements the same
     rule so it's unit-testable without Postgres — see tests/test_feature_store.py.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import datetime
from typing import Iterable, Iterator, Optional
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

# --- team-name normalization ------------------------------------------------
# Duplicated (not imported) from ml/matchup_intel/db.py deliberately: this
# package must not import ml.matchup_intel (concurrent edits there, and this
# package should not couple its leakage-critical read path to another team's
# in-flight module). Keep this regex identical to matchup_intel's if it changes.


def normalize_team_name(name: str) -> str:
    """Lowercase, collapse whitespace/punctuation — the join key to ``teams``."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


@contextmanager
def connect(database_url: str) -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# --- pure as-of assembly (no DB — unit-testable) ----------------------------


def _row_value(row: dict):
    """A feature_values row carries value_num XOR value_text; prefer numeric."""
    return row["value_num"] if row.get("value_num") is not None else row.get("value_text")


def _latest_asof_by_feature(rows: Iterable[dict], kickoff: datetime) -> dict:
    """Pure core of the as-of read: given candidate rows (each a dict with at
    least ``feature_name``, ``value_num``, ``value_text``, ``as_of_timestamp``,
    and optionally ``point_in_time_safe``), return the newest-per-feature value
    known at or before ``kickoff``.

    Mirrors the SQL in db/schema.sql exactly:
      WHERE as_of_timestamp <= kickoff AND point_in_time_safe
      ORDER BY feature_name, as_of_timestamp DESC  (newest wins)

    ``point_in_time_safe`` defaults to True when absent (e.g. when the caller
    has already pre-filtered via the SQL join) so this helper can be reused
    both as a defensive re-check and as a pure in-memory test target.
    """
    latest: dict[str, tuple[datetime, object]] = {}
    for row in rows:
        as_of = row["as_of_timestamp"]
        if as_of > kickoff:
            continue  # POINT-IN-TIME cutoff — never visible to this game/team
        if not row.get("point_in_time_safe", True):
            continue  # leaky feature — never served to the model
        name = row["feature_name"]
        incumbent = latest.get(name)
        if incumbent is None or as_of > incumbent[0]:
            latest[name] = (as_of, _row_value(row))
    return {name: value for name, (_, value) in latest.items()}


# --- DB-backed as-of reads (game-level, team-level) -------------------------

_GAME_ASOF_SQL = """
    SELECT DISTINCT ON (fv.feature_name)
           fv.feature_name, fv.value_num, fv.value_text
    FROM feature_values fv
    JOIN feature_definitions fd USING (feature_name)
    WHERE fv.ncaa_game_id = %(ncaa_game_id)s
      AND fv.as_of_timestamp <= %(kickoff)s
      AND fd.point_in_time_safe
    ORDER BY fv.feature_name, fv.as_of_timestamp DESC
"""

_TEAM_ASOF_SQL = """
    SELECT DISTINCT ON (fv.feature_name)
           fv.feature_name, fv.value_num, fv.value_text
    FROM feature_values fv
    JOIN feature_definitions fd USING (feature_name)
    WHERE fv.team_id = %(team_id)s
      AND fv.as_of_timestamp <= %(kickoff)s
      AND fd.point_in_time_safe
    ORDER BY fv.feature_name, fv.as_of_timestamp DESC
"""


def fetch_game_features_asof(
    conn: psycopg.Connection, ncaa_game_id: int, kickoff: datetime
) -> dict:
    """Game-level point-in-time feature vector: {feature_name: value}."""
    with conn.cursor(row_factory=dict_row) as cur:
        rows = cur.execute(
            _GAME_ASOF_SQL, {"ncaa_game_id": ncaa_game_id, "kickoff": kickoff}
        ).fetchall()
    return {r["feature_name"]: _row_value(r) for r in rows}


def fetch_team_features_asof(
    conn: psycopg.Connection, team_id, kickoff: datetime
) -> dict:
    """Team-level point-in-time feature vector: {feature_name: value}."""
    tid = team_id if isinstance(team_id, UUID) else UUID(str(team_id))
    with conn.cursor(row_factory=dict_row) as cur:
        rows = cur.execute(
            _TEAM_ASOF_SQL, {"team_id": tid, "kickoff": kickoff}
        ).fetchall()
    return {r["feature_name"]: _row_value(r) for r in rows}


def get_team_id(conn: psycopg.Connection, team_name: str) -> Optional[str]:
    """Look up teams.team_id by normalized_name (soft ref from predictions'
    TEXT home_team/away_team), or None if the team isn't in the dimension yet."""
    row = conn.execute(
        "SELECT team_id FROM teams WHERE normalized_name = %s",
        (normalize_team_name(team_name),),
    ).fetchone()
    return str(row[0]) if row else None


def assemble_matchup_feature_vector(
    conn: psycopg.Connection,
    *,
    ncaa_game_id: int,
    home_team: str,
    away_team: str,
    kickoff: datetime,
) -> dict:
    """Full point-in-time feature vector for one game: game-level features
    (unprefixed) + home/away team-level features (``home_``/``away_`` prefixed,
    matching the ml/m1 training-data convention). Missing team rows (team not
    yet in the ``teams`` dimension) simply contribute no team-level features —
    this degrades gracefully rather than raising, consistent with the rest of
    the schema's soft-ref philosophy.
    """
    vector: dict = {}
    vector.update(fetch_game_features_asof(conn, ncaa_game_id, kickoff))

    home_team_id = get_team_id(conn, home_team)
    if home_team_id is not None:
        for k, v in fetch_team_features_asof(conn, home_team_id, kickoff).items():
            vector[f"home_{k}"] = v

    away_team_id = get_team_id(conn, away_team)
    if away_team_id is not None:
        for k, v in fetch_team_features_asof(conn, away_team_id, kickoff).items():
            vector[f"away_{k}"] = v

    return vector


# --- catalog-first writer ---------------------------------------------------


def upsert_feature_definition(
    conn: psycopg.Connection,
    feature_name: str,
    *,
    dtype: str = "numeric",
    entity_level: str = "team_game",
    unit: Optional[str] = None,
    source: Optional[str] = None,
    point_in_time_safe: bool = True,
    description: Optional[str] = None,
) -> None:
    """Register (or update) a feature's catalog entry. Values are never
    written for a feature that hasn't been declared here first — this keeps
    ``point_in_time_safe`` an explicit, reviewable decision per feature rather
    than an incidental default."""
    conn.execute(
        """
        INSERT INTO feature_definitions
            (feature_name, description, dtype, entity_level, unit, source,
             point_in_time_safe, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (feature_name) DO UPDATE SET
            description        = COALESCE(EXCLUDED.description, feature_definitions.description),
            dtype               = EXCLUDED.dtype,
            entity_level        = EXCLUDED.entity_level,
            unit                = COALESCE(EXCLUDED.unit, feature_definitions.unit),
            source              = COALESCE(EXCLUDED.source, feature_definitions.source),
            point_in_time_safe  = EXCLUDED.point_in_time_safe,
            updated_at          = now()
        """,
        (feature_name, description, dtype, entity_level, unit, source, point_in_time_safe),
    )


def write_feature_value(
    conn: psycopg.Connection,
    feature_name: str,
    *,
    as_of_timestamp: datetime,
    source: str,
    ncaa_game_id: Optional[int] = None,
    team_id: Optional[str] = None,
    game_id: Optional[int] = None,
    season: Optional[int] = None,
    week: Optional[int] = None,
    value_num: Optional[float] = None,
    value_text: Optional[str] = None,
    dtype: str = "numeric",
    entity_level: Optional[str] = None,
    point_in_time_safe: bool = True,
) -> None:
    """Catalog-first, idempotent upsert of one feature_values row.

    Ensures a feature_definitions row exists (creating a minimal one on first
    write if needed) then upserts on the schema's
    ``UNIQUE NULLS NOT DISTINCT (feature_name, ncaa_game_id, team_id, as_of_timestamp)``
    key. Exactly one of ``value_num``/``value_text`` must be set (the schema's
    CHECK constraint enforces this too).
    """
    if value_num is None and value_text is None:
        raise ValueError("write_feature_value requires value_num or value_text")
    if ncaa_game_id is None and team_id is None:
        raise ValueError("write_feature_value requires ncaa_game_id and/or team_id")

    inferred_entity_level = entity_level or (
        "team_game" if (ncaa_game_id is not None and team_id is not None)
        else ("game" if team_id is None else "team")
    )
    upsert_feature_definition(
        conn, feature_name, dtype=dtype, entity_level=inferred_entity_level,
        point_in_time_safe=point_in_time_safe,
    )

    tid = UUID(team_id) if isinstance(team_id, str) else team_id
    conn.execute(
        """
        INSERT INTO feature_values
            (feature_name, ncaa_game_id, game_id, team_id, season, week,
             value_num, value_text, as_of_timestamp, source)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (feature_name, ncaa_game_id, team_id, as_of_timestamp) DO UPDATE SET
            value_num  = EXCLUDED.value_num,
            value_text = EXCLUDED.value_text,
            season     = EXCLUDED.season,
            week       = EXCLUDED.week,
            game_id    = COALESCE(EXCLUDED.game_id, feature_values.game_id),
            source     = EXCLUDED.source
        """,
        (feature_name, ncaa_game_id, game_id, tid, season, week,
         value_num, value_text, as_of_timestamp, source),
    )


def write_feature_values_bulk(conn: psycopg.Connection, rows: list[dict]) -> int:
    """Write many feature_values rows (each a kwargs dict for
    ``write_feature_value``). Best-effort per-row: one bad row doesn't abort
    the batch. Returns the count successfully written."""
    written = 0
    for row in rows:
        try:
            write_feature_value(conn, row.pop("feature_name"), **row)
            written += 1
        except Exception as exc:  # pragma: no cover - defensive, logged not raised
            print(f"[WARNING] write_feature_value failed for row {row}: {exc}")
    return written


def main() -> None:
    """Smoke-test CLI: print the point-in-time feature vector for one game.

    Usage: python -m ml.ensemble.feature_store <ncaa_game_id>

    Requires DATABASE_URL and a live game in `predictions` (for game_date /
    home_team / away_team) plus the feature store actually being populated —
    which it is not yet (feature ingestion isn't built). Expect an empty dict
    until that pipeline exists; this script exists to prove the read path is
    wired correctly against a real Postgres instance.
    """
    import sys

    from .config import load_config

    if len(sys.argv) != 2:
        print("Usage: python -m ml.ensemble.feature_store <ncaa_game_id>")
        sys.exit(1)
    ncaa_game_id = int(sys.argv[1])

    cfg = load_config()
    if not cfg.database_url:
        print("[ERROR] DATABASE_URL is not set.")
        sys.exit(1)

    with connect(cfg.database_url) as conn:
        row = conn.execute(
            "SELECT game_date, home_team, away_team FROM predictions WHERE ncaa_game_id = %s",
            (ncaa_game_id,),
        ).fetchone()
        if row is None:
            print(f"[ERROR] No predictions row for ncaa_game_id={ncaa_game_id}")
            sys.exit(1)
        kickoff, home_team, away_team = row
        vector = assemble_matchup_feature_vector(
            conn, ncaa_game_id=ncaa_game_id, home_team=home_team,
            away_team=away_team, kickoff=kickoff,
        )
    print(f"kickoff={kickoff} home={home_team!r} away={away_team!r}")
    print(f"features ({len(vector)}): {vector}")


if __name__ == "__main__":
    main()
