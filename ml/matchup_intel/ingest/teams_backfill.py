"""Populate the teams dimension from CFBD — the foundation for real data.

Pulls the FBS team list (with each team's nested venue location) from CFBD and
upserts name / cfbd_id / conference / venue_name / stadium coords / timezone
into the ``teams`` table. This is the prerequisite for the league-wide weather
backfill (which reads stadium coords + tz straight back out of teams) and for
keying factors by a real team_id instead of the two seeded demo teams.

Idempotent: upsert-on-normalized_name, so re-running refreshes conference moves
and venue changes without creating duplicates. Team NAMES come from the same
CFBD source as training_data.csv (collect_data.py's /games), so teams.name lines
up with the weather backfill's home_team join key.

Run:  python -m ml.matchup_intel.ingest.teams_backfill [year]
(needs CFBD_API_KEY + DATABASE_URL in the environment / ml/matchup_intel/.env)
"""

from __future__ import annotations

from .. import db
from ..sources import cfbd

# CFBD's current-season FBS membership. Bumped as the default view of "who is
# FBS"; historical weather still backfills from training_data.csv regardless.
_DEFAULT_YEAR = 2024


def backfill(database_url: str, cfbd_api_key: str, *, year: int = _DEFAULT_YEAR,
             timeout: int = 30) -> dict:
    """Upsert every FBS team for ``year`` into the teams dimension. Returns a
    small summary {total, with_coords, without_coords}."""
    teams = cfbd.fetch_fbs_teams(cfbd_api_key, year, timeout=timeout)
    if not teams:
        raise RuntimeError(
            f"CFBD returned no FBS teams for {year}; refusing to proceed "
            "(check CFBD_API_KEY and the year)."
        )

    total = with_coords = 0
    with db.connect(database_url) as conn:
        for raw in teams:
            v = cfbd.team_venue(raw)
            if not v["name"]:
                continue  # can't key a team with no school name
            db.upsert_team(
                conn, v["name"],
                cfbd_id=v["cfbd_id"],
                conference=v["conference"],
                venue_name=v["venue_name"],
                stadium_lat=v["lat"],
                stadium_lon=v["lon"],
                stadium_timezone=v["timezone"],
            )
            total += 1
            if v["lat"] is not None and v["lon"] is not None and v["timezone"]:
                with_coords += 1

    summary = {
        "year": year,
        "total": total,
        "with_coords": with_coords,
        "without_coords": total - with_coords,
    }
    print(f"[teams_backfill] {summary}")
    return summary


if __name__ == "__main__":
    import sys

    from ..config import load_config

    cfg = load_config()
    if not cfg.database_url:
        raise RuntimeError("DATABASE_URL is not set (see ml/matchup_intel/env.example)")
    if not cfg.cfbd_api_key:
        raise RuntimeError("CFBD_API_KEY is not set (see ml/matchup_intel/env.example)")

    year = int(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_YEAR
    backfill(cfg.database_url, cfg.cfbd_api_key, year=year, timeout=cfg.request_timeout)
