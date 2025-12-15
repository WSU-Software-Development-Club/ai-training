"""
Team routes for team-specific data like record, ppg, etc.

Endpoints will expose team-centric data, such as:
- GET /team/<team_name>/record
"""

from flask import Blueprint, jsonify
from services.team_service import (
    get_team_record,
    get_all_teams,
)


team_bp = Blueprint("team", __name__, url_prefix="/team")


@team_bp.route("/<team_name>/record", methods=["GET"])
def get_team_record_route(team_name: str):
    """Route to get a single team's record."""
    record = get_team_record(team_name)
    
    if record is None:
        return jsonify({
            "success": False,
            "error": f"Failed to fetch record for team '{team_name}'."
        }), 404
    
    return jsonify({
        "success": True,
        "data": record,
        "data_type": "Team record"
    })


@team_bp.route("", methods=["GET"])
@team_bp.route("/", methods=["GET"])
def get_all_teams_route():
    """Route to get all teams with their conferences and stats."""
    teams = get_all_teams()
    
    if teams is None:
        return jsonify({
            "success": False,
            "error": "Failed to fetch teams data."
        }), 500
    
    return jsonify({
        "success": True,
        "data": teams,
        "data_type": "Teams list",
        "count": len(teams)
    })


