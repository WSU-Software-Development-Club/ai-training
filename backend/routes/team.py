"""
Team routes for team-specific data like record, ppg, etc.

Endpoints will expose team-centric data, such as:
- GET /team/<team_name>/record
"""

from flask import Blueprint, jsonify, request
from services.team_service import (
    available_seasons,
    get_team_record,
    get_all_teams,
)


team_bp = Blueprint("team", __name__, url_prefix="/team")


@team_bp.route("/seasons", methods=["GET"])
def get_seasons_route():
    """Seasons the team-record view can request, newest first. Powers the
    year dropdown on the team page."""
    seasons = available_seasons()
    return jsonify({
        "success": True,
        "data": seasons,
        "data_type": "Available seasons",
        "count": len(seasons)
    })


@team_bp.route("/<team_name>/record", methods=["GET"])
def get_team_record_route(team_name: str):
    """Route to get a single team's record. Optional ?year=<season> selects a
    past season (defaults to the current season)."""
    year = request.args.get("year", type=int)
    record = get_team_record(team_name, year=year)

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


