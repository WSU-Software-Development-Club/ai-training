"""Polymarket 2-way vs 3-way market handling, driven entirely by captured
Gamma fixtures — NO live network calls (CLOB is monkeypatched off so the
Gamma-cached ``outcomePrices`` path is exercised deterministically).

Fixtures under tests/fixtures/:
- ``cfb-byu-col-2025-09-27.json`` — a REAL, archived CFB moneyline event
  captured from Gamma (`/events?slug=cfb-byu-col-2025-09-27`). Single market,
  two team-name outcomes, ``negRisk: false``. Resolved, so its outcomePrices
  are the degenerate 1/0 of a settled market — which is exactly what makes it a
  faithful 2-way structural fixture. (Live fractional 2-way pricing is already
  covered by the synthetic flat-market test below and in test_polymarket.py.)
- ``fifwc-par-fra-2026-07-04.json`` — a REAL 3-way World Cup neg-risk event:
  three linked Yes/No submarkets (home win / draw / away win).

These tests are written test-first against the NOT-YET-IMPLEMENTED
``polymarket.extract_odds`` dispatcher; they are expected to fail until the
3-way support lands.
"""

from __future__ import annotations

import json
from pathlib import Path

from ml.matchup_intel.sources import polymarket

FIXTURES = Path(__file__).parent / "fixtures"


def _load_event(name: str) -> dict:
    """Gamma `/events` fixtures are a JSON list of event objects; the
    single-game ones hold exactly one event."""
    return json.loads((FIXTURES / name).read_text())[0]


def _flat_two_way_market(**overrides) -> dict:
    """A flat Gamma `/markets`-shaped 2-way moneyline (the existing code path),
    with live-ish fractional prices."""
    data = dict(
        id=99001,
        question="Ohio State vs. Michigan: Who wins?",
        slug="ohio-state-vs-michigan",
        outcomes=json.dumps(["Ohio State", "Michigan"]),
        outcomePrices=json.dumps(["0.62", "0.38"]),
        clobTokenIds=json.dumps(["tok-home", "tok-away"]),
        volume="150000",
        liquidity="20000",
        endDate="2024-11-30T00:00:00Z",
        closed=False,
    )
    data.update(overrides)
    return data


# --- 2-way: existing flat-market path must be untouched ----------------------

def test_extract_odds_two_way_flat_market_unchanged(monkeypatch):
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    odds = polymarket.extract_odds(_flat_two_way_market(), "Ohio State", "Michigan", timeout=5)
    assert odds is not None
    assert odds["market_type"] == "2way"
    assert odds["home_win_prob"] == 0.62
    assert odds["away_win_prob"] == 0.38
    assert "draw_prob" not in odds  # 2-way markets have no draw


def test_extract_odds_two_way_real_archived_event(monkeypatch):
    """The real BYU vs. Colorado event: a single 2-team market wrapped in an
    event envelope. Resolves to home/away exactly like the flat path."""
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    event = _load_event("cfb-byu-col-2025-09-27.json")
    odds = polymarket.extract_odds(event, "BYU", "Colorado", timeout=5)
    assert odds is not None
    assert odds["market_type"] == "2way"
    assert odds["home_win_prob"] == 1.0   # BYU (settled winner)
    assert odds["away_win_prob"] == 0.0   # Colorado
    assert odds["home_team"] == "BYU"
    assert odds["away_team"] == "Colorado"


# --- 3-way: World Cup neg-risk home/draw/away --------------------------------

def test_extract_odds_three_way_resolves_home_draw_away(monkeypatch):
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    event = _load_event("fifwc-par-fra-2026-07-04.json")
    odds = polymarket.extract_odds(event, "Paraguay", "France", timeout=5)
    assert odds is not None
    assert odds["market_type"] == "3way"
    # Yes-price of each linked binary submarket = that outcome's implied prob.
    assert odds["home_win_prob"] == 0.045   # "Will Paraguay win?"
    assert odds["draw_prob"] == 0.135       # "...end in a draw?"
    assert odds["away_win_prob"] == 0.815   # "Will France win?"
    assert odds["home_team"] == "Paraguay"
    assert odds["away_team"] == "France"
    assert odds["slug"] == "fifwc-par-fra-2026-07-04"
    assert odds["source_url"] == "https://polymarket.com/event/fifwc-par-fra-2026-07-04"


def test_three_way_draw_leg_not_misclassified_as_a_team(monkeypatch):
    """The draw submarket's title ("Draw (Paraguay vs. France)") mentions BOTH
    team names — it must map to draw, never to a team leg."""
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    event = _load_event("fifwc-par-fra-2026-07-04.json")
    odds = polymarket.extract_odds(event, "Paraguay", "France", timeout=5)
    assert odds["home_win_prob"] == 0.045   # NOT the draw's 0.135
    assert odds["draw_prob"] == 0.135


def test_extract_odds_three_way_prefers_clob_midpoint(monkeypatch):
    """Live CLOB midpoint (of each leg's Yes token) wins over Gamma's cached
    outcomePrices, mirroring the 2-way behaviour."""
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: 0.5)
    event = _load_event("fifwc-par-fra-2026-07-04.json")
    odds = polymarket.extract_odds(event, "Paraguay", "France", timeout=5)
    assert odds["home_win_prob"] == 0.5
    assert odds["draw_prob"] == 0.5
    assert odds["away_win_prob"] == 0.5


def test_extract_odds_three_way_missing_draw_leg_returns_none(monkeypatch):
    """A malformed event that isn't a clean 3-way (draw leg dropped) and isn't a
    single flat 2-way market resolves to None — explicit missingness, no raise."""
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    event = _load_event("fifwc-par-fra-2026-07-04.json")
    event["markets"] = [
        m for m in event["markets"] if "draw" not in (m.get("question") or "").lower()
    ]
    assert polymarket.extract_odds(event, "Paraguay", "France", timeout=5) is None


def test_three_way_ambiguous_leg_returns_none(monkeypatch):
    """Misclassification safety: if a leg's text matches BOTH teams (and isn't a
    draw), it is genuinely ambiguous — the classifier must yield None rather
    than silently assign it to home or away. Wrong odds are worse than no odds."""
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    event = _load_event("fifwc-par-fra-2026-07-04.json")
    for m in event["markets"]:
        # Corrupt the France leg into an ambiguous one mentioning both teams,
        # with no draw marker and no disambiguating metadata.
        if m.get("groupItemTitle") == "France":
            m["groupItemTitle"] = "Paraguay vs. France"
            m["question"] = "Who advances between Paraguay and France?"
            m["marketMetadata"] = {}
    assert polymarket._classify_three_way(event["markets"], "Paraguay", "France") is None
    assert polymarket.extract_odds(event, "Paraguay", "France", timeout=5) is None


def test_three_way_unclassifiable_leg_returns_none(monkeypatch):
    """A leg mentioning NEITHER team and not a draw is also unclassifiable."""
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    event = _load_event("fifwc-par-fra-2026-07-04.json")
    for m in event["markets"]:
        if m.get("groupItemTitle") == "France":
            m["groupItemTitle"] = "Will the favorite advance?"
            m["question"] = "Will the favorite advance on 2026-07-04?"
            m["marketMetadata"] = {}
    assert polymarket._classify_three_way(event["markets"], "Paraguay", "France") is None


# --- discovery + matching over the event shape -------------------------------

def test_match_market_matches_event_by_title():
    event = _load_event("fifwc-par-fra-2026-07-04.json")
    match = polymarket._match_market([event], "Paraguay", "France")
    assert match is not None
    assert match["slug"] == "fifwc-par-fra-2026-07-04"


def test_find_game_market_three_way_end_to_end(monkeypatch):
    """Discovery → match → dispatch, with search_markets stubbed to return the
    captured event (no live call)."""
    event = _load_event("fifwc-par-fra-2026-07-04.json")
    monkeypatch.setattr(polymarket, "iter_candidates", lambda game_date, timeout: [event])
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    odds = polymarket.find_game_market("Paraguay", "France", "2026-07-04")
    assert odds is not None
    assert odds["market_type"] == "3way"
    assert odds["away_win_prob"] == 0.815


# --- discovery via the real /events query (HTTP boundary stubbed) -------------

def _load_events(name: str) -> list:
    """The full multi-event Gamma `/events` list fixture."""
    return json.loads((FIXTURES / name).read_text())


def _route_get(markets_result, events_result):
    """Build a `_get_with_retry` replacement that answers per Gamma endpoint —
    lets us exercise the REAL search_markets (which now fans out to both
    /markets and /events) without any live network call."""
    def _get(url, params, timeout, max_retries=3):
        if url == polymarket.GAMMA_MARKETS_URL:
            return markets_result
        if url == polymarket.GAMMA_EVENTS_URL:
            return events_result
        raise AssertionError(f"unexpected Gamma URL: {url}")
    return _get


def test_search_markets_includes_events_slice(monkeypatch):
    """search_markets must fan out to /events, not just /markets, so 3-way
    neg-risk events become discoverable candidates."""
    events = _load_events("world-cup-events.json")
    monkeypatch.setattr(polymarket, "_get_with_retry", _route_get([], events))
    candidates = polymarket.search_markets("2026-07-04", timeout=5)
    slugs = {c.get("slug") for c in candidates}
    assert "fifwc-par-fra-2026-07-04" in slugs


def test_find_game_market_discovers_world_cup_event_via_events(monkeypatch):
    """End-to-end through the REAL discovery: no /markets hit for the game, the
    event is found only via the /events slice, then priced. Proves the /events
    discovery path (not just extract_odds) resolves a live World Cup event."""
    events = _load_events("world-cup-events.json")
    monkeypatch.setattr(polymarket, "_get_with_retry", _route_get([], events))
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    odds = polymarket.find_game_market("Paraguay", "France", "2026-07-04")
    assert odds is not None
    assert odds["market_type"] == "3way"
    assert odds["slug"] == "fifwc-par-fra-2026-07-04"
    # Cached outcomePrices from the full /events list fixture (captured slightly
    # later than the single-game fixture, hence 0.055 vs 0.045 home).
    assert odds["home_win_prob"] == 0.055
    assert odds["draw_prob"] == 0.135
    assert odds["away_win_prob"] == 0.815


def test_find_game_market_events_endpoint_failure_degrades_to_none(monkeypatch):
    """If BOTH Gamma slices come back empty/unreachable, discovery yields no
    candidate and the never-raise contract holds → None, not an exception."""
    monkeypatch.setattr(polymarket, "_get_with_retry", _route_get(None, None))
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    assert polymarket.find_game_market("Paraguay", "France", "2026-07-04") is None
