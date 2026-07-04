#!/usr/bin/env python3
"""Manual LIVE check of the Polymarket path — hits the real Gamma + CLOB APIs.

Unlike ``seed_local.py`` (which parses committed fixtures OFFLINE with CLOB
neutralized), this makes genuine network calls so you can watch current odds
come back through the exact production chain:

    fetch_game_odds -> find_game_market -> search_markets (/markets + /events)
                    -> _match_market -> extract_odds -> clob_midpoint (live CLOB)

Read-only, no auth/API key, no DB writes. Honours the module's never-raise
contract: if there's no market (the common case) it prints "no market", never
an error.

Usage:
    python -m scripts.check_polymarket_live                 # default WC matchup
    python scripts/check_polymarket_live.py "Paraguay" "France" 2026-07-04
    python scripts/check_polymarket_live.py "Ohio State" "Michigan" 2025-11-29

Args (all optional, positional): HOME AWAY GAME_DATE(ISO 8601).

Egress goes to gamma-api.polymarket.com / clob.polymarket.com over the open
internet — if your host blocks that, expect "no market".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# --- import the matchup pipeline package from the repo root ------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml.matchup_intel.sources import polymarket  # noqa: E402

# An UPCOMING FIFA World Cup game with an open market — a moving target: once a
# game kicks off and resolves, Polymarket closes its market and this default
# starts returning "no market" (the never-raise path). Point it at the next
# upcoming matchup via CLI args when that happens.
_DEFAULT = ("Brazil", "Norway", "2026-07-05")


def _parse_json_field(value):
    # mirror the module helper without reaching into a private name
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
    return value


def _prove_live_clob(market: dict, timeout: int) -> None:
    """Make ONE direct clob_midpoint call on a matched leg's token so a fresh
    order-book price is visibly hit — this is the part seed_local neutralizes."""
    submarkets = market.get("markets") if isinstance(market, dict) else None
    holder = (submarkets[0] if isinstance(submarkets, list) and submarkets else market)
    token_ids = _parse_json_field(holder.get("clobTokenIds")) or []
    token = token_ids[0] if token_ids else None
    if not token:
        print("  live CLOB   : (no clobTokenIds on the matched market to probe)")
        return
    mid = polymarket.clob_midpoint(token, timeout)
    if mid is None:
        print(f"  live CLOB   : token {token[:12]}… -> None "
              "(order book unpriced / CLOB unreachable; Gamma cache used instead)")
    else:
        print(f"  live CLOB   : token {token[:12]}… -> mid={mid}  (fresh order-book price)")


def main() -> int:
    args = sys.argv[1:]
    if args and args[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    # Fill any missing positional args from the default matchup.
    merged = args + list(_DEFAULT)[len(args):]
    home, away, game_date = merged[0], merged[1], merged[2]

    timeout = 30
    print(f"=== LIVE Polymarket check ===")
    print(f"  matchup     : {home} vs {away}")
    print(f"  game_date   : {game_date}")
    print(f"  gamma       : {polymarket.GAMMA_MARKETS_URL} + {polymarket.GAMMA_EVENTS_URL}")
    print(f"  clob        : {polymarket.CLOB_MIDPOINT_URL}")
    print("  (hitting the live APIs — first CLOB read may take a moment)\n")

    # 1) Show discovery actually finds the event via the combined, paged
    #    /markets+/events walk — stopping at the first candidate that mentions
    #    both teams (exactly what find_game_market does internally).
    match = None
    scanned = 0
    for candidate in polymarket.iter_candidates(game_date, timeout):
        scanned += 1
        if polymarket._match_market([candidate], home, away) is not None:
            match = candidate
            break
    print(f"  scanned     : {scanned} market(s)/event(s) before "
          f"{'matching' if match else 'exhausting the window'}")
    if match is None:
        print(f"  matched     : <none> — no market mentions both '{home}' and '{away}'")
        print("\n  => no market (expected for most games). Nothing to price.")
        return 0
    print(f"  matched     : slug={match.get('slug')} "
          f"title={match.get('title') or match.get('question')!r}")

    # 2) Prove the live CLOB leg is really hit (the bit seed_local neutralizes).
    _prove_live_clob(match, timeout)

    # 3) Full production entrypoint — this is what the pipeline persists.
    odds = polymarket.fetch_game_odds(home, away, game_date, timeout=timeout)
    print()
    if odds is None:
        print("  fetch_game_odds -> None (never raises; treat as 'no data')")
        return 0
    print("  fetch_game_odds -> live odds:")
    print(json.dumps(odds, indent=2, sort_keys=True))
    mt = odds.get("market_type")
    if mt == "3way":
        print(f"\n  implied: home={odds.get('home_win_prob')} "
              f"draw={odds.get('draw_prob')} away={odds.get('away_win_prob')}")
    else:
        print(f"\n  implied: home={odds.get('home_win_prob')} "
              f"away={odds.get('away_win_prob')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
