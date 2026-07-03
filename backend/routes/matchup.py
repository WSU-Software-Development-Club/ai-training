"""Matchup Intelligence Engine routes — serves the per-game factor deck."""

from flask import Blueprint, jsonify
from services.matchup_service import get_matchup_deck

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
