"""Postgres persistence for the matchup pipeline (psycopg3, parameterized SQL).

Follows the repo conventions: psycopg v3, ``%s``/named params only (no string
interpolation of values), TIMESTAMPTZ + UTC, soft external-id refs. Writes to
the teams / raw_signals / factors / factor_decks tables in db/schema.sql.
"""

from __future__ import annotations

import hashlib
import json
import re
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator, Optional
from uuid import UUID

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .schemas import Factor, RawSignalRef


def normalize_team_name(name: str) -> str:
    """Lowercase, collapse whitespace/punctuation — the join key to predictions."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def content_hash(source_type: str, payload: dict, published_at: Optional[str]) -> str:
    """Stable hash for idempotent ingest (ON CONFLICT (content_hash) DO NOTHING)."""
    blob = json.dumps(
        {"t": source_type, "p": payload, "d": published_at},
        sort_keys=True, default=str,
    )
    return hashlib.sha256(blob.encode()).hexdigest()


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


# --- teams -----------------------------------------------------------------

def upsert_team(
    conn: psycopg.Connection,
    name: str,
    *,
    cfbd_id: Optional[int] = None,
    conference: Optional[str] = None,
    venue_name: Optional[str] = None,
    stadium_lat: Optional[float] = None,
    stadium_lon: Optional[float] = None,
) -> str:
    """Insert or update a team by normalized_name; returns team_id (UUID str)."""
    normalized = normalize_team_name(name)
    row = conn.execute(
        """
        INSERT INTO teams (name, normalized_name, cfbd_id, conference,
                           venue_name, stadium_lat, stadium_lon, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, now())
        ON CONFLICT (normalized_name) DO UPDATE SET
            name       = COALESCE(EXCLUDED.name, teams.name),
            cfbd_id    = COALESCE(EXCLUDED.cfbd_id, teams.cfbd_id),
            conference = COALESCE(EXCLUDED.conference, teams.conference),
            venue_name = COALESCE(EXCLUDED.venue_name, teams.venue_name),
            stadium_lat = COALESCE(EXCLUDED.stadium_lat, teams.stadium_lat),
            stadium_lon = COALESCE(EXCLUDED.stadium_lon, teams.stadium_lon),
            updated_at = now()
        RETURNING team_id
        """,
        (name, normalized, cfbd_id, conference, venue_name, stadium_lat, stadium_lon),
    ).fetchone()
    return str(row[0])


# --- raw_signals + watermarks ---------------------------------------------

def insert_raw_signal(
    conn: psycopg.Connection,
    *,
    source_type: str,
    payload: dict,
    as_of_timestamp: datetime,
    published_at: Optional[datetime] = None,
    source_name: Optional[str] = None,
    source_url: Optional[str] = None,
    team_id: Optional[str] = None,
    ncaa_game_id: Optional[int] = None,
) -> Optional[str]:
    """Idempotent insert. Returns raw_id, or None if it was a duplicate."""
    chash = content_hash(source_type, payload, published_at.isoformat() if published_at else None)
    row = conn.execute(
        """
        INSERT INTO raw_signals (source_type, source_name, source_url, team_id,
                                 ncaa_game_id, payload, content_hash,
                                 published_at, as_of_timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (content_hash) DO NOTHING
        RETURNING raw_id
        """,
        (source_type, source_name, source_url,
         UUID(team_id) if team_id else None, ncaa_game_id,
         Jsonb(payload), chash, published_at, as_of_timestamp),
    ).fetchone()
    return str(row[0]) if row else None


def get_watermark(conn: psycopg.Connection, extractor: str) -> Optional[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "SELECT * FROM ingest_watermarks WHERE extractor = %s", (extractor,)
        ).fetchone()


def set_watermark(conn: psycopg.Connection, extractor: str, cursor: Optional[str]) -> None:
    conn.execute(
        """
        INSERT INTO ingest_watermarks (extractor, last_run_at, last_cursor, updated_at)
        VALUES (%s, now(), %s, now())
        ON CONFLICT (extractor) DO UPDATE SET
            last_run_at = now(), last_cursor = EXCLUDED.last_cursor, updated_at = now()
        """,
        (extractor, cursor),
    )


# --- factors ---------------------------------------------------------------

def fetch_raw_signals_for_game(
    conn: psycopg.Connection, ncaa_game_id: int, kickoff: datetime
) -> list[dict]:
    """Point-in-time: only signals observed at/before kickoff. The published_at
    check is applied in Python (logic.filter_point_in_time) for consistency, but
    we pre-filter as_of here to keep the working set small."""
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            """
            SELECT * FROM raw_signals
            WHERE ncaa_game_id = %s AND as_of_timestamp <= %s
            ORDER BY as_of_timestamp
            """,
            (ncaa_game_id, kickoff),
        ).fetchall()


def fetch_all_raw_signals_for_game(conn: psycopg.Connection, ncaa_game_id: int) -> list[dict]:
    """Every raw signal for a game, regardless of time. Extraction runs over all
    of them; the point-in-time filter is applied later at the serving boundary
    (serve.build_and_store_decks), matching the spec's 'filter at kickoff' rule."""
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "SELECT * FROM raw_signals WHERE ncaa_game_id = %s ORDER BY as_of_timestamp",
            (ncaa_game_id,),
        ).fetchall()


def insert_factor(conn: psycopg.Connection, factor: Factor) -> str:
    row = conn.execute(
        """
        INSERT INTO factors (ncaa_game_id, game_id, season, week, team_id,
            category, raw_signal, direction, magnitude, confidence, explanation,
            scoring_method, historical_rate, sample_size, sources,
            derived_from_raw_ids, grounding, as_of_timestamp)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING factor_id
        """,
        (
            factor.ncaa_game_id, factor.game_id, factor.season, factor.week,
            factor.team_id, factor.category, factor.raw_signal,
            factor.direction, factor.magnitude, factor.confidence,
            factor.explanation, factor.scoring_method, factor.historical_rate,
            factor.sample_size,
            Jsonb([s.model_dump(mode="json") for s in factor.sources]),
            list(factor.derived_from_raw_ids),
            Jsonb(factor.grounding) if factor.grounding is not None else None,
            factor.as_of_timestamp,
        ),
    ).fetchone()
    return str(row[0])


def fetch_factors_for_game(conn: psycopg.Connection, ncaa_game_id: int) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        return cur.execute(
            "SELECT * FROM factors WHERE ncaa_game_id = %s", (ncaa_game_id,)
        ).fetchall()


# --- reference panel + serving --------------------------------------------

def get_model_reference_panel(conn: psycopg.Connection, ncaa_game_id: int) -> Optional[dict]:
    """Layer 6: the existing XGBoost prediction, framed as an input not a verdict."""
    with conn.cursor(row_factory=dict_row) as cur:
        pred = cur.execute(
            """
            SELECT predicted_home_score, predicted_away_score, predicted_winner,
                   predicted_margin, predicted_total, betting_over_under,
                   over_probability, under_probability
            FROM predictions WHERE ncaa_game_id = %s
            """,
            (ncaa_game_id,),
        ).fetchone()
    if pred is None:
        return None
    return {
        "model": {k: pred[k] for k in (
            "predicted_home_score", "predicted_away_score", "predicted_winner",
            "predicted_margin", "predicted_total")},
        "vegas": {"over_under": pred["betting_over_under"]},
        # Polymarket is intentionally null until that extractor is wired.
        "polymarket": None,
    }


def upsert_factor_deck(
    conn: psycopg.Connection,
    *,
    ncaa_game_id: int,
    team_id: str,
    factors_view: list[dict],
    reference_panels: Optional[dict],
    as_of_timestamp: datetime,
) -> None:
    conn.execute(
        """
        INSERT INTO factor_decks (ncaa_game_id, team_id, factors,
                                  reference_panels, as_of_timestamp)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (ncaa_game_id, team_id, as_of_timestamp) DO UPDATE SET
            factors = EXCLUDED.factors,
            reference_panels = EXCLUDED.reference_panels,
            assembled_at = now()
        """,
        (ncaa_game_id, UUID(team_id) if isinstance(team_id, str) else team_id,
         Jsonb(factors_view),
         Jsonb(reference_panels) if reference_panels is not None else None,
         as_of_timestamp),
    )
