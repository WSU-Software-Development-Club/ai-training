"""Polymarket client — public, unauthenticated read endpoints. Layer-6
reference-panel INPUT only (implied win probability from a prediction market),
never a verdict — same status as the "vegas"/"model" keys already in
``db.get_model_reference_panel``.

Two APIs, mirroring the task split:
- Gamma API (gamma-api.polymarket.com): market DISCOVERY. No full-text search
  we can rely on for CFB, so we pull a date-windowed slice of markets and match
  team names locally against the market question.
- CLOB API (clob.polymarket.com): current PRICE for a matched market's outcome
  tokens (the midpoint of the live order book), which is fresher than Gamma's
  cached ``outcomePrices``. Falls back to ``outcomePrices`` if a CLOB call
  fails, so a flaky CLOB read degrades the price's freshness, not the result.

Coverage is genuinely sparse for CFB (Polymarket runs markets mostly for
marquee/playoff games) — a game with no market is the COMMON case, not an
error. Every public function returns ``None`` (never raises) when a market
can't be found or a network call ultimately fails, so callers can persist
"no data" as an explicit null rather than have a fetch failure kill the
pipeline run for the games that DO have markets. Mirrors sources/open_meteo.py
(requests, rate-limit + backoff/429 handling, returns plain dicts) except for
that not-raising rule, deliberately: weather is a required signal, Polymarket
is an optional one.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta
from typing import Optional

import requests

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
CLOB_MIDPOINT_URL = "https://clob.polymarket.com/midpoint"

# How many days around the game date to pull candidate markets from. Polymarket
# markets for a game are typically created days-to-weeks out and resolve
# shortly after kickoff, so a generous window costs nothing but a few extra
# rows to filter locally.
_DEFAULT_WINDOW_DAYS = 5
_PAGE_LIMIT = 200


def _get_with_retry(url: str, params: dict, timeout: int, max_retries: int = 3):
    """GET with polite rate-limiting + backoff (mirrors open_meteo's pattern).

    Unlike open_meteo, NEVER raises: Polymarket is an optional, sparse-coverage
    input, so a persistent transport failure degrades to ``None`` (explicit
    missingness) instead of aborting the caller.
    """
    for attempt in range(max_retries):
        try:
            time.sleep(0.2)  # be gentle on the public API
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429:
                time.sleep(30)
                continue
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            if attempt == max_retries - 1:
                return None
            time.sleep(2 ** attempt)
    return None


def _tokens(name: str) -> set[str]:
    return set(re.sub(r"[^a-z0-9 ]", " ", (name or "").lower()).split())


def _mentions_team(text: str, team: str) -> bool:
    """True if every word of ``team`` (e.g. {'ohio', 'state'}) appears in
    ``text``. A simple, dependency-free heuristic — good enough for a
    best-effort match against Polymarket's inconsistent question phrasing
    (school name vs. mascot); false negatives just mean 'no market found',
    which is already the expected common case."""
    team_tok = _tokens(team)
    if not team_tok:
        return False
    return team_tok.issubset(_tokens(text))


def _parse_json_field(value):
    """Gamma encodes list fields (outcomes, outcomePrices, clobTokenIds) as
    JSON strings, not native JSON arrays."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None
    return value


def _safe_float(value) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def search_markets(game_date: str, timeout: int, window_days: int = _DEFAULT_WINDOW_DAYS) -> list[dict]:
    """Candidate Gamma markets whose window overlaps ``game_date`` (ISO 8601).
    Returns ``[]`` (never None) on a bad date or an unreachable API — callers
    filtering this list handle an empty list identically to 'no match'."""
    try:
        d = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return []
    start = (d - timedelta(days=window_days)).date().isoformat()
    end = (d + timedelta(days=window_days)).date().isoformat()
    params = {
        "active": "true",
        "closed": "false",
        "start_date_min": start,
        "start_date_max": end,
        "limit": _PAGE_LIMIT,
    }
    data = _get_with_retry(GAMMA_MARKETS_URL, params, timeout)
    return data if isinstance(data, list) else []


def _match_market(candidates: list[dict], home_team: str, away_team: str) -> Optional[dict]:
    for market in candidates:
        question = market.get("question") or market.get("slug") or ""
        if _mentions_team(question, home_team) and _mentions_team(question, away_team):
            return market
    return None


def clob_midpoint(token_id: str, timeout: int) -> Optional[float]:
    """Current implied probability for one outcome token, from the live
    order-book midpoint. Read-only, no auth/API key required."""
    if not token_id:
        return None
    data = _get_with_retry(CLOB_MIDPOINT_URL, {"token_id": token_id}, timeout)
    if not isinstance(data, dict):
        return None
    return _safe_float(data.get("mid"))


def _market_to_odds(market: dict, home_team: str, away_team: str, timeout: int) -> Optional[dict]:
    outcomes = _parse_json_field(market.get("outcomes")) or []
    prices = _parse_json_field(market.get("outcomePrices")) or []
    token_ids = _parse_json_field(market.get("clobTokenIds")) or []

    if len(outcomes) != 2:
        return None  # only binary team-vs-team moneyline markets are supported

    def _idx_for(team: str) -> Optional[int]:
        for i, label in enumerate(outcomes):
            if _mentions_team(str(label), team):
                return i
        return None

    home_idx = _idx_for(home_team)
    away_idx = _idx_for(away_team)
    if home_idx is None or away_idx is None or home_idx == away_idx:
        return None

    def _price(i: int) -> Optional[float]:
        # Prefer a live CLOB midpoint; fall back to Gamma's (possibly stale
        # but always-present-if-priced) outcomePrices.
        token = token_ids[i] if i < len(token_ids) else None
        live = clob_midpoint(token, timeout) if token else None
        if live is not None:
            return live
        return _safe_float(prices[i]) if i < len(prices) else None

    return {
        "market_id": str(market["id"]) if market.get("id") is not None else None,
        "question": market.get("question"),
        "slug": market.get("slug"),
        "home_team": home_team,
        "away_team": away_team,
        "home_win_prob": _price(home_idx),
        "away_win_prob": _price(away_idx),
        "volume": _safe_float(market.get("volume")),
        "liquidity": _safe_float(market.get("liquidity")),
        "end_date": market.get("endDate"),
        "closed": bool(market.get("closed")) if market.get("closed") is not None else None,
        "source_url": f"https://polymarket.com/event/{market['slug']}" if market.get("slug") else None,
    }


def find_game_market(home_team: str, away_team: str, game_date: str, timeout: int = 30) -> Optional[dict]:
    """Discover + price a CFB game's Polymarket market, if one exists.

    Returns ``None`` when there's no matching market (the common CFB case) —
    NOT an error. On a match, returns implied win probabilities:
        {market_id, question, slug, home_team, home_win_prob, away_team,
         away_win_prob, volume, liquidity, end_date, closed, source_url}
    ``*_win_prob`` values are themselves independently nullable (e.g. CLOB and
    Gamma both failed to price one side) — always None-check before use.
    """
    candidates = search_markets(game_date, timeout)
    market = _match_market(candidates, home_team, away_team)
    if market is None:
        return None
    return _market_to_odds(market, home_team, away_team, timeout)


def fetch_game_odds(home_team: str, away_team: str, game_date: str, timeout: int = 30) -> Optional[dict]:
    """Public entrypoint. Wraps ``find_game_market`` with a blanket try/except
    so ANY unexpected failure (bad payload shape, etc.) also degrades to
    ``None`` rather than propagating — callers must treat None as "no data",
    never as an error to retry/alert on."""
    try:
        return find_game_market(home_team, away_team, game_date, timeout=timeout)
    except Exception:
        return None
