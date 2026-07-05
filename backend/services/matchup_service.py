"""Serving-read logic for the Matchup Intelligence Engine.

Reads the materialized factor_decks (the sample-size guard was already applied
when they were written by the pipeline) and shapes them for the frontend as a
two-sided edge board: the HOME and AWAY teams, each with its ranked factor deck,
a betting posture (from the score model), and the shared reference panel. Both
teams are always returned when a prediction exists — a team with no weather edge
still gets a column (empty factors), so the UI stays symmetric.
"""

import re

import requests

from api_vars import NCAA_API_BASE_URL
from utils.db import get_db


def _norm(name):
    """Loose team-name key so a deck's team_name matches the prediction's
    home_team/away_team despite punctuation/case differences."""
    return re.sub(r"[^a-z0-9]+", " ", (name or "").lower()).strip()


def _betting(is_home, pred):
    """Per-team betting posture from the model prediction: a signed spread
    (positive = favored by that many) plus the game's over/under."""
    hp = pred.get("predicted_home_score")
    ap = pred.get("predicted_away_score")
    pts, opp = (hp, ap) if is_home else (ap, hp)
    spread = round(pts - opp) if pts is not None and opp is not None else None
    return {
        "predicted_points": round(pts) if pts is not None else None,
        "spread": spread,                     # + favored, - underdog
        "over_under": pred.get("betting_over_under"),
    }


def _model_panel(pred):
    """Fallback reference panel built straight from the prediction row, for a
    game that has a model prediction but no materialized factor deck (so the
    Pre-Game model numbers still show). Mirrors the `model`/`vegas` shape the
    pipeline materializes in `reference_panels`; polymarket is deck-only."""
    keys = ("predicted_home_score", "predicted_away_score", "predicted_winner",
            "predicted_margin", "predicted_total")
    return {
        "model": {k: pred.get(k) for k in keys},
        "vegas": {"over_under": pred.get("betting_over_under")},
        "polymarket": None,
    }


def get_matchup_deck(ncaa_game_id):
    """Return the assembled matchup for a game, or None if nothing exists.

    Shape:
        {
          "ncaa_game_id": int,
          "home_team": str | None,
          "away_team": str | None,
          "reference_panels": {...} | None,
          "teams": [                       # ordered [home, away] when known
            {team_id, team_name, is_home, factors:[...], betting:{...},
             as_of_timestamp}, ...
          ]
        }
    """
    db = get_db()
    rows = db.get_factor_deck_by_game(ncaa_game_id)
    pred = db.get_prediction_by_ncaa_game_id(ncaa_game_id) if db.is_connected else None
    if not rows and not pred:
        return None

    # Latest deck per team, keyed by normalized team name for the home/away join.
    decks_by_name = {}
    reference_panels = None
    seen = set()
    for row in rows or []:
        team_id = str(row["team_id"])
        if team_id in seen:
            continue
        seen.add(team_id)
        if reference_panels is None:
            reference_panels = row.get("reference_panels")
        decks_by_name[_norm(row.get("team_name"))] = {
            "team_id": team_id,
            "team_name": row.get("team_name"),
            "factors": row.get("factors") or [],
            "as_of_timestamp": row.get("as_of_timestamp"),
        }

    def team_entry(name, is_home):
        deck = decks_by_name.get(_norm(name)) or {
            "team_id": None, "team_name": name, "factors": [], "as_of_timestamp": None,
        }
        return {
            **deck,
            "team_name": deck.get("team_name") or name,
            "is_home": is_home,
            "betting": _betting(is_home, pred) if pred else None,
        }

    # A game can have a prediction but no materialized factor deck (no rows,
    # so no reference_panels came off them). Still surface the model numbers —
    # the Pre-Game tab leans on reference_panels.model as its headline input.
    if reference_panels is None and pred:
        reference_panels = _model_panel(pred)

    if pred:
        teams = [team_entry(pred.get("home_team"), True),
                 team_entry(pred.get("away_team"), False)]
    else:
        # No prediction row — fall back to whatever decks exist, no home/away.
        teams = [{**d, "is_home": None, "betting": None} for d in decks_by_name.values()]

    return {
        "ncaa_game_id": ncaa_game_id,
        "home_team": pred.get("home_team") if pred else None,
        "away_team": pred.get("away_team") if pred else None,
        "reference_panels": reference_panels,
        "teams": teams,
    }


def get_matchup_polymarket_history(ncaa_game_id):
    """Polymarket implied-win-probability history for a game, or None if the
    game has no prediction row at all (same 404 semantics as the score route).

    Team names come from the prediction (so the chart can label home/away); the
    series itself is the ordered list of Polymarket snapshots. An empty series
    (`points: []`) is legitimate and common — most CFB games never had a market
    — and is returned as 200, not 404, so the UI shows an "no market" state.

    Shape:
        {ncaa_game_id, home_team, away_team, kickoff, question, source_url,
         points: [{as_of, home_win_prob, away_win_prob}, ...]}
    `kickoff` (ISO-8601 or None) lets the chart default its view to the game
    window instead of the full ingested span.
    """
    db = get_db()
    pred = db.get_prediction_by_ncaa_game_id(ncaa_game_id) if db.is_connected else None
    if not pred:
        return None

    history = db.get_polymarket_history(ncaa_game_id)
    # Market metadata is game-level; take it from the latest snapshot that has it.
    question = source_url = None
    for row in reversed(history):
        question = question or row.get("question")
        source_url = source_url or row.get("source_url")
        if question and source_url:
            break

    kickoff = pred.get("game_date")
    if hasattr(kickoff, "isoformat"):
        kickoff = kickoff.isoformat()

    return {
        "ncaa_game_id": ncaa_game_id,
        "home_team": pred.get("home_team"),
        "away_team": pred.get("away_team"),
        "kickoff": kickoff,
        "question": question,
        "source_url": source_url,
        "points": [
            {
                "as_of": row.get("as_of"),
                "home_win_prob": row.get("home_win_prob"),
                "away_win_prob": row.get("away_win_prob"),
            }
            for row in history
        ],
    }


def _int_or_none(v):
    """NCAA scores can be ints, numeric strings, or '' before a game is played."""
    if v in ("", None):
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _status_from_contest(contest):
    """Normalize the NCAA game status to our small set: pre | live | final."""
    s = (contest.get("statusCodeDisplay") or "").lower()
    if s in ("pre", "live", "final"):
        return s
    # Fall back to the single-letter gameState (F/L/P) if needed.
    return {"F": "final", "L": "live", "P": "pre"}.get(contest.get("gameState"))


def _fetch_ncaa_game_json(ncaa_game_id, sub_path=""):
    """GET a NCAA game-by-id document, optionally a sub-resource like
    ``/team-stats`` or ``/scoring-summary``. Returns the parsed JSON dict, or
    None on any network/parse failure (same graceful-degrade as the rest of the
    app — a missing feed becomes "no data", never an error)."""
    url = f"{NCAA_API_BASE_URL}/game/{ncaa_game_id}{sub_path}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except (requests.exceptions.RequestException, ValueError):
        return None


def _fetch_game_result(ncaa_game_id):
    """Fetch a single game's result straight from the NCAA game-by-id endpoint
    (same source the scoreboard uses, but keyed by the exact NCAA gameID so no
    week/date resolution is needed). Returns {home_score, away_score, status}
    or None on any miss/parse failure. Home/away follow the NCAA `isHome` flag.
    """
    data = _fetch_ncaa_game_json(ncaa_game_id)
    if data is None:
        return None

    contests = data.get("contests") or []
    if not contests:
        return None
    contest = contests[0]

    home_score = away_score = None
    for team in contest.get("teams") or []:
        score = _int_or_none(team.get("score"))
        if team.get("isHome"):
            home_score = score
        else:
            away_score = score

    return {
        "home_score": home_score,
        "away_score": away_score,
        "status": _status_from_contest(contest),
    }


def get_matchup_score(ncaa_game_id):
    """Actual score for a game, or None if it has no prediction row at all.

    Team names come from the prediction; the live score/status come from the
    NCAA game-by-id endpoint. Scores/status stay None when the game can't be
    resolved (e.g. a synthetic seed id, or the NCAA feed is unavailable) — the
    caller renders that as "—".

    Shape:
        {ncaa_game_id, home_team, away_team, home_score, away_score, status}
        status: "pre" | "live" | "final" | None
    """
    db = get_db()
    pred = db.get_prediction_by_ncaa_game_id(ncaa_game_id) if db.is_connected else None
    if not pred:
        return None

    result = {
        "ncaa_game_id": ncaa_game_id,
        "home_team": pred.get("home_team"),
        "away_team": pred.get("away_team"),
        "home_score": None,
        "away_score": None,
        "status": None,
    }

    live = _fetch_game_result(ncaa_game_id)
    if live:
        result.update(live)

    return result


def _team_meta(team):
    """Compact identity block for one team from a NCAA `teams` entry."""
    return {
        "team_id": str(team.get("teamId")) if team.get("teamId") is not None else None,
        "name": team.get("nameShort") or team.get("nameFull") or team.get("name6Char"),
        "abbrev": team.get("name6Char"),
        "is_home": bool(team.get("isHome")),
    }


def _num(v):
    """Coerce a NCAA stat string to a float, or None when blank/non-numeric."""
    if v in ("", None):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _ratio(num, denom, digits=1):
    """Safe per-attempt average as a display string (e.g. yards per pass)."""
    n, d = _num(num), _num(denom)
    if n is None or d in (None, 0):
        return "0.0"
    return f"{round(n / d, digits)}"


def _stat_rows(stats):
    """Build ESPN-style comparison labels/values from one team's `teamStats`.

    Returns an ordered {label: value} map; the caller zips two of these into
    away/home columns. Mirrors the box-score rows ESPN shows (first downs,
    down efficiency, total/passing/rushing yards, turnovers, penalties)."""
    passing = stats.get("TeamPassingStats") or {}
    rushing = stats.get("TeamRushingStats") or {}

    def s(v):
        return "" if v is None else str(v)

    interceptions = _num(passing.get("passingInterceptions")) or 0
    fumbles_lost = _num(stats.get("fumblesLost")) or 0
    return {
        "1st Downs": s(stats.get("firstDowns")),
        "3rd down efficiency": f"{s(stats.get('thirdDowns'))}-{s(stats.get('thirdDownAttempts'))}",
        "4th down efficiency": f"{s(stats.get('fourthDowns'))}-{s(stats.get('fourthDownAttempts'))}",
        "Total Yards": s(stats.get("teamYards")),
        "Passing": s(passing.get("passingYards")),
        "Comp-Att": f"{s(passing.get('passingCompletions'))}-{s(passing.get('passingAttempts'))}",
        "Yards per pass": _ratio(passing.get("passingYards"), passing.get("passingAttempts")),
        "Interceptions thrown": s(passing.get("passingInterceptions")),
        "Rushing": s(rushing.get("rushingYards")),
        "Rushing Attempts": s(rushing.get("rushingAttempts")),
        "Yards per rush": _ratio(rushing.get("rushingYards"), rushing.get("rushingAttempts")),
        "Penalties": f"{s(stats.get('penalty'))}-{s(stats.get('penaltyYards'))}",
        "Turnovers": s(int(interceptions + fumbles_lost)),
        "Fumbles lost": s(stats.get("fumblesLost")),
    }


def get_matchup_team_stats(ncaa_game_id):
    """ESPN-style team-stats comparison for a finished game, or None if the
    NCAA box score is unavailable (unplayed game, synthetic seed id, feed down).

    Shape:
        {ncaa_game_id, home:{team_id,name,abbrev}, away:{...},
         rows: [{label, home, away}, ...]}
    Rows are ordered as ESPN presents them; away sits left of home in the UI.
    """
    data = _fetch_ncaa_game_json(ncaa_game_id, "/team-stats")
    if not data:
        return None

    boxscores = data.get("teamBoxscore") or []
    teams = data.get("teams") or []
    if len(boxscores) < 2 or len(teams) < 2:
        return None

    # `teams` carries isHome; `teamBoxscore` carries the stats, joined on teamId
    # (string in `teams`, int in `teamBoxscore`).
    meta_by_id = {str(t.get("teamId")): _team_meta(t) for t in teams}
    stats_by_id = {
        str(b.get("teamId")): _stat_rows(b.get("teamStats") or {})
        for b in boxscores
    }

    home_meta = next((m for m in meta_by_id.values() if m["is_home"]), None)
    away_meta = next((m for m in meta_by_id.values() if not m["is_home"]), None)
    if not home_meta or not away_meta:
        return None

    home_stats = stats_by_id.get(home_meta["team_id"]) or {}
    away_stats = stats_by_id.get(away_meta["team_id"]) or {}
    if not home_stats or not away_stats:
        return None

    rows = [
        {"label": label, "home": home_stats.get(label, ""), "away": away_stats.get(label, "")}
        for label in home_stats
    ]

    return {
        "ncaa_game_id": ncaa_game_id,
        "home": {k: home_meta[k] for k in ("team_id", "name", "abbrev")},
        "away": {k: away_meta[k] for k in ("team_id", "name", "abbrev")},
        "rows": rows,
    }


# NCAA scoreType codes → human labels for the scoring feed.
_SCORE_TYPE_LABELS = {
    "TD": "Touchdown",
    "FG": "Field Goal",
    "XP": "Extra Point",
    "2PT": "Two-Point",
    "XP2": "Two-Point",
    "SF": "Safety",
    "SAF": "Safety",
}


def get_matchup_scoring_summary(ncaa_game_id):
    """Quarter-by-quarter scoring feed for a finished game (the narrative
    "play-by-play"), or None if the NCAA scoring summary is unavailable.

    Each period lists its scoring plays in order, with the team, clock, a
    human-readable description, and the running score after the play.

    Shape:
        {ncaa_game_id, home:{team_id,name,abbrev}, away:{...},
         periods: [{title, plays: [{team_id, is_home, team_abbrev, time,
                    type, type_label, text, home_score, away_score}]}]}
    """
    data = _fetch_ncaa_game_json(ncaa_game_id, "/scoring-summary")
    if not data:
        return None

    teams = data.get("teams") or []
    periods = data.get("periods") or []
    if len(teams) < 2:
        return None

    meta_by_id = {}
    home_meta = away_meta = None
    for t in teams:
        m = _team_meta(t)
        meta_by_id[m["team_id"]] = m
        if m["is_home"]:
            home_meta = m
        else:
            away_meta = m
    if not home_meta or not away_meta:
        return None

    out_periods = []
    for period in periods:
        plays = []
        for play in period.get("summary") or []:
            tid = str(play.get("teamId")) if play.get("teamId") is not None else None
            meta = meta_by_id.get(tid) or {}
            score_type = play.get("scoreType")
            text = play.get("scoreText")
            if text in (None, "", "null"):
                text = _SCORE_TYPE_LABELS.get(score_type, score_type or "Score")
            plays.append({
                "team_id": tid,
                "is_home": meta.get("is_home"),
                "team_abbrev": meta.get("abbrev"),
                "time": play.get("time") or "",
                "type": score_type,
                "type_label": _SCORE_TYPE_LABELS.get(score_type, score_type or ""),
                "text": text,
                "home_score": _int_or_none(play.get("homeScore")),
                "away_score": _int_or_none(play.get("visitScore")),
            })
        if plays:
            out_periods.append({"title": period.get("title") or "", "plays": plays})

    if not out_periods:
        return None

    return {
        "ncaa_game_id": ncaa_game_id,
        "home": {k: home_meta[k] for k in ("team_id", "name", "abbrev")},
        "away": {k: away_meta[k] for k in ("team_id", "name", "abbrev")},
        "periods": out_periods,
    }
