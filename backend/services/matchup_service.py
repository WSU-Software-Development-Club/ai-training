"""Serving-read logic for the Matchup Intelligence Engine.

Reads the materialized factor_decks (the sample-size guard was already applied
when they were written by the pipeline) and shapes them for the frontend as a
two-sided edge board: the HOME and AWAY teams, each with its ranked factor deck,
a betting posture (from the score model), and the shared reference panel. Both
teams are always returned when a prediction exists — a team with no weather edge
still gets a column (empty factors), so the UI stays symmetric.
"""

import re

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
