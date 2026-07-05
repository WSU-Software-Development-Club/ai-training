"""Polymarket client: sparse-coverage CFB odds lookup. No real network calls —
requests/CLOB calls are monkeypatched so these run anywhere `requests` is
installed, matching the rest of this test suite's "pure" style."""

from __future__ import annotations

import json

from ml.matchup_intel.sources import polymarket


def _gamma_market(**overrides) -> dict:
    data = dict(
        id=12345,
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


# --- team-name matching ------------------------------------------------------

def test_mentions_team_matches_full_school_name():
    assert polymarket._mentions_team("Ohio State vs. Michigan", "Ohio State")


def test_mentions_team_false_when_only_partial_match():
    assert not polymarket._mentions_team("Michigan vs. Michigan State", "Ohio State")


def test_mentions_team_false_on_empty_team():
    assert not polymarket._mentions_team("Ohio State vs. Michigan", "")


# --- market matching ----------------------------------------------------------

def test_match_market_finds_game_among_candidates():
    candidates = [
        _gamma_market(question="Georgia vs. Alabama: Who wins?"),
        _gamma_market(question="Ohio State vs. Michigan: Who wins?"),
    ]
    match = polymarket._match_market(candidates, "Ohio State", "Michigan")
    assert match is not None
    assert match["slug"] == "ohio-state-vs-michigan"


def test_match_market_none_when_no_candidate_mentions_both_teams():
    candidates = [_gamma_market(question="Georgia vs. Alabama: Who wins?")]
    assert polymarket._match_market(candidates, "Ohio State", "Michigan") is None


def test_match_market_none_on_empty_candidates():
    assert polymarket._match_market([], "Ohio State", "Michigan") is None


# --- odds extraction -----------------------------------------------------------

def test_market_to_odds_uses_clob_midpoint_when_available(monkeypatch):
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: {
        "tok-home": 0.65, "tok-away": 0.35,
    }.get(token))
    odds = polymarket._market_to_odds(_gamma_market(), "Ohio State", "Michigan", timeout=5)
    assert odds is not None
    assert odds["home_win_prob"] == 0.65
    assert odds["away_win_prob"] == 0.35
    assert odds["market_id"] == "12345"
    assert odds["source_url"] == "https://polymarket.com/event/ohio-state-vs-michigan"


def test_market_to_odds_falls_back_to_gamma_prices_when_clob_fails(monkeypatch):
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    odds = polymarket._market_to_odds(_gamma_market(), "Ohio State", "Michigan", timeout=5)
    assert odds is not None
    assert odds["home_win_prob"] == 0.62
    assert odds["away_win_prob"] == 0.38


def test_market_to_odds_none_when_not_binary():
    market = _gamma_market(outcomes=json.dumps(["Ohio State", "Michigan", "Tie"]))
    assert polymarket._market_to_odds(market, "Ohio State", "Michigan", timeout=5) is None


def test_market_to_odds_none_when_team_not_in_outcomes(monkeypatch):
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    market = _gamma_market(outcomes=json.dumps(["Georgia", "Alabama"]))
    assert polymarket._market_to_odds(market, "Ohio State", "Michigan", timeout=5) is None


# --- top-level entrypoints: explicit-missingness (never raise) ----------------

def test_find_game_market_none_when_no_candidates(monkeypatch):
    monkeypatch.setattr(polymarket, "search_markets", lambda game_date, timeout: [])
    assert polymarket.find_game_market("Ohio State", "Michigan", "2024-11-30") is None


def test_find_game_market_returns_odds_on_match(monkeypatch):
    monkeypatch.setattr(polymarket, "search_markets",
                         lambda game_date, timeout: [_gamma_market()])
    monkeypatch.setattr(polymarket, "clob_midpoint", lambda token, timeout: None)
    odds = polymarket.find_game_market("Ohio State", "Michigan", "2024-11-30")
    assert odds is not None
    assert odds["home_win_prob"] == 0.62


def test_fetch_game_odds_swallows_any_exception(monkeypatch):
    def _boom(*a, **kw):
        raise RuntimeError("unexpected shape")

    monkeypatch.setattr(polymarket, "find_game_market", _boom)
    assert polymarket.fetch_game_odds("Ohio State", "Michigan", "2024-11-30") is None


def test_search_markets_empty_on_bad_date():
    assert polymarket.search_markets("not-a-date", timeout=5) == []


def test_get_with_retry_degrades_to_none_on_persistent_failure(monkeypatch):
    import requests

    def _raise(*a, **kw):
        raise requests.ConnectionError("no route to host")

    monkeypatch.setattr(polymarket.requests, "get", _raise)
    monkeypatch.setattr(polymarket.time, "sleep", lambda *_: None)  # skip real backoff
    assert polymarket._get_with_retry("https://example.invalid", {}, timeout=1) is None


# --- historical price curve (past/resolved games) -----------------------------

def test_pick_moneyline_skips_spread_and_total_markets():
    markets = [
        {"question": "Spread: Michigan (-9.5)",
         "outcomes": json.dumps(["Ohio State", "Michigan"])},
        {"question": "Ohio State vs. Michigan: O/U 51.5",
         "outcomes": json.dumps(["Over", "Under"])},
        {"question": "Ohio State Buckeyes vs. Michigan",
         "outcomes": json.dumps(["Ohio State Buckeyes", "Michigan"]),
         "clobTokenIds": json.dumps(["tok-home", "tok-away"])},
    ]
    ml = polymarket._pick_moneyline(markets, "Ohio State", "Michigan")
    assert ml is not None
    assert ml["question"] == "Ohio State Buckeyes vs. Michigan"


def test_pick_moneyline_none_when_only_derivative_markets():
    markets = [{"question": "Spread: Michigan (-9.5)",
                "outcomes": json.dumps(["Ohio State", "Michigan"])}]
    assert polymarket._pick_moneyline(markets, "Ohio State", "Michigan") is None


def test_fetch_price_history_windowed(monkeypatch):
    captured = {}

    def _fake_get(url, params, timeout, max_retries=3):
        captured["url"] = url
        captured["params"] = params
        return {"history": [{"t": 100, "p": 0.6}, {"t": 200, "p": None},
                            {"t": 300, "p": 0.9}]}

    monkeypatch.setattr(polymarket, "_get_with_retry", _fake_get)
    out = polymarket.fetch_price_history("tok-home", 1000, 2000, timeout=5, fidelity=1)
    # fidelity is floored to the CLOB minimum, and a null price point is dropped.
    assert captured["params"]["fidelity"] == polymarket._MIN_FIDELITY
    assert captured["params"]["startTs"] == 1000
    assert out == [{"t": 100, "p": 0.6}, {"t": 300, "p": 0.9}]


def test_find_game_price_history_builds_binary_curve(monkeypatch):
    event = {
        "title": "Coastal Carolina Chanticleers vs. Louisiana Tech",
        "slug": "cfb-coast-loutch-2025-12-30",
        "startDate": "2025-12-30T19:00:00Z",
        "markets": [
            {"id": 999, "question": "Coastal Carolina Chanticleers vs. Louisiana Tech",
             "outcomes": json.dumps(["Coastal Carolina Chanticleers", "Louisiana Tech"]),
             "clobTokenIds": json.dumps(["tok-away", "tok-home"])},
        ],
    }
    monkeypatch.setattr(polymarket, "_search_event", lambda h, a, d, t: event)

    kickoff = 1767121200  # 2025-12-30T19:00:00Z
    game_pt = kickoff + 1800          # in the dense game window
    pregame_pt = kickoff - 2 * 86400  # days before, from the coarse context fetch

    # The function fetches twice: a DENSE per-minute game window (fidelity 1) and
    # a COARSE hourly context (fidelity 60). Model each returning its own points.
    def _fake_history(token, s, e, timeout, fidelity):
        if token != "tok-home":
            return None
        return [{"t": pregame_pt, "p": 0.60}] if fidelity == 60 else [{"t": game_pt, "p": 0.72}]

    monkeypatch.setattr(polymarket, "fetch_price_history", _fake_history)
    res = polymarket.find_game_price_history(
        "Louisiana Tech", "Coastal Carolina", "2025-12-30T19:00:00+00:00")
    assert res is not None
    assert res["slug"] == "cfb-coast-loutch-2025-12-30"
    assert res["source_url"].endswith("cfb-coast-loutch-2025-12-30")
    # Merged: the coarse pre-game point (outside the window) + the dense game point.
    assert len(res["points"]) == 2
    # Sorted ascending: pre-game first, then the game point; away = 1 - home.
    assert res["points"][0]["home_win_prob"] == 0.60
    assert res["points"][1]["home_win_prob"] == 0.72
    assert res["points"][1]["away_win_prob"] == 0.28


def test_find_game_price_history_drops_coarse_points_inside_game_window(monkeypatch):
    """A coarse-context point that falls INSIDE the dense game window is dropped,
    so the per-minute series is the single source of truth there (no duplicates)."""
    event = {
        "title": "Coastal Carolina Chanticleers vs. Louisiana Tech",
        "slug": "cfb-coast-loutch-2025-12-30",
        "startDate": "2025-12-30T19:00:00Z",
        "markets": [
            {"id": 999, "question": "Coastal Carolina Chanticleers vs. Louisiana Tech",
             "outcomes": json.dumps(["Coastal Carolina Chanticleers", "Louisiana Tech"]),
             "clobTokenIds": json.dumps(["tok-away", "tok-home"])},
        ],
    }
    monkeypatch.setattr(polymarket, "_search_event", lambda h, a, d, t: event)
    kickoff = 1767121200
    in_window = kickoff + 1800

    def _fake_history(token, s, e, timeout, fidelity):
        # Both fetches return a point inside the game window; the coarse one must
        # be discarded in favor of the dense one.
        return [{"t": in_window, "p": 0.72 if fidelity != 60 else 0.70}]

    monkeypatch.setattr(polymarket, "fetch_price_history", _fake_history)
    res = polymarket.find_game_price_history(
        "Louisiana Tech", "Coastal Carolina", "2025-12-30T19:00:00+00:00")
    assert len(res["points"]) == 1
    assert res["points"][0]["home_win_prob"] == 0.72  # dense wins


def test_fetch_game_price_history_swallows_any_exception(monkeypatch):
    def _boom(*a, **kw):
        raise RuntimeError("bad payload")

    monkeypatch.setattr(polymarket, "find_game_price_history", _boom)
    assert polymarket.fetch_game_price_history(
        "Louisiana Tech", "Coastal Carolina", "2025-12-30") is None
