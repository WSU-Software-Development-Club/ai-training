"""
Scoreboard service for fetching NCAA football game data by week
"""

import requests
from datetime import datetime, timezone
from api_vars import NCAA_API_BASE_URL

def get_scoreboard_data(week, year):
    """
    TODO: Fetch scoreboard data for a specific week from NCAA API
    Args:
        week (int): Week number (required)
        year (int): Season year
    Returns:
        dict or None: Scoreboard data or None if error occurred
    """
    pass