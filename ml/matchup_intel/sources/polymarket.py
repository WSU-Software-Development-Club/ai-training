"""Polymarket client — public, unauthenticated read endpoints. Layer-6
reference-panel INPUT only (implied win probability from a prediction market),
never a verdict — same status as the "vegas"/"model" keys already in
``db.get_model_reference_panel``.

Two APIs, mirroring the task split:
- Gamma API (gamma-api.polymarket.com): market DISCOVERY. No full-text search
  we can rely on for CFB, so we pull a date-windowed slice of both `/markets`
  (flat 2-way moneylines) and `/events` (event envelopes, incl. 3-way neg-risk
  soccer events) and match team names locally against the market question/title.
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
GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"
CLOB_MIDPOINT_URL = "https://clob.polymarket.com/midpoint"

# How many days around the game date to pull candidate markets from. Polymarket
# markets for a game are typically created days-to-weeks out and resolve
# shortly after kickoff, so a generous window costs nothing but a few extra
# rows to filter locally.
_DEFAULT_WINDOW_DAYS = 5
# Gamma caps a `/events` page at 100 rows regardless of a larger ``limit``; use
# that as the page size for both endpoints and walk the window with ``offset``.
# A busy window (e.g. a World Cup slate mixed with earnings/crypto markets) runs
# to several hundred rows, and the target game's event can sit on the 2nd-3rd
# page — a single page silently misses it. ``_MAX_PAGES`` bounds the walk so a
# no-market game (the common CFB case) can't page forever; discovery early-exits
# the moment it matches, so a game that DOES have a market rarely pays the cap.
_PAGE_LIMIT = 100
_MAX_PAGES = 10


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


def _window_params(game_date: str, window_days: int) -> Optional[dict]:
    """Shared date-window query params for both Gamma endpoints, or None on a
    bad date (callers translate None → ``[]``)."""
    try:
        d = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    start = (d - timedelta(days=window_days)).date().isoformat()
    end = (d + timedelta(days=window_days)).date().isoformat()
    return {
        "active": "true",
        "closed": "false",
        "start_date_min": start,
        "start_date_max": end,
        "limit": _PAGE_LIMIT,
    }


def _iter_endpoint(url: str, params: dict, timeout: int):
    """Yield rows of one Gamma endpoint across the date window, paged by
    ``offset``. Stops at the first empty/short/failed page or ``_MAX_PAGES``.
    Never raises — a failed page (``_get_with_retry`` → None) just ends the walk,
    so a transport hiccup degrades to fewer candidates, not an exception."""
    for page in range(_MAX_PAGES):
        page_params = dict(params, limit=_PAGE_LIMIT, offset=page * _PAGE_LIMIT)
        data = _get_with_retry(url, page_params, timeout)
        if not isinstance(data, list) or not data:
            return
        yield from data
        if len(data) < _PAGE_LIMIT:
            return  # last (short) page — nothing more in the window


def iter_candidates(game_date: str, timeout: int, window_days: int = _DEFAULT_WINDOW_DAYS):
    """Yield candidate Gamma markets/events whose window overlaps ``game_date``
    (ISO 8601), lazily and paged, so a caller can stop the moment it finds its
    game. Walks BOTH the flat ``/markets`` slice (2-way moneylines) first, then
    the ``/events`` slice (event envelopes, incl. the 3-way neg-risk soccer
    events that exist ONLY under ``/events``) — ``_match_market``/``extract_odds``
    handle the shape difference downstream. Yields nothing on a bad date."""
    params = _window_params(game_date, window_days)
    if params is None:
        return
    yield from _iter_endpoint(GAMMA_MARKETS_URL, params, timeout)
    yield from _iter_endpoint(GAMMA_EVENTS_URL, params, timeout)


def search_markets(game_date: str, timeout: int, window_days: int = _DEFAULT_WINDOW_DAYS) -> list[dict]:
    """Eager list form of ``iter_candidates`` — all candidate markets/events in
    the window, both Gamma slices concatenated (flat ``/markets`` first to
    preserve the original CFB matching precedence). Returns ``[]`` (never None)
    on a bad date or an unreachable API. Prefer ``iter_candidates`` +
    ``_match_market`` for discovery so a match short-circuits the paged walk;
    this materializer stays for callers/tests that want the full slice."""
    return list(iter_candidates(game_date, timeout, window_days))


def _match_market(candidates: list[dict], home_team: str, away_team: str) -> Optional[dict]:
    for market in candidates:
        # Flat `/markets` rows carry ``question``; `/events` envelopes (incl. the
        # 3-way neg-risk soccer events) carry ``title`` instead — check both.
        text = market.get("question") or market.get("title") or market.get("slug") or ""
        if _mentions_team(text, home_team) and _mentions_team(text, away_team):
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
        "market_type": "2way",
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


# --- 3-way (soccer neg-risk) markets ------------------------------------------
# A World Cup / soccer game is NOT a single 2-outcome market. It's a "neg-risk"
# EVENT whose ``markets`` array holds three LINKED binary Yes/No submarkets —
# home win / draw / away win. Each leg's implied probability is the "Yes" price
# of that submarket; the three roughly sum to 1. This is a different Gamma shape
# from the flat 2-way moneyline above, so it gets its own extractor and the
# public ``extract_odds`` dispatcher routes between them.


def _yes_index(outcomes: list) -> Optional[int]:
    for i, label in enumerate(outcomes):
        if str(label).strip().lower() == "yes":
            return i
    return None


def _leg_yes_price(submarket: dict, timeout: int) -> Optional[float]:
    """Implied probability of a Yes/No leg = its "Yes" price. Prefers the live
    CLOB midpoint of the Yes token, falling back to Gamma's cached
    outcomePrices — same freshness policy as the 2-way path."""
    outcomes = _parse_json_field(submarket.get("outcomes")) or []
    yi = _yes_index(outcomes)
    if yi is None:
        return None
    token_ids = _parse_json_field(submarket.get("clobTokenIds")) or []
    prices = _parse_json_field(submarket.get("outcomePrices")) or []
    token = token_ids[yi] if yi < len(token_ids) else None
    live = clob_midpoint(token, timeout) if token else None
    if live is not None:
        return live
    return _safe_float(prices[yi]) if yi < len(prices) else None


def _leg_slot(submarket: dict, home_team: str, away_team: str) -> Optional[str]:
    """Classify one Yes/No leg as 'home' | 'draw' | 'away' from its OWN text —
    or None if it can't be resolved unambiguously.

    Never guesses: a leg that mentions BOTH teams (e.g. the draw leg's title
    "Draw (Paraguay vs. France)") or NEITHER team is only accepted as 'draw'
    when it carries a draw marker; otherwise it is ambiguous → None. Draw is
    checked first precisely because the draw leg names both sides."""
    meta = submarket.get("marketMetadata") or {}
    line = str(meta.get("opticOddsSelectionLine") or "").strip().lower()
    text = f"{submarket.get('groupItemTitle') or ''} {submarket.get('question') or ''}"
    if line == "draw" or "draw" in text.lower():
        return "draw"
    home_match = _mentions_team(text, home_team)
    away_match = _mentions_team(text, away_team)
    if home_match and not away_match:
        return "home"
    if away_match and not home_match:
        return "away"
    return None  # ambiguous (both) or unclassifiable (neither) — never guess


def _classify_three_way(submarkets: list, home_team: str, away_team: str) -> Optional[dict]:
    """Map an event's submarkets to {'home','draw','away'} leg dicts, or None.

    Returns None (never a partial/guessed mapping) unless there are exactly
    three Yes/No binary legs that each classify to a DISTINCT slot filling all
    of home/draw/away. Any unclassifiable, ambiguous, or duplicated leg fails
    the whole event — a wrong home/away assignment is worse than no odds."""
    if not isinstance(submarkets, list) or len(submarkets) != 3:
        return None
    slots: dict[str, dict] = {}
    for m in submarkets:
        outcomes = _parse_json_field(m.get("outcomes")) or []
        if len(outcomes) != 2 or _yes_index(outcomes) is None:
            return None  # every leg of a 3-way must be a Yes/No binary
        slot = _leg_slot(m, home_team, away_team)
        if slot is None or slot in slots:
            return None  # unclassifiable, ambiguous, or duplicate slot
        slots[slot] = m
    if set(slots) != {"home", "draw", "away"}:
        return None
    return slots


def _event_to_three_way_odds(event: dict, home_team: str, away_team: str, timeout: int) -> Optional[dict]:
    slots = _classify_three_way(event.get("markets") or [], home_team, away_team)
    if slots is None:
        return None
    slug = event.get("slug")
    return {
        "market_type": "3way",
        "market_id": (
            str(event["id"]) if event.get("id") is not None else event.get("negRiskMarketID")
        ),
        "question": event.get("title"),
        "slug": slug,
        "home_team": home_team,
        "away_team": away_team,
        "home_win_prob": _leg_yes_price(slots["home"], timeout),
        "draw_prob": _leg_yes_price(slots["draw"], timeout),
        "away_win_prob": _leg_yes_price(slots["away"], timeout),
        "volume": _safe_float(event.get("volume")),
        "liquidity": _safe_float(event.get("liquidity")),
        "end_date": event.get("endDate"),
        "closed": bool(event.get("closed")) if event.get("closed") is not None else None,
        "source_url": f"https://polymarket.com/event/{slug}" if slug else None,
    }


def extract_odds(obj: dict, home_team: str, away_team: str, timeout: int) -> Optional[dict]:
    """Shape-agnostic odds extraction. Routes between:
    - a 3-way neg-risk EVENT (``markets`` = 3 linked Yes/No legs) → home/draw/away,
    - an EVENT wrapping a single 2-team moneyline market → 2-way,
    - a flat `/markets` 2-team moneyline row → 2-way (the original path).
    Returns None for any shape it can't resolve — the caller treats that as
    explicit missingness, identical to 'no market'."""
    submarkets = obj.get("markets")
    if isinstance(submarkets, list) and submarkets:
        three = _event_to_three_way_odds(obj, home_team, away_team, timeout)
        if three is not None:
            return three
        # Not a clean 3-way: only a single wrapped 2-team market is a valid 2-way.
        if len(submarkets) == 1:
            return _market_to_odds(submarkets[0], home_team, away_team, timeout)
        return None
    return _market_to_odds(obj, home_team, away_team, timeout)


def find_game_market(home_team: str, away_team: str, game_date: str, timeout: int = 30) -> Optional[dict]:
    """Discover + price a CFB game's Polymarket market, if one exists.

    Returns ``None`` when there's no matching market (the common CFB case) —
    NOT an error. On a match, returns implied win probabilities. The payload
    carries a ``market_type`` discriminator:
      - ``"2way"``  → {..., home_win_prob, away_win_prob}
      - ``"3way"``  → {..., home_win_prob, draw_prob, away_win_prob}  (soccer/
                       neg-risk events where a draw is a distinct outcome)
    plus {market_type, market_id, question, slug, home_team, away_team, volume,
    liquidity, end_date, closed, source_url}. ``*_prob`` values are themselves
    independently nullable (e.g. CLOB and Gamma both failed to price a leg) —
    always None-check before use.

    Discovery walks BOTH the flat `/markets` slice and the `/events` slice
    (paged), so live 3-way neg-risk EVENTS (which exist only under `/events`)
    are found and priced end-to-end here — not just when an event is handed to
    ``extract_odds`` directly. It early-exits on the first candidate that
    mentions both teams, so a game with a market rarely walks the full window.
    """
    for candidate in iter_candidates(game_date, timeout):
        if _match_market([candidate], home_team, away_team) is not None:
            return extract_odds(candidate, home_team, away_team, timeout)
    return None


def fetch_game_odds(home_team: str, away_team: str, game_date: str, timeout: int = 30) -> Optional[dict]:
    """Public entrypoint. Wraps ``find_game_market`` with a blanket try/except
    so ANY unexpected failure (bad payload shape, etc.) also degrades to
    ``None`` rather than propagating — callers must treat None as "no data",
    never as an error to retry/alert on."""
    try:
        return find_game_market(home_team, away_team, game_date, timeout=timeout)
    except Exception:
        return None
