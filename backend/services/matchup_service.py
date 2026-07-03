"""Serving-read logic for the Matchup Intelligence Engine.

Reads the materialized factor_decks (the sample-size guard was already applied
when they were written by the pipeline) and shapes them for the frontend: both
teams' ranked factor decks plus the Layer-6 reference panel (model/vegas/
polymarket), explicitly framed as context inputs, not a verdict.
"""

from utils.db import get_db


def get_matchup_deck(ncaa_game_id):
    """Return the assembled matchup for a game, or None if no deck exists.

    Shape:
        {
          "ncaa_game_id": int,
          "reference_panels": {...} | None,   # inputs, not the answer
          "teams": [ {team_id, team_name, factors:[...], as_of_timestamp}, ... ]
        }
    """
    rows = get_db().get_factor_deck_by_game(ncaa_game_id)
    if not rows:
        return None

    teams = []
    seen = set()
    reference_panels = None
    # Rows are newest-first per team; keep the first (latest) deck per team.
    for row in rows:
        team_id = str(row["team_id"])
        if team_id in seen:
            continue
        seen.add(team_id)
        if reference_panels is None:
            reference_panels = row.get("reference_panels")
        teams.append({
            "team_id": team_id,
            "team_name": row.get("team_name"),
            "factors": row.get("factors") or [],
            "as_of_timestamp": row.get("as_of_timestamp"),
        })

    return {
        "ncaa_game_id": ncaa_game_id,
        "reference_panels": reference_panels,
        "teams": teams,
    }
