"""
Rankings routes for NCAA football rankings data
"""

from flask import Blueprint, jsonify
from services.rankings_service import (
get_ap_rankings
)
# Create blueprint for rankings routes
rankings_bp = Blueprint('rankings', __name__, url_prefix='/rankings')


@rankings_bp.route('/ap-top25', methods=['GET'])
def get_ap_rankings_route():
    """
    Route to get AP Top 25 rankings
    
    Calls rankings_service.get_ap_rankings() to fetch data from: 
    https://ncaa-api.henrygd.me/rankings/football/fbs/associated-press
    
    Returns:
        JSON response with AP Top 25 rankings
    """
    rankings_data = get_ap_rankings()

    if rankings_data is None:
        return jsonify({
            "success": False,
            "error": "Failed to fetch AP rankings"
        }), 500
    
    return jsonify({
        "success": True,
        "data": rankings_data,
        "data_type": "AP rankings"
    })


