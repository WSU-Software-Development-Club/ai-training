"""
Stats routes for NCAA football statistics data
"""

from flask import Blueprint, jsonify
from services.stats_service import (
    get_all_teams_stats, 
    get_team_stats, 
    get_stat_category_name,
    get_offense_stats,
    get_defense_stats,
    get_team_offense_stats,
    get_team_defense_stats
)

# Create blueprint for stats routes
stats_bp = Blueprint('stats', __name__, url_prefix='/stats')


@stats_bp.route('/stat/<int:stat_id>', methods=['GET'])
def get_stat_category(stat_id):
    """Route to get statistics for all teams in a specific stat category"""
    stats_data = get_all_teams_stats(stat_id)
    
    if stats_data is None:
        return jsonify({
            "success": False,
            "error": f"Failed to fetch statistics for stat category {stat_id}"
        }), 500
    
    return jsonify({
        "success": True,
        "data": stats_data,
        "stat_name": get_stat_category_name(stat_id)
    })


@stats_bp.route('/stat/<int:stat_id>/team/<team_name>', methods=['GET'])
def get_team_stat(stat_id, team_name):
    """Route to get statistics for a specific team in a specific stat category"""
    team_data = get_team_stats(stat_id, team_name)
    
    if team_data is None:
        return jsonify({
            "success": False,
            "error": f"Team '{team_name}' not found in {get_stat_category_name(stat_id)} statistics"
        }), 404
    
    return jsonify({
        "success": True,
        "data": team_data,
        "stat_name": get_stat_category_name(stat_id),
        "team_name": team_name
    })


@stats_bp.route('/offense', methods=['GET'])
def get_offense_stats_route():
    """Route to get total offense statistics for all teams"""
    offense_data = get_offense_stats()
    
    if offense_data is None:
        return jsonify({
            "success": False,
            "error": "Failed to fetch offense statistics"
        }), 500
    
    return jsonify({
        "success": True,
        "data": offense_data,
        "stat_name": "Total Offense"
    })


@stats_bp.route('/offense/team/<team_name>', methods=['GET'])
def get_team_offense_stats_route(team_name):
    """Route to get offense statistics for a specific team"""
    team_data = get_team_offense_stats(team_name)
    
    if team_data is None:
        return jsonify({
            "success": False,
            "error": f"Team '{team_name}' not found in offense statistics"
        }), 404
    
    return jsonify({
        "success": True,
        "data": team_data,
        "stat_name": "Total Offense",
        "team_name": team_name
    })


@stats_bp.route('/defense', methods=['GET'])
def get_defense_stats_route():
    """Route to get total defense statistics for all teams"""
    defense_data = get_defense_stats()
    
    if defense_data is None:
        return jsonify({
            "success": False,
            "error": "Failed to fetch defense statistics"
        }), 500
    
    return jsonify({
        "success": True,
        "data": defense_data,
        "stat_name": "Total Defense"
    })


@stats_bp.route('/defense/team/<team_name>', methods=['GET'])
def get_team_defense_stats_route(team_name):
    """Route to get defense statistics for a specific team"""
    team_data = get_team_defense_stats(team_name)
    
    if team_data is None:
        return jsonify({
            "success": False,
            "error": f"Team '{team_name}' not found in defense statistics"
        }), 404
    
    return jsonify({
        "success": True,
        "data": team_data,
        "stat_name": "Total Defense",
        "team_name": team_name
    })
