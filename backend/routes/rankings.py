"""
Rankings routes for NCAA football rankings data
"""

from flask import Blueprint, jsonify

# Create blueprint for rankings routes
rankings_bp = Blueprint('rankings', __name__, url_prefix='/rankings')


@rankings_bp.route('/ap-top25', methods=['GET'])
def get_ap_rankings():
    """
    Route to get AP Top 25 rankings
    
    This would call rankings_service.get_ap_rankings() to fetch data from:
    https://ncaa-api.henrygd.me/rankings/football/fbs/associated-press
    
    Returns:
        JSON response with AP Top 25 rankings
    """
    # TODO: Implement this route by calling rankings_service.get_ap_rankings()
    return jsonify({
        "success": False,
        "error": "AP Top 25 rankings route not implemented yet",
        "message": "This route would fetch AP Top 25 rankings from the NCAA API"
    }), 501


