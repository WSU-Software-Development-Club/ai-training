"""LIVE historical grounding backfill for the weather factor.

Joins REAL game results (ml/training_data/training_data.csv, 2003-2024) to REAL
archived weather (Open-Meteo) at each stadium's coordinates, buckets each home
game, and writes the team's (bucket, won) history into weather_history. This
replaces the seeded demo history with genuine data; the grounder + guard then
serve (or withhold) a real win-rate depending on the real sample size.

Stadiums are read from the teams dimension (coords + tz populated by
ingest/teams_backfill.py from CFBD), so this covers every FBS venue with known
coordinates rather than a hardcoded pair. Run teams_backfill first.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .. import db
from ..score.weather import classify_bucket
from ..sources import open_meteo

_CSV = Path(__file__).resolve().parents[2] / "training_data" / "training_data.csv"


def _load_stadiums(database_url: str, only: set[str] | None = None) -> dict[str, tuple]:
    """{team name: (lat, lon, IANA tz)} for every FBS team the teams dimension
    has coords + tz for. The tz is the stadium's local timezone — passed to
    Open-Meteo (instead of "auto") AND used to convert each game's UTC kickoff,
    so the two sides of the date join agree (see _local_date()). ``only``
    restricts to a subset of team names (handy for a quick test run)."""
    with db.connect(database_url) as conn:
        rows = db.fetch_teams_with_coords(conn)
    stadiums = {
        r["name"]: (r["stadium_lat"], r["stadium_lon"], r["stadium_timezone"])
        for r in rows
        if not only or r["name"] in only
    }
    if not stadiums:
        raise RuntimeError(
            "No teams have stadium coords + timezone yet. Run the teams "
            "dimension backfill first: python -m ml.matchup_intel.ingest."
            "teams_backfill"
        )
    return stadiums


def _local_date(date_iso: str, tz_name: str) -> str:
    """Convert a UTC ISO kickoff timestamp (training_data.csv's 'date' column,
    e.g. '2003-11-09T00:00:00.000Z') to the stadium's LOCAL calendar date
    ('YYYY-MM-DD'). Evening Pacific kickoffs often serialize to the *next* UTC
    calendar day, so naively slicing date_iso[:10] joins to the wrong (or a
    missing) Open-Meteo daily row. Open-Meteo must be queried with this same
    tz_name (not "auto") so both sides of the join agree."""
    utc_dt = datetime.fromisoformat(date_iso.replace("Z", "+00:00"))
    return utc_dt.astimezone(ZoneInfo(tz_name)).date().isoformat()


def _home_games(teams: set[str], seasons: range) -> dict[str, list[tuple]]:
    """{team: [(date_iso, season, won), ...]} for non-neutral home games."""
    out: dict[str, list[tuple]] = defaultdict(list)
    with open(_CSV) as fh:
        for row in csv.DictReader(fh):
            team = row.get("home_team")
            if team not in teams:
                continue
            try:
                season = int(row["season"])
            except (KeyError, ValueError):
                continue
            if season not in seasons:
                continue
            if str(row.get("neutral_site", "")).lower() in ("true", "1"):
                continue  # home stadium weather only meaningful for true home games
            try:
                hs, as_ = int(row["home_score"]), int(row["away_score"])
            except (KeyError, ValueError):
                continue
            out[team].append((row["date"], season, hs > as_))
    return out


def backfill(database_url: str, *, seasons: range = range(2003, 2025),
             timeout: int = 60, only: set[str] | None = None) -> dict:
    """FETCH-THEN-WRITE, per team: all Open-Meteo HTTP calls happen with no DB
    connection open, results accumulate in memory, then a short-lived
    connection does the delete+bulk-insert and commits — so a mid-run network
    failure on one team doesn't lose already-completed teams, and no
    transaction sits idle for the ~duration of a team's HTTP calls.

    Stadiums come from the teams dimension (see _load_stadiums); ``only`` limits
    the run to a subset of team names for a quick smoke test."""
    stadiums = _load_stadiums(database_url, only=only)
    games = _home_games(set(stadiums), seasons)
    summary: dict[str, dict] = {}

    for team, (lat, lon, tz_name) in stadiums.items():
        by_season: dict[int, list[tuple]] = defaultdict(list)
        for date_iso, season, won in games.get(team, []):
            by_season[season].append((_local_date(date_iso, tz_name), won))

        # --- fetch phase: network only, no DB connection open -------------
        bucket_rows: dict[str, list[tuple]] = defaultdict(list)
        for season, glist in sorted(by_season.items()):
            print(f"[weather_backfill] {team} {season}: fetching {len(glist)} "
                  f"home date(s) from Open-Meteo...")
            # One archive call per season covers all that season's home dates.
            # Explicit tz (not "auto") so the join key matches _local_date().
            daily = open_meteo.archive_daily(
                lat, lon, f"{season}-08-01", f"{season}-12-31",
                timeout=timeout, timezone=tz_name)
            for day, won in glist:
                cond = daily.get(day)
                if not cond:
                    continue
                bucket = classify_bucket(open_meteo.daily_to_conditions(cond))
                bucket_rows[bucket].append((season, won))

        # --- write phase: short-lived connection, commits per team --------
        with db.connect(database_url) as conn:
            team_id = db.upsert_team(conn, team, stadium_lat=lat, stadium_lon=lon,
                                     stadium_timezone=tz_name)
            db.delete_weather_history_for_team(conn, team_id)   # idempotent refresh
            for bucket, results in bucket_rows.items():
                db.insert_weather_history_bulk(conn, team_id, bucket, results,
                                               source="cfbd+open-meteo")

        summary[team] = {b: len(r) for b, r in sorted(bucket_rows.items())}
        print(f"[weather_backfill] {team}: wrote {summary[team]}")
    return summary


if __name__ == "__main__":
    from ..config import load_config

    cfg = load_config()
    if not cfg.database_url:
        raise RuntimeError("DATABASE_URL is not set (see ml/matchup_intel/env.example)")
    result = backfill(cfg.database_url, timeout=cfg.request_timeout)
    for team, buckets in result.items():
        print(f"{team}: {buckets}")
