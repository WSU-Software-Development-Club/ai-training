"""Layer 0 ingestion for Polymarket odds (Layer-6 reference-panel input).

Best-effort and sparse by design: most CFB games have no Polymarket market at
all, and a "not found" game writes NOTHING to raw_signals (rather than a
placeholder row) — the absence of a row IS the null, which
``db.get_latest_polymarket_odds`` / ``db.get_model_reference_panel`` already
treat as "no data" for that game. Re-running is safe: prices move, so each
run's snapshot gets its own content_hash and is kept (not deduped away) as
long as at least one field differs from the last snapshot.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import db
from ..sources import polymarket


def ingest_game_odds(
    conn,
    *,
    ncaa_game_id: int,
    home_team: str,
    away_team: str,
    game_date: str,
    timeout: int = 30,
) -> bool:
    """Fetch + persist one game's current Polymarket snapshot.

    Returns True if a signal was written (a market was found and a fresh
    snapshot inserted), False otherwise — no market, an unchanged duplicate
    snapshot, and a transport failure are all silent no-ops by design.
    """
    odds = polymarket.fetch_game_odds(home_team, away_team, game_date, timeout=timeout)
    if odds is None:
        return False
    raw_id = db.insert_raw_signal(
        conn,
        source_type="polymarket",
        payload=odds,
        as_of_timestamp=datetime.now(timezone.utc),
        published_at=None,  # a live order-book snapshot has no fixed publish time
        source_name="Polymarket",
        source_url=odds.get("source_url"),
        team_id=None,  # game-level signal; payload carries both teams' probabilities
        ncaa_game_id=ncaa_game_id,
    )
    return raw_id is not None


def ingest_seed_odds(conn, timeout: int = 30) -> dict:
    """Best-effort odds ingest for every seeded game. Re-runnable/idempotent
    per ``ingest_game_odds``; a per-game failure never aborts the batch."""
    from .seed import load_seed_games

    games = load_seed_games()
    found = 0
    for game in games:
        try:
            ok = ingest_game_odds(
                conn,
                ncaa_game_id=game["ncaa_game_id"],
                home_team=game["home_team"],
                away_team=game["away_team"],
                game_date=game["kickoff"],
                timeout=timeout,
            )
        except Exception:
            ok = False
        found += int(ok)
    return {"games": len(games), "polymarket_markets_found": found}


if __name__ == "__main__":
    from ..config import load_config

    cfg = load_config()
    with db.connect(cfg.database_url) as conn:
        print(ingest_seed_odds(conn, timeout=cfg.request_timeout))
