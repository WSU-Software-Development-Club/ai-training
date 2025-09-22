"""
Stats service for fetching NCAA football statistics data
"""

import requests
from api_vars import NCAA_API_BASE_URL, STAT_CATEGORIES


def get_stat_category_name(stat_id):
    """Get the human-readable name for a stat category ID"""
    return STAT_CATEGORIES.get(stat_id, f"Unknown Stat (ID: {stat_id})")


def get_all_teams_stats(stat_id):
    """
    Fetch statistics for all teams across all pages for a specific stat category
    
    This function demonstrates how to handle pagination with the NCAA API.
    It fetches all pages of data and combines them into a single response.
    
    Args:
        stat_id (int): The stat category ID
    
    Returns:
        dict or None: Combined statistics data from all pages, or None if error occurred
    """
    try:
        all_data = []
        page = 1
        
        while True:
            # Build URL with page parameter
            if page == 1:
                url = f"{NCAA_API_BASE_URL}/stats/football/fbs/current/team/{stat_id}"
            else:
                url = f"{NCAA_API_BASE_URL}/stats/football/fbs/current/team/{stat_id}/p{page}"
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                page_data = response.json()
                
                # Check if this page has data
                if 'data' in page_data and page_data['data']:
                    all_data.extend(page_data['data'])
                    
                    # Check if there are more pages
                    total_pages = page_data.get('pages', 1)
                    if page >= total_pages:
                        break
                    
                    page += 1
                else:
                    # No more data, break the loop
                    break
            else:
                print(f"API returned status code: {response.status_code} for page {page}")
                break
        
        if all_data:
            # Return the first page's metadata with combined data
            first_page_response = requests.get(f"{NCAA_API_BASE_URL}/stats/football/fbs/current/team/{stat_id}")
            if first_page_response.status_code == 200:
                metadata = first_page_response.json()
                metadata['data'] = all_data
                metadata['total_records'] = len(all_data)
                return metadata
        
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching all teams stats for stat ID {stat_id}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


def get_team_stats(stat_id, team_name):
    """
    Fetch statistics for a specific team by searching through all pages
    
    Args:
        stat_id (int): The stat category ID
        team_name (str): The team name to search for
    
    Returns:
        dict or None: Team statistics data if found, or None if not found or error occurred
    """
    # TODO: Implement this function
    # Hint: You'll need to search through all pages to find the specific team
    # Look for the team name in the 'Team' field of each record
    
    print(f"get_team_stats not implemented yet for stat ID: {stat_id}, team: {team_name}")
    return None


def get_offense_stats():
    """Fetch total offense statistics for all teams"""
    return get_all_teams_stats(21)


def get_defense_stats():
    """Fetch total defense statistics for all teams"""
    return get_all_teams_stats(22)


def get_team_offense_stats(team_name):
    """Find a specific team's offense statistics"""
    return get_team_stats(21, team_name)


def get_team_defense_stats(team_name):
    """Find a specific team's defense statistics"""
    return get_team_stats(22, team_name)


