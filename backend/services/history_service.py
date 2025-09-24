"""
History service for fetching NCAA championship data
"""

import requests
from api_vars import NCAA_API_BASE_URL


def get_championship_winners():
    """
    Fetch championship winners from NCAA API

    Returns:
        dict or None: Championship data from API, or None if error occurred
    """

    try:
        response = requests.get(f'{NCAA_API_BASE_URL}/history/football/fbs')
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
    return None