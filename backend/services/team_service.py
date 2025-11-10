"""
Service file for team-specific data like record, ppg, etc.
"""

import requests
from api_vars import NCAA_API_BASE_URL

def normalize_team_name(name):
    """
    Normalize a team name for comparisons on case the name is not always consistent.

    Has to be implemented after frontend methods are implemented.
    """
    raise NotImplementedError


def get_team_record(team_name):
    """
    Fetch team records for a given team from NCAA API

    Args:
        team_name (str): Team name (required)
    Returns:
        dict or None: Comprehensive team record data or None if not found or error occured
    """
    try:
        response = requests.get(f'{NCAA_API_BASE_URL}/standings/football/fbs', timeout=10)
        response.raise_for_status()
        raw_data = response.json()
        for conf_block in raw_data.get('data', []):
            for row in conf_block.get('standings', []):
                school = row.get("School", "")
                if school == team_name:
                    return row
        return None

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
        return None