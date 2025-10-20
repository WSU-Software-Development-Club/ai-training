"""
Scoreboard service for fetching NCAA football game data by week
"""

import requests
from datetime import date
from api_vars import NCAA_API_BASE_URL

def get_scoreboard_data(week, year = date.today().year):
    """
    Args:
        week (int): Week number (required)
        year (int): Season year
    Returns:
        dict or None: Scoreboard data or None if error occurred
    """ 
    try:
        response = requests.get(f'{NCAA_API_BASE_URL}/scoreboard/football/fbs/{year}/{week}/all-conf', timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
    return None