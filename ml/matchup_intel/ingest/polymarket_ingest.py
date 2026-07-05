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


def ingest_game_history(
    conn,
    *,
    ncaa_game_id: int,
    home_team: str,
    away_team: str,
    game_date: str,
    timeout: int = 30,
    fidelity: int = 1,
) -> int:
    """Backfill a PAST game's full Polymarket win-probability CURVE.

    Unlike ``ingest_game_odds`` (one current-price snapshot for an upcoming
    game), this pulls the whole archived time series from CLOB /prices-history
    and writes each point as its own ``polymarket`` raw_signal, so the post-game
    view can render the same curve Polymarket shows. Each point's own timestamp
    is used for BOTH ``as_of_timestamp`` and ``published_at``, which (via
    ``content_hash``) makes the backfill idempotent and re-runnable — re-running
    only inserts genuinely new points.

    Returns the number of points inserted (0 = no market/history, or already
    fully ingested), never raising."""
    try:
        history = polymarket.fetch_game_price_history(
            home_team, away_team, game_date, timeout=timeout, fidelity=fidelity
        )
    except Exception:
        history = None
    if not history or not history.get("points"):
        return 0

    question = history.get("question")
    slug = history.get("slug")
    source_url = history.get("source_url")
    market_id = history.get("market_id")

    inserted = 0
    for pt in history["points"]:
        try:
            as_of = datetime.fromisoformat(pt["as_of"])
        except (ValueError, KeyError, TypeError):
            continue
        payload = {
            "home_win_prob": pt.get("home_win_prob"),
            "away_win_prob": pt.get("away_win_prob"),
            "market_id": market_id,
            "question": question,
            "slug": slug,
            "source_url": source_url,
            "is_history": True,  # distinguishes a curve point from a live snapshot
        }
        try:
            raw_id = db.insert_raw_signal(
                conn,
                source_type="polymarket",
                payload=payload,
                as_of_timestamp=as_of,
                published_at=as_of,  # the point's own market timestamp
                source_name="Polymarket",
                source_url=source_url,
                team_id=None,
                ncaa_game_id=ncaa_game_id,
            )
        except Exception:
            raw_id = None
        inserted += int(raw_id is not None)
    return inserted


def backfill_all_history(conn, timeout: int = 30, fidelity: int = 1) -> dict:
    """Best-effort curve backfill for every game in ``predictions``. Sparse by
    design (most CFB games have no market); a per-game failure never aborts the
    batch. Returns a small summary dict."""
    with conn.cursor() as cur:
        # Only PAST games can have a resolved price curve — skip anything whose
        # kickoff is still in the future (e.g. next-season schedule rows) so the
        # sweep doesn't waste a search request per game that cannot have data.
        # Most-recent first, so the latest bowl/playoff games (where markets are
        # most likely) populate before older regular-season games.
        games = cur.execute(
            "SELECT ncaa_game_id, home_team, away_team, game_date "
            "FROM predictions WHERE ncaa_game_id IS NOT NULL "
            "AND game_date IS NOT NULL AND game_date < now() "
            "ORDER BY game_date DESC"
        ).fetchall()

    games_with_market = 0
    total_points = 0
    for ncaa_game_id, home_team, away_team, game_date in games:
        if not game_date:
            continue
        n = ingest_game_history(
            conn,
            ncaa_game_id=ncaa_game_id,
            home_team=home_team,
            away_team=away_team,
            game_date=game_date.isoformat(),
            timeout=timeout,
            fidelity=fidelity,
        )
        if n:
            games_with_market += 1
            total_points += n
        # Commit per game so a long best-effort backfill keeps partial progress
        # if a later game errors or the run is interrupted.
        conn.commit()
    return {
        "games_scanned": len(games),
        "games_with_history": games_with_market,
        "points_inserted": total_points,
    }


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
    import os
    import sys

    from ..config import load_config

    cfg = load_config()
    # `python -m ...polymarket_ingest history` backfills the full price CURVE for
    # every past game (what the post-game view renders); no arg keeps the old
    # behavior of ingesting one current-price snapshot per seeded game.
    mode = sys.argv[1] if len(sys.argv) > 1 else "seed"
    with db.connect(cfg.database_url) as conn:
        if mode == "history":
            # In-game sampling resolution (minutes); env override for the CI job.
            try:
                fidelity = int(os.environ.get("POLYMARKET_FIDELITY", "1"))
            except ValueError:
                fidelity = 1
            print(backfill_all_history(conn, timeout=cfg.request_timeout, fidelity=fidelity))
        else:
            print(ingest_seed_odds(conn, timeout=cfg.request_timeout))
