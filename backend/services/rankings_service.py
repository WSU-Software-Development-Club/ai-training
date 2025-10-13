"""
Rankings service for fetching NCAA football rankings data
"""

import requests
from api_vars import NCAA_API_BASE_URL


def get_ap_rankings():
    """
    Fetch AP Top 25 rankings from NCAA API
    
    Returns:
        dict or None: AP Top 25 rankings data, or None if error occurred
    """

    try:
        response = requests.get(f'{NCAA_API_BASE_URL}/rankings/football/fbs/associated-press', timeout=10)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
    return None