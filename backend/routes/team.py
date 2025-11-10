"""
Team routes for team-specific data like record, ppg, etc.

Endpoints will expose team-centric data, such as:
- GET /team/<team_name>/record
"""

from flask import Blueprint, jsonify
from services.team_service import (
    get_team_record,
)


team_bp = Blueprint("team", __name__, url_prefix="/team")


@team_bp.route("/<team_name>/record", methods=["GET"])
def get_team_record_route(team_name: str):
    """Route to get a single team's record."""
    record = get_team_record(team_name)
    
    if record is None:
        return jsonify({
            "success": False,
            "error": "Failed to fetch record"
        }), 500
    
    return jsonify({
        "success": True,
        "data": record,
        "data_type": "Team record"
    })


