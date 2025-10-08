"""
Stats routes for NCAA football statistics data
"""

from flask import Blueprint, jsonify
from services.stats_service import (
get_stat_category_name,
get_all_teams_stats,
get_team_stats,

get_offense_stats,
get_defense_stats,
get_rushing_offense,
get_rushing_defense,
get_passing_offense,
get_scoring_offense,
get_scoring_defense,
get_turnover_margin,
get_team_passing_efficiency_defense,
get_kickoff_returns,
get_punt_returns,
get_net_punting,
get_fumbles_recovered,
get_passes_intercepted,
get_fumbles_lost,
get_passes_had_intercepted,
get_turnovers_gained,
get_turnovers_lost,
get_punt_return_defense,
get_kickoff_return_defense,
get_team_passing_efficiency,
get_team_sacks,
get_team_tackles_for_loss,
get_sacks_allowed,
get_first_downs_offense,
get_first_downs_defense,
get_passing_yards_allowed,
get_tackles_for_loss_allowed,
get_fewest_penalties_per_game,
get_fewest_penalty_yards_per_game,
get_third_down_conversion_pct,
get_fourth_down_conversion_pct,
get_third_down_conversion_pct_defense,
get_fourth_down_conversion_pct_defense,
get_red_zone_offense,
get_red_zone_defense,
get_time_of_possession,
get_passing_yards_per_completion,
get_winning_percentage,
get_completion_percentage,
get_blocked_kicks,
get_blocked_kicks_allowed,
get_blocked_punts,
get_blocked_punts_allowed,
get_fewest_penalties,
get_fewest_penalty_yards,
get_defensive_tds,

get_team_offense_stats,
get_team_defense_stats,
get_team_rushing_offense_stats,
get_team_rushing_defense_stats,
get_team_passing_offense_stats,
get_team_scoring_offense_stats,
get_team_scoring_defense_stats,
get_team_turnover_margin_stats,
get_team_passing_efficiency_defense_stats,
get_team_kickoff_returns_stats,
get_team_punt_returns_stats,
get_team_net_punting_stats,
get_team_fumbles_recovered_stats,
get_team_passes_intercepted_stats,
get_team_fumbles_lost_stats,
get_team_passes_had_intercepted_stats,
get_team_turnovers_gained_stats,
get_team_turnovers_lost_stats,
get_team_punt_return_defense_stats,
get_team_kickoff_return_defense_stats,
get_team_passing_efficiency_stats,
get_team_sacks_stats,
get_team_tackles_for_loss_stats,
get_team_sacks_allowed_stats,
get_team_first_downs_offense_stats,
get_team_first_downs_defense_stats,
get_team_passing_yards_allowed_stats,
get_team_tackles_for_loss_allowed_stats,
get_team_fewest_penalties_per_game_stats,
get_team_fewest_penalty_yards_per_game_stats,
get_team_third_down_conversion_pct_stats,
get_team_fourth_down_conversion_pct_stats,
get_team_third_down_conversion_pct_defense_stats,
get_team_fourth_down_conversion_pct_defense_stats,
get_team_red_zone_offense_stats,
get_team_red_zone_defense_stats,
get_team_time_of_possession_stats,
get_team_passing_yards_per_completion_stats,
get_team_winning_percentage_stats,
get_team_completion_percentage_stats,
get_team_blocked_kicks_stats,
get_team_blocked_kicks_allowed_stats,
get_team_blocked_punts_stats,
get_team_blocked_punts_allowed_stats,
get_team_fewest_penalties_stats,
get_team_fewest_penalty_yards_stats,
get_team_defensive_tds_stats

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


@stats_bp.route('/offense/rushing', methods=['GET'])
def get_rushing_offense_stats_route():
    """Route to get total offense rushing statistics for all teams"""
    rushing_offense_data = get_rushing_offense()
    
    if rushing_offense_data is None:
        return jsonify({
            "success": False,
            "error": "Failed to fetch rushing offense statistics"
        }), 500
    
    return jsonify({
        "success": True,
        "data": rushing_offense_data,
        "stat_name": "Rushing Offense"
    })

@stats_bp.route('/defense/rushing', methods=['GET'])
def get_rushing_defense_stats_route():
    """Route to get total defense rushing statistics for all teams"""
    rushing_defense_data = get_rushing_defense()
    
    if rushing_defense_data is None:
        return jsonify({
            "success": False,
            "error": "Failed to fetch rushing defense statistics"
        }), 500
    
    return jsonify({
        "success": True,
        "data": rushing_defense_data,
        "stat_name": "Rushing Defense"
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
