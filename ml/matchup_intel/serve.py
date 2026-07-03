"""Layer 5 — assemble + serve per-team factor decks.

Reads persisted factors, enforces point-in-time (as_of <= kickoff), dedupes,
ranks, applies the sample-size guard (via logic.assemble_deck), attaches the
Layer-6 reference panel, and materializes to factor_decks.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from . import db
from .logic import assemble_deck
from .schemas import Factor, Source


def _row_to_factor(row: dict) -> Factor:
    sources = [Source.model_validate(s) for s in (row.get("sources") or [])]
    return Factor(
        ncaa_game_id=row["ncaa_game_id"],
        game_id=row.get("game_id"),
        season=row.get("season"),
        week=row.get("week"),
        team_id=row["team_id"] if isinstance(row["team_id"], UUID) else UUID(str(row["team_id"])),
        category=row["category"],
        raw_signal=row.get("raw_signal"),
        direction=row["direction"],
        magnitude=row["magnitude"],
        confidence=row["confidence"],
        explanation=row["explanation"],
        scoring_method=row["scoring_method"],
        historical_rate=row.get("historical_rate"),
        sample_size=row.get("sample_size", 0),
        sources=sources,
        derived_from_raw_ids=[
            r if isinstance(r, UUID) else UUID(str(r))
            for r in (row.get("derived_from_raw_ids") or [])
        ],
        grounding=row.get("grounding"),
        as_of_timestamp=row["as_of_timestamp"],
    )


def build_and_store_decks(
    conn,
    *,
    ncaa_game_id: int,
    kickoff: datetime,
    threshold: int,
) -> dict[str, list[dict]]:
    """Assemble+serve both teams' decks for one game. Returns {team_id: deck}."""
    rows = db.fetch_factors_for_game(conn, ncaa_game_id)
    factors = [_row_to_factor(r) for r in rows]

    # Point-in-time: only factors knowable by kickoff feed the served deck.
    factors = [f for f in factors if f.as_of_timestamp <= kickoff]

    reference = db.get_model_reference_panel(conn, ncaa_game_id)

    by_team: dict[str, list[Factor]] = {}
    for f in factors:
        by_team.setdefault(str(f.team_id), []).append(f)

    decks: dict[str, list[dict]] = {}
    for team_id, team_factors in by_team.items():
        deck = assemble_deck(team_factors, threshold)  # dedupe -> rank -> guard
        db.upsert_factor_deck(
            conn,
            ncaa_game_id=ncaa_game_id,
            team_id=team_id,
            factors_view=deck,
            reference_panels=reference,
            as_of_timestamp=kickoff,
        )
        decks[team_id] = deck
    return decks
