"""
Scoreboard routes for NCAA football game data
"""

from flask import Blueprint, jsonify, request
from services.scoreboard_service import get_formatted_scoreboard_data

# Create blueprint for scoreboard routes
scoreboard_bp = Blueprint('scoreboard', __name__, url_prefix='/scoreboard')

@scoreboard_bp.route('/week/<int:week>', methods=['GET'])
def get_scoreboard_by_week(week):
    """
    TODO: Route to get scoreboard data for a specific week
    Args:
        week (int): Week number (1-16 typically)
    Returns:
        JSON response with scoreboard data or error message
    """
    pass
