"""
Scoreboard service for fetching NCAA football game data by week
"""

import requests
from datetime import datetime, timezone
from api_vars import NCAA_API_BASE_URL

def get_current_week():
    """
    TODO: Determine the current week of the season
    This is a simplified implementation - you may need to adjust based on actual season dates
    You could also fetch this from a separate API endpoint or calculate based on season start date
    """
    return 8 # for now return a week that works until this function can actually return the current week

def get_scoreboard_data(week=None, year=2025):
    """
    TODO: Fetch scoreboard data for a specific week from NCAA API
    Args:
        week (int, optional): Week number. If None, uses current week
        year (int): Season year
    Returns:
        dict or None: Scoreboard data or None if error occurred
    """
    pass

def extract_game_data(raw_game_data):
    """
    TODO: Extract and format relevant game data for frontend consumption
    Args:
        raw_game_data (dict): Raw game data from NCAA API
    Returns:
        dict: Formatted game data with isLive, isFinished, scores, team info, etc.
    """
    pass

def get_formatted_scoreboard_data(week=None, year=2025):
    """
    TODO: Fetch and format scoreboard data for frontend consumption
    Args:
        week (int, optional): Week number. If None, uses current week
        year (int): Season year
    Returns:
        dict or None: Formatted scoreboard data or None if error occurred
    """
    pass