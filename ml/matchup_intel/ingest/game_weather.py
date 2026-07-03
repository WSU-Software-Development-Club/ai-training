"""Observed-weather-per-game ingest -> real weather factor decks.

The offseason/historical analog of a live forecast job: for each real game in
the predictions table (that has a home stadium with coords + tz), fetch the
ACTUAL OBSERVED weather (Open-Meteo archive) at the home stadium on the game's
local date, write a weather raw_signal, then run the existing weather scorer ->
grounder -> serve path so the game gets a real weather factor deck. Reference
panels (XGBoost model + Vegas) attach automatically at serve time.

Real inputs only — observed weather, real model predictions, real Vegas lines,
real historical outcomes for grounding. Idempotent: raw_signals dedupe on
content_hash, factors reset per game, decks upsert. Per-game try/except so one
bad game never aborts the slate.

Prerequisites:
  1. teams_backfill  — populates the teams dimension (coords + tz) this joins on.
  2. weather_backfill — grounds weather_history so the guard can surface a real
     historical rate (without it, factors still serve but the rate is withheld).

Run:  python -m ml.matchup_intel.ingest.game_weather [season] [min_week]
      (defaults: season=2025, min_week=0 = whole season)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from .. import db
from ..config import Config, load_config
from ..flows import extract_and_ground_stage, serve_stage
from ..sources import open_meteo
from .weather_backfill import _local_date

# Weather is knowable well before kickoff; stamp the signal a few hours prior so
# the point-in-time serving filter (as_of <= kickoff) always accepts it.
_AS_OF_LEAD = timedelta(hours=6)

# Join predictions -> teams on the same normalized-name key the rest of the
# engine uses. Only games with home coords + tz + a kickoff can be weathered.
_GAMES_SQL = """
SELECT p.ncaa_game_id, p.season, p.week, p.home_team, p.game_date,
       t.team_id, t.stadium_lat, t.stadium_lon, t.stadium_timezone
FROM predictions p
JOIN teams t
  ON t.normalized_name = regexp_replace(lower(p.home_team), '[^a-z0-9]+', ' ', 'g')
WHERE p.season = %s AND p.week >= %s
  AND t.stadium_lat IS NOT NULL
  AND t.stadium_timezone IS NOT NULL
  AND p.game_date IS NOT NULL
ORDER BY p.week, p.ncaa_game_id
"""


def fetch_games(conn, season: int, min_week: int) -> list[dict]:
    """Real games (with home-stadium coords + tz) to attach weather to."""
    with conn.cursor() as cur:
        cur.execute(_GAMES_SQL, (season, min_week))
        cols = [c.name for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def build_payload(home_team: str, conditions: dict, as_of: datetime) -> dict:
    """Weather raw_signal payload: observed conditions + a fan-readable line +
    a self-referential source for provenance. Pure (no I/O)."""
    text = (
        f"Observed conditions at {home_team}'s stadium: "
        f"~{round(conditions['temp_f'])}°F, wind {round(conditions['wind_mph'])} mph, "
        f"{'wet' if (conditions.get('precip_prob') or 0) >= 0.6 else 'dry'}."
    )
    return {
        "text": text,
        "conditions": conditions,
        "sources": [{
            "source_type": "weather",
            "url": "https://open-meteo.com",
            "snippet": text,
            "published_at": as_of.isoformat(),
        }],
    }


def _game_conditions(game: dict, timeout: int) -> Optional[dict]:
    """Observed conditions at the home stadium on the game's LOCAL date, or None
    if the archive has no row for that day."""
    tz = game["stadium_timezone"]
    local = _local_date(game["game_date"].isoformat(), tz)
    daily = open_meteo.archive_daily(
        game["stadium_lat"], game["stadium_lon"], local, local,
        timeout=timeout, timezone=tz)
    day = daily.get(local)
    return open_meteo.daily_to_conditions(day) if day else None


def ingest_game(cfg: Config, game: dict) -> str:
    """One game end-to-end: observed weather -> raw_signal -> factor + grounding
    -> served deck. Returns 'deck' or 'no_weather'."""
    conditions = _game_conditions(game, cfg.request_timeout)
    if conditions is None:
        return "no_weather"

    as_of = game["game_date"] - _AS_OF_LEAD
    payload = build_payload(game["home_team"], conditions, as_of)
    with db.connect(cfg.database_url) as conn:
        db.insert_raw_signal(
            conn, source_type="weather", payload=payload,
            as_of_timestamp=as_of, published_at=as_of,
            source_name="open-meteo", source_url="https://open-meteo.com",
            team_id=str(game["team_id"]), ncaa_game_id=game["ncaa_game_id"])

    served = {
        "ncaa_game_id": game["ncaa_game_id"],
        "season": game["season"],
        "week": game["week"],
        "kickoff": game["game_date"].isoformat(),
    }
    extract_and_ground_stage(cfg, served)  # weather -> Layer-2 scorer + grounding
    serve_stage(cfg, served)               # assemble + guard + upsert deck
    return "deck"


def run(cfg: Config, *, season: int = 2025, min_week: int = 0) -> dict:
    """Weather-deck every eligible real game for a season. Returns a summary."""
    if not cfg.database_url:
        raise RuntimeError("DATABASE_URL is not set (see ml/matchup_intel/env.example)")

    with db.connect(cfg.database_url) as conn:
        games = fetch_games(conn, season, min_week)
    print(f"[game_weather] {len(games)} games (season={season}, week>={min_week})")

    made = no_weather = failed = 0
    for game in games:
        try:
            if ingest_game(cfg, game) == "deck":
                made += 1
            else:
                no_weather += 1
        except Exception as exc:  # one game must not abort the slate
            failed += 1
            print(f"[game_weather] FAIL {game['home_team']} {game['ncaa_game_id']}: {exc}")
        if (made + no_weather + failed) % 50 == 0:
            print(f"[game_weather] progress: {made} decks / {no_weather} no-weather "
                  f"/ {failed} failed")

    summary = {"season": season, "games": len(games), "decks": made,
               "no_weather": no_weather, "failed": failed}
    print(f"[game_weather] DONE: {summary}")
    return summary


if __name__ == "__main__":
    import sys

    cfg = load_config()
    season = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
    min_week = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    run(cfg, season=season, min_week=min_week)
