"""
Scoreboard routes for NCAA football game data
"""

from flask import Blueprint, jsonify, request
from services.scoreboard_service import get_formatted_scoreboard_data, get_current_week

# Create blueprint for scoreboard routes
scoreboard_bp = Blueprint('scoreboard', __name__, url_prefix='/scoreboard')

@scoreboard_bp.route('/week/<int:week>', methods=['GET'])
def get_scoreboard_by_week(week):
    """
    TODO: Route to get scoreboard data for a specific week
    Args:
        week (int): Week number (1-15 typically)
    Returns:
        JSON response with scoreboard data or error message
    """
    pass

@scoreboard_bp.route('/current', methods=['GET'])
def get_current_scoreboard():
    """
    TODO: Route to get scoreboard data for the current week
    Returns:
        JSON response with current week scoreboard data or error message
    """
    pass

@scoreboard_bp.route('/weeks', methods=['GET'])
def get_available_weeks():
    """
    TODO: Route to get information about available weeks
    Returns:
        JSON response with current week and available week range
    """
    pass
