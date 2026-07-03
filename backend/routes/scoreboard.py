"""
Scoreboard routes for NCAA football game data
"""

from flask import Blueprint, jsonify, request
from services.scoreboard_service import get_scoreboard_data

# Create blueprint for scoreboard routes
scoreboard_bp = Blueprint('scoreboard', __name__, url_prefix='/scoreboard')

@scoreboard_bp.route('/week/<int:week>', methods=['GET'])
def get_scoreboard_by_week(week):
    """
    Route to get scoreboard data for a specific week
    Args:
        week (int): Week number (1-16 typically)
    Query params:
        year (int, optional): Season year (defaults to the current CFB season
            year - see services.scoreboard_service.get_scoreboard_data)
    Returns:
        JSON response with scoreboard data or error message
    """
    # Get year from query parameter; None falls through to
    # get_scoreboard_data's own CFB-season-aware default.
    year = request.args.get('year', type=int)

    scoreboard_data = get_scoreboard_data(week, year)

    if scoreboard_data is None:
        return jsonify({
            "success": False,
            "error": "Failed to fetch scoreboard data"
        }), 500
    
    return jsonify({
        "success": True,
        "data": scoreboard_data,
        "data_type": "Scoreboard data"
    })

