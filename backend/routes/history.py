"""
History routes for championship data
"""

from flask import Blueprint, jsonify
from services.history_service import get_championship_winners

# Create blueprint for history routes
history_bp = Blueprint('history', __name__, url_prefix='/history')


@history_bp.route('/champions', methods=['GET'])
def get_champions():
    """
    Route to get championship winners from NCAA API
    
    Returns:
        JSON response with championship data or error message
    """
    try:
        # Call service function to fetch data from NCAA API
        champions = get_championship_winners()
        
        # Check if service function returned data successfully
        if champions is None:
            return jsonify({
                "success": False,
                "error": "Failed to fetch championship data from NCAA API"
            }), 500
        
        # Return successful response with data
        return jsonify({
            "success": True,
            "data": champions,
            "count": len(champions) if isinstance(champions, list) else 1,
            "message": "Championship data retrieved successfully"
        })
        
    except Exception as e:
        # Handle any unexpected errors
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500
