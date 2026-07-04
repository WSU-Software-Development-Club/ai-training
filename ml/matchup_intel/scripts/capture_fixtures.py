"""Capture real Polymarket Gamma API responses as test fixtures.

The CFB season is dormant, so the live FIFA World Cup on Polymarket is our
dev data: it exercises the same Gamma endpoints (``sources/polymarket.py``)
with rich, real payloads — including 3-way soccer moneyline markets
(Team / Draw / Team), which CFB never has.

Each retained response object is written verbatim — no field is parsed or
rewritten. The one non-verbatim step is *list subsetting*: the World Cup tag
also contains huge futures/props events (e.g. "Player to score" with 150+
nested markets → tens of MB), so the market-list capture keeps only the base
3-way moneyline *game* events (each byte-for-byte unchanged) and drops the
futures/props events wholesale. The per-game detail files are fully verbatim.

Two shapes are captured, both from the Gamma API (gamma-api.polymarket.com):

1. The World Cup *market list* — the base moneyline game events under the
   ``fifa-world-cup`` tag, collected across all pages and filtered by slug
   shape (``fifwc-XXX-YYY-YYYY-MM-DD`` with no ``-player-props`` / ``-exact-
   score`` / ``-more-markets`` / etc. suffix). Saved as ``world-cup-events.json``.
   Only currently-open (``closed=false``) games appear, so this tracks the
   live slate (knockout games at capture time; group games already resolved).
2. Full *market detail* for a handful of specific games — each fetched by its
   event slug via ``/events?slug=<slug>``. A game event nests its outcome
   markets (moneyline W/D/L, plus the outcome tokens/prices), so this is the
   full detail for one matchup. Saved one file per slug (``<slug>.json``).

Run:  python -m ml.matchup_intel.scripts.capture_fixtures
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import requests

GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"

# tests/fixtures/ lives one level up from this scripts/ dir.
FIXTURES_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"

# Base moneyline game slug: fifwc-<home>-<away>-YYYY-MM-DD, no suffix. The
# suffixed variants (-player-props, -exact-score, -halftime-result,
# -more-markets, -first-to-score) are the bulky derivative markets we skip.
GAME_SLUG_RE = re.compile(r"^fifwc-[a-z]{3}-[a-z]{3}-\d{4}-\d{2}-\d{2}$")

# The World Cup market-list capture: page through the tag's open events and
# keep only the base moneyline games (see module docstring). One generous
# page size; stop when a page comes back empty.
WORLD_CUP_TAG = "fifa-world-cup"
LIST_PAGE_SIZE = 100
LIST_MAX_PAGES = 20

# Specific game events to snapshot in full. par-fra is the requested 3-way
# knockout game; the other two are group-stage games with 3-outcome markets.
GAME_SLUGS = [
    "fifwc-par-fra-2026-07-04",  # Paraguay vs. France (requested)
    "fifwc-fra-sen-2026-06-16",  # France vs. Senegal
    "fifwc-bra-mar-2026-06-13",  # Brazil vs. Morocco
]

TIMEOUT = 30


def _get(params: dict):
    """Plain GET → parsed JSON. Raises on transport/HTTP errors so a bad
    capture is loud (this is a dev tool, not the pipeline's degrade-to-None
    path)."""
    resp = requests.get(GAMMA_EVENTS_URL, params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _collect_game_events() -> list:
    """Page through the World Cup tag and return the base moneyline game
    events verbatim (each event object untouched; non-game events dropped)."""
    games: list = []
    for page in range(LIST_MAX_PAGES):
        batch = _get(
            {
                "tag_slug": WORLD_CUP_TAG,
                "closed": "false",
                "limit": LIST_PAGE_SIZE,
                "offset": page * LIST_PAGE_SIZE,
                "order": "startDate",
                "ascending": "true",
            }
        )
        if not batch:
            break
        games.extend(e for e in batch if GAME_SLUG_RE.match(e.get("slug") or ""))
    return games


def _save(name: str, payload) -> Path:
    path = FIXTURES_DIR / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    return path


def main() -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    # 1) World Cup market list (base moneyline games only).
    events = _collect_game_events()
    path = _save("world-cup-events", events)
    print(f"[list]  {path.name:40s} ({len(events)} moneyline games)")

    # 2) Full detail per game (fetched by event slug).
    for slug in GAME_SLUGS:
        detail = _get({"slug": slug})
        path = _save(slug, detail)
        # /events?slug= returns a list of matching events (0 or 1).
        if isinstance(detail, list) and detail:
            n_markets = len(detail[0].get("markets", []))
            print(f"[game]  {path.name:40s} ({n_markets} markets)")
        else:
            print(f"[game]  {path.name:40s} (EMPTY — slug not found)")


if __name__ == "__main__":
    main()
