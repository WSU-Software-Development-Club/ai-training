"""Matchup Intelligence Engine routes — serves the per-game factor deck."""

from flask import Blueprint, jsonify
from services.matchup_service import (
    get_matchup_deck,
    get_matchup_polymarket_history,
    get_matchup_score,
)

matchup_bp = Blueprint('matchup', __name__, url_prefix='/matchup')


@matchup_bp.route('/<int:ncaa_game_id>', methods=['GET'])
def get_matchup(ncaa_game_id):
    """Return both teams' ranked factor decks + reference panels for a game.

    404 when no deck has been assembled yet (or the DB is unreachable — the
    reader degrades to [] like the rest of the app).
    """
    deck = get_matchup_deck(ncaa_game_id)
    if deck is None:
        return jsonify({
            "success": False,
            "error": "No matchup factor deck available for this game"
        }), 404

    return jsonify({
        "success": True,
        "data": deck,
        "data_type": "Matchup factor deck"
    })


@matchup_bp.route('/<int:ncaa_game_id>/score', methods=['GET'])
def get_score(ncaa_game_id):
    """Return the actual final score for a game (best-effort, from the NCAA
    scoreboard).

    404 when the game has no prediction row at all. When the game exists but the
    score can't be resolved (unplayed, synthetic seed id, or NCAA feed down),
    this still returns 200 with null scores/status so the UI can show "—".
    """
    score = get_matchup_score(ncaa_game_id)
    if score is None:
        return jsonify({
            "success": False,
            "error": "No game found for this id"
        }), 404

    return jsonify({
        "success": True,
        "data": score,
        "data_type": "Matchup final score"
    })


@matchup_bp.route('/<int:ncaa_game_id>/polymarket', methods=['GET'])
def get_polymarket(ncaa_game_id):
    """Return the Polymarket implied-win-probability history for a game.

    404 when the game has no prediction row at all. When the game exists but
    never had a Polymarket market (the common CFB case), this returns 200 with
    an empty `points` list so the UI can render a "no market" state.
    """
    history = get_matchup_polymarket_history(ncaa_game_id)
    if history is None:
        return jsonify({
            "success": False,
            "error": "No game found for this id"
        }), 404

    return jsonify({
        "success": True,
        "data": history,
        "data_type": "Matchup Polymarket history"
    })
