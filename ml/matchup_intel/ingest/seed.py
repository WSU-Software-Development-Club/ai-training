"""Seed-first ingestion (Layer 0): load the bundled seed games into raw_signals.

Idempotent (content_hash ON CONFLICT DO NOTHING) and re-runnable. Returns the
games so downstream stages know each game's kickoff for point-in-time filtering.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .. import db

_SEED_PATH = Path(__file__).resolve().parent / "seed_data.json"


def load_seed_games() -> list[dict]:
    with open(_SEED_PATH) as fh:
        return json.load(fh)["games"]


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def ingest_seed(conn) -> dict:
    """Upsert teams + insert raw_signals for every seed game. Returns a summary."""
    games = load_seed_games()
    inserted = 0
    seen = 0
    for game in games:
        # Ensure both teams exist in the dimension.
        home_id = db.upsert_team(conn, game["home_team"])
        away_id = db.upsert_team(conn, game["away_team"])
        team_ids = {
            db.normalize_team_name(game["home_team"]): home_id,
            db.normalize_team_name(game["away_team"]): away_id,
        }
        for sig in game.get("signals", []):
            seen += 1
            team_id = team_ids.get(db.normalize_team_name(sig["team"]))
            # Persist the factor category inside the payload so the extraction
            # stage (which reads only raw_signals rows) can see it.
            payload = {**sig["payload"], "category": sig.get("category", "QB")}
            raw_id = db.insert_raw_signal(
                conn,
                source_type=sig["source_type"],
                payload=payload,
                as_of_timestamp=_parse_ts(sig["as_of_timestamp"]),
                published_at=_parse_ts(sig.get("published_at")),
                source_name=sig.get("source_name"),
                source_url=sig.get("source_url"),
                team_id=team_id,
                ncaa_game_id=game["ncaa_game_id"],
            )
            if raw_id:
                inserted += 1
    db.set_watermark(conn, "seed", cursor=str(len(games)))
    return {"games": len(games), "signals_seen": seen, "signals_inserted": inserted}


if __name__ == "__main__":
    from ..config import load_config

    cfg = load_config()
    with db.connect(cfg.database_url) as conn:
        print(ingest_seed(conn))
