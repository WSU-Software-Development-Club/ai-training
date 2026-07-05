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
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests

GAMMA_MARKETS_URL = "https://gamma-api.polymarket.com/markets"
GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"
GAMMA_SEARCH_URL = "https://gamma-api.polymarket.com/public-search"
CLOB_MIDPOINT_URL = "https://clob.polymarket.com/midpoint"
CLOB_PRICES_HISTORY_URL = "https://clob.polymarket.com/prices-history"

# Keywords that mark a NON-moneyline market (spread/total/half/quarter/props),
# so game-win-probability discovery keeps only the full-game moneyline.
_NON_MONEYLINE = ("spread", "o/u", "over", "under", "1h", "2h", "half",
                  "1st", "quarter", "props", "player", "margin")

# Finest resolution (minutes) we request from CLOB /prices-history. 1 = per
# minute, which the endpoint honors for a windowed (startTs/endTs) query as long
# as the span is short (≲10h); it silently coarsens wider spans on its own.
_MIN_FIDELITY = 1

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


# --------------------------------------------------------------------------
# Historical price CURVE (for PAST/resolved games).
#
# find_game_market above discovers only ACTIVE markets (Gamma active=true,
# closed=false) and reports a single CURRENT price — right for an upcoming game,
# useless for one that already resolved. The functions below instead locate the
# game's market via Gamma's public-search (which returns resolved events too)
# and pull the full CLOB /prices-history time series, so the post-game view can
# render the same win-probability curve Polymarket shows.
# --------------------------------------------------------------------------


def _search_event(home_team: str, away_team: str, game_date: str, timeout: int) -> Optional[dict]:
    """Find the Polymarket EVENT for a game via public-search, resolved markets
    included. Returns the event dict (with its markets) whose title mentions
    both teams and whose date matches, or None. Unlike ``search_markets`` this
    finds CLOSED markets, which is exactly what a past game needs."""
    q = f"{away_team} {home_team}"
    data = _get_with_retry(GAMMA_SEARCH_URL, {"q": q, "limit_per_type": 20}, timeout)
    events = (data or {}).get("events") if isinstance(data, dict) else None
    if not events:
        return None
    try:
        target = datetime.fromisoformat(game_date.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        target = None
    best = None
    for ev in events:
        title = ev.get("title") or ""
        if not (_mentions_team(title, home_team) and _mentions_team(title, away_team)):
            continue
        # When the game date is known, require the event to fall within a few
        # days of it (the search can return same-matchup rematches).
        if target is not None:
            ev_date = _event_date(ev)
            if ev_date is not None and abs((ev_date - target).days) > 5:
                continue
        best = ev
        break
    return best


def _event_date(ev: dict) -> Optional["datetime.date"]:
    for key in ("startDate", "endDate", "startTime"):
        val = ev.get(key)
        if not val:
            continue
        try:
            return datetime.fromisoformat(str(val).replace("Z", "+00:00")).date()
        except (ValueError, AttributeError):
            continue
    return None


def _pick_moneyline(markets: list[dict], home_team: str, away_team: str) -> Optional[dict]:
    """From an event's markets, pick the full-game MONEYLINE: exactly two
    outcomes, one per team, and no spread/total/half phrasing in the question."""
    for market in markets or []:
        question = (market.get("question") or "").lower()
        if any(kw in question for kw in _NON_MONEYLINE):
            continue
        outcomes = _parse_json_field(market.get("outcomes")) or []
        if len(outcomes) != 2:
            continue
        mentions = [
            (_mentions_team(o, home_team), _mentions_team(o, away_team)) for o in outcomes
        ]
        if any(h for h, _ in mentions) and any(a for _, a in mentions):
            return market
    return None


def fetch_price_history(
    token_id: str,
    start_ts: int,
    end_ts: int,
    timeout: int = 30,
    fidelity: int = 60,
) -> Optional[list[dict]]:
    """Full CLOB price history for one outcome token over [start_ts, end_ts]
    (unix seconds), as ``[{"t": <unix>, "p": <price 0..1>}, ...]`` or None.

    NOTE: an explicit start/end window is REQUIRED for resolved markets —
    ``interval=max`` returns an EMPTY series once a market has closed, whereas a
    windowed query returns the archived curve. ``fidelity`` is the sampling
    resolution in minutes (min 10)."""
    if not token_id:
        return None
    params = {
        "market": token_id,
        "startTs": int(start_ts),
        "endTs": int(end_ts),
        "fidelity": max(_MIN_FIDELITY, int(fidelity)),
    }
    data = _get_with_retry(CLOB_PRICES_HISTORY_URL, params, timeout)
    if not isinstance(data, dict):
        return None
    history = data.get("history")
    if not isinstance(history, list):
        return None
    out = []
    for pt in history:
        t = pt.get("t")
        p = _safe_float(pt.get("p"))
        if t is not None and p is not None:
            out.append({"t": int(t), "p": p})
    return out


def _trim_flat_tail(series: list[dict], eps: float = 0.005, keep_after_s: int = 600) -> list[dict]:
    """Drop the long flat tail a resolved market leaves after it pins to 0/1.

    Finds the last point that still MOVED (differs from the final price by more
    than ``eps``) and keeps only ``keep_after_s`` seconds past it, so the curve
    ends a few minutes after the outcome locks instead of stretching a flat line
    for hours. Returns the series unchanged when nothing is flat."""
    if len(series) < 3:
        return series
    final = series[-1]["p"]
    last_move = 0
    for i, pt in enumerate(series):
        if abs(pt["p"] - final) > eps:
            last_move = i
    if last_move >= len(series) - 1:
        return series  # movement right up to the end; nothing flat to trim
    cutoff = series[last_move]["t"] + keep_after_s
    return [pt for pt in series if pt["t"] <= cutoff]


def find_game_price_history(
    home_team: str,
    away_team: str,
    game_date: str,
    timeout: int = 30,
    hours_before: int = 2,
    hours_after: int = 7,
    fidelity: int = 1,
    context_days: int = 7,
) -> Optional[dict]:
    """The historical win-probability CURVE for a (past) game's moneyline, or
    None if no market is found. Binary market ⇒ away = 1 − home, so we pull only
    the home token's series and derive the away side (identical timestamps).

    Two fetches are merged so the UI can default to the game window yet still
    zoom OUT to the days-long pre-game drift:
      * a DENSE per-minute game window (kickoff −``hours_before`` / +``hours_after``);
        CLOB only keeps 1-min resolution for spans ≲10h, hence the tight window.
      * a COARSE multi-day context (``context_days`` before kickoff, hourly) for
        everything outside that window.
    Overlapping coarse points inside the dense window are dropped (the per-minute
    series wins there), so the result is dense in-game and sparse before it —
    exactly the shape Polymarket renders.

    On success:
        {market_id, question, slug, source_url, home_team, away_team,
         points: [{as_of, home_win_prob, away_win_prob}, ...]}  # as_of ISO-8601 UTC
    """
    event = _search_event(home_team, away_team, game_date, timeout)
    if event is None:
        return None
    market = _pick_moneyline(event.get("markets") or [], home_team, away_team)
    if market is None:
        return None

    outcomes = _parse_json_field(market.get("outcomes")) or []
    tokens = _parse_json_field(market.get("clobTokenIds")) or []
    if len(outcomes) != len(tokens) or not tokens:
        return None
    home_token = next(
        (tok for o, tok in zip(outcomes, tokens) if _mentions_team(o, home_team)), None
    )
    if home_token is None:
        return None

    try:
        d = datetime.fromisoformat(game_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None
    game_start = int((d - timedelta(hours=hours_before)).timestamp())
    game_end = int((d + timedelta(hours=hours_after)).timestamp())

    # Dense per-minute in-game curve (the default view).
    dense = fetch_price_history(home_token, game_start, game_end, timeout, fidelity) or []
    # Coarse hourly context for zooming out to the pre-game drift.
    context_start = int((d - timedelta(days=context_days)).timestamp())
    coarse = fetch_price_history(home_token, context_start, game_end, timeout, 60) or []

    # Merge: keep every dense point, plus coarse points OUTSIDE the dense window.
    merged = list(dense)
    merged.extend(pt for pt in coarse if pt["t"] < game_start or pt["t"] > game_end)
    merged.sort(key=lambda pt: pt["t"])
    if not merged:
        return None
    # A resolved market pins to 0/1 and then sits flat for hours — meaningless to
    # plot. Cut the trailing flat run shortly after the last real move.
    series = _trim_flat_tail(merged)

    slug = event.get("slug") or market.get("slug")
    points = [
        {
            "as_of": datetime.fromtimestamp(pt["t"], tz=timezone.utc).isoformat(),
            "home_win_prob": pt["p"],
            "away_win_prob": round(1.0 - pt["p"], 6),
        }
        for pt in series
    ]
    return {
        "market_id": str(market.get("id")) if market.get("id") is not None else None,
        "question": market.get("question"),
        "slug": slug,
        "source_url": f"https://polymarket.com/event/{slug}" if slug else None,
        "home_team": home_team,
        "away_team": away_team,
        "points": points,
    }


def fetch_game_price_history(
    home_team: str, away_team: str, game_date: str, timeout: int = 30, fidelity: int = 1
) -> Optional[dict]:
    """Public entrypoint for the historical curve. Wraps
    ``find_game_price_history`` so ANY unexpected failure degrades to None
    (treat as "no market/history"), never raising — same contract as
    ``fetch_game_odds``."""
    try:
        return find_game_price_history(
            home_team, away_team, game_date, timeout=timeout, fidelity=fidelity
        )
    except Exception:
        return None
