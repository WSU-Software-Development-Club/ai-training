#!/usr/bin/env python3
"""LOCAL-DEV-ONLY seeder: render a real World Cup matchup end-to-end.

Loads one or two committed World Cup Polymarket fixtures into the LOCAL compose
Postgres so the SPA surfaces them at ``/matchup/<ncaa_game_id>`` while CFB is
dormant. It writes:

    teams          -> one row per club (Paraguay, France, ...) via upsert_team
    predictions    -> one synthetic, all-nullable row per game (ncaa_game_id
                      UNIQUE upsert). Required: get_matchup_deck returns None
                      unless a prediction row exists, and it's what makes both
                      team columns render (home_team/away_team).
    raw_signals    -> one 'polymarket' provenance row per game (idempotent on
                      content_hash) — mirrors the real Layer-0 ingest.
    factor_decks   -> one row per team (factors = [], reference_panels = the
                      full 3-way odds). This is where the Polymarket reference
                      panel actually lives for the serving read.

Odds are parsed OFFLINE from the committed fixtures through the now-3-way-aware
``polymarket.extract_odds`` path (CLOB midpoint is neutralized so the fixture's
cached ``outcomePrices`` are used — deterministic, no network). NO live fetch.

Idempotent: safe to re-run. teams upsert on normalized_name, predictions upsert
on ncaa_game_id, raw_signals dedupe on content_hash, factor_decks upsert on
(ncaa_game_id, team_id, as_of_timestamp).

============================  SAFETY  ========================================
This must ONLY ever write to the local compose Postgres, NEVER troyster/prod.
Guarantees, in order:
  1. It does NOT read the ambient DATABASE_URL (which on this machine may point
     at troyster for ml/ jobs). It resolves its own DSN, defaulting to the
     compose-local one, or an explicit --database-url.
  2. It parses the DSN host and REFUSES to run unless the host is in a strict
     local-only allowlist (localhost / 127.0.0.1 / ::1 / the compose service
     name 'db'). troyster (192.168.1.126 / *.ts.net / 'troyster') is not in the
     allowlist, so the script structurally cannot reach it.
  3. It is a DRY RUN by default. It prints the resolved DSN (password masked),
     the guard verdict, and every write it WOULD make, and only mutates the DB
     when passed --apply.
=============================================================================
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

# --- import the matchup pipeline package from the repo root ------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml.matchup_intel import db  # noqa: E402
from ml.matchup_intel.sources import polymarket  # noqa: E402

_FIXTURES = _REPO_ROOT / "ml" / "matchup_intel" / "tests" / "fixtures"

# The compose-local DSN (host-side; docker-compose.dev.yml maps db:5432 -> 5432).
# Deliberately NOT os.environ["DATABASE_URL"] — that may point at troyster.
_DEFAULT_LOCAL_DSN = "postgresql://aitraining:aitraining@localhost:5432/aitraining"

# Only these hosts are accepted. All are structurally local: loopback, or the
# compose service name 'db' (resolvable only inside the compose network, i.e.
# definitionally the local dev DB). troyster is reachable only as 192.168.1.126
# / a tailscale name / 'troyster' — none of which appear here.
_ALLOWED_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "db"}

# Explicitly blocked, for a clear error if someone points this at prod.
_BLOCKED_SUBSTRINGS = ("192.168.1.126", "troyster", ".ts.net", "tailscale")


# --- the games to seed -------------------------------------------------------
# Synthetic, clearly-fake ncaa_game_ids (real NCAA ids are ~6-7 digits; the
# 90909xxxx range won't collide). home_team is the side listed first in the
# fixture title, matching the extract_odds home/away convention.
GAMES = [
    {
        "fixture": "fifwc-par-fra-2026-07-04.json",
        "ncaa_game_id": 909090704,
        "home_team": "Paraguay",
        "away_team": "France",
        "kickoff": "2026-07-04T21:00:00Z",  # fixture endDate (match time)
    },
    {
        "fixture": "fifwc-bra-mar-2026-06-13.json",
        "ncaa_game_id": 909090613,
        "home_team": "Brazil",
        "away_team": "Morocco",
        "kickoff": "2026-06-13T21:00:00Z",
    },
]


# --- safety ------------------------------------------------------------------
def _mask(dsn: str) -> str:
    """Return the DSN with any password replaced by '***'."""
    parts = urlsplit(dsn)
    if parts.password:
        netloc = parts.netloc.replace(f":{parts.password}@", ":***@")
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    return dsn


def assert_local_dsn(dsn: str) -> str:
    """Return the host if the DSN is a known-local target; raise SystemExit
    otherwise. This is the structural guarantee that we never touch prod."""
    low = dsn.lower()
    for bad in _BLOCKED_SUBSTRINGS:
        if bad in low:
            raise SystemExit(
                f"REFUSING: DSN references a non-local/prod host ({bad!r}). "
                f"This script only writes to the local compose Postgres."
            )
    host = (urlsplit(dsn).hostname or "").lower()
    if host not in _ALLOWED_HOSTS:
        raise SystemExit(
            f"REFUSING: DSN host {host!r} is not in the local allowlist "
            f"{sorted(_ALLOWED_HOSTS)}. Point --database-url at the local "
            f"compose DB (e.g. {_DEFAULT_LOCAL_DSN})."
        )
    return host


# --- odds parsing (offline) --------------------------------------------------
def _load_event(fixture: str) -> dict:
    """Gamma /events fixtures are a JSON list holding one event object."""
    return json.loads((_FIXTURES / fixture).read_text())[0]


def parse_offline_odds(event: dict, home_team: str, away_team: str) -> dict | None:
    """Run extract_odds against a fixture with CLOB disabled, so only the
    committed outcomePrices are used — deterministic and network-free."""
    original = polymarket.clob_midpoint
    polymarket.clob_midpoint = lambda token, timeout: None  # force cached path
    try:
        return polymarket.extract_odds(event, home_team, away_team, timeout=5)
    finally:
        polymarket.clob_midpoint = original


def build_reference_panels(odds: dict | None) -> dict:
    """Layer-6 panel for a World Cup game: no CFB XGBoost model, no vegas O/U,
    the full 3-way Polymarket odds (incl. market_type + draw_prob, which the
    get_latest_polymarket_odds helper would otherwise strip)."""
    return {"model": None, "vegas": {"over_under": None}, "polymarket": odds}


# --- predictions writer (no writer exists in db.py; all cols nullable) -------
_UPSERT_PREDICTION = """
    INSERT INTO predictions (
        ncaa_game_id, season, week, game_date, home_team, away_team,
        neutral_site, prediction_made_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, now())
    ON CONFLICT (ncaa_game_id) DO UPDATE SET
        season       = EXCLUDED.season,
        game_date    = EXCLUDED.game_date,
        home_team    = EXCLUDED.home_team,
        away_team    = EXCLUDED.away_team,
        neutral_site = EXCLUDED.neutral_site
"""


def seed_game(conn, game: dict, *, apply: bool) -> None:
    event = _load_event(game["fixture"])
    home, away = game["home_team"], game["away_team"]
    ncaa_game_id = game["ncaa_game_id"]
    kickoff = datetime.fromisoformat(game["kickoff"].replace("Z", "+00:00"))

    odds = parse_offline_odds(event, home, away)
    panels = build_reference_panels(odds)

    print(f"\n=== {home} vs {away}  (ncaa_game_id={ncaa_game_id}) ===")
    print(f"  fixture   : {game['fixture']}")
    print(f"  kickoff   : {kickoff.isoformat()}")
    if odds is None:
        print("  odds      : <none parsed> (fixture did not resolve to a market)")
    else:
        print(f"  odds      : type={odds.get('market_type')} "
              f"home={odds.get('home_win_prob')} draw={odds.get('draw_prob')} "
              f"away={odds.get('away_win_prob')}")
    print(f"  URL       : /matchup/{ncaa_game_id}")

    if not apply:
        print("  [dry-run] would upsert: teams x2, predictions x1, "
              "raw_signals(polymarket) x1, factor_decks x2")
        return

    # teams
    home_id = db.upsert_team(conn, home, conference="FIFA World Cup")
    away_id = db.upsert_team(conn, away, conference="FIFA World Cup")

    # predictions (synthetic, all-nullable, neutral site)
    conn.execute(
        _UPSERT_PREDICTION,
        (ncaa_game_id, 2026, None, kickoff, home, away, True),
    )

    # raw_signals provenance (idempotent on content_hash)
    if odds is not None:
        db.insert_raw_signal(
            conn,
            source_type="polymarket",
            payload=odds,
            as_of_timestamp=datetime.now(timezone.utc),
            published_at=None,
            source_name="Polymarket (seed_local fixture)",
            source_url=odds.get("source_url"),
            team_id=None,
            ncaa_game_id=ncaa_game_id,
        )

    # factor_decks: one per team, empty factors, shared reference panel
    for team_id in (home_id, away_id):
        db.upsert_factor_deck(
            conn,
            ncaa_game_id=ncaa_game_id,
            team_id=team_id,
            factors_view=[],
            reference_panels=panels,
            as_of_timestamp=kickoff,
        )
    print("  [applied] teams, predictions, raw_signal, factor_decks written")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--database-url", default=_DEFAULT_LOCAL_DSN,
                    help=f"local compose DSN (default: {_mask(_DEFAULT_LOCAL_DSN)})")
    ap.add_argument("--apply", action="store_true",
                    help="actually write (default is a dry-run plan)")
    ap.add_argument("--only", choices=[g["home_team"].lower() for g in GAMES],
                    help="seed only one game by home-team name")
    args = ap.parse_args()

    dsn = args.database_url
    host = assert_local_dsn(dsn)

    print("=" * 68)
    print("seed_local.py — LOCAL DEV ONLY")
    print(f"  resolved DSN : {_mask(dsn)}")
    print(f"  host         : {host}  (local allowlist OK)")
    print(f"  mode         : {'APPLY (writing)' if args.apply else 'DRY RUN (no writes)'}")
    print("=" * 68)

    games = GAMES if not args.only else [g for g in GAMES if g["home_team"].lower() == args.only]

    if not args.apply:
        for g in games:
            seed_game(None, g, apply=False)
        print("\nDry run complete. Re-run with --apply to write to the local DB.")
        return

    with db.connect(dsn) as conn:
        for g in games:
            seed_game(conn, g, apply=True)
    print("\nDone. Open the frontend and visit /matchup/<id> for each game above.")


if __name__ == "__main__":
    main()
