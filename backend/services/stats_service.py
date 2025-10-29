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

    try:
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
                    # Check if team_name is in page_data
                    for team in page_data['data']:
                        if team['Team'].lower() == team_name.lower():
                           return team
                    
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
    
        print(f"Team '{team_name}' not found for stat ID {stat_id}")
        return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching stats for team name {team_name} for stat ID {stat_id}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None


# All team stats

def get_offense_stats():
    """Fetch total offense statistics for all teams"""
    return get_all_teams_stats(21)


def get_defense_stats():
    """Fetch total defense statistics for all teams"""
    return get_all_teams_stats(22)

def get_rushing_offense():
    """Fetch rushing offense statistics for all teams"""
    return get_all_teams_stats(23)

def get_rushing_defense():
    """Fetch rushing defense statistics for all teams"""
    return get_all_teams_stats(24)

def get_passing_offense():
    """Fetch passing offense statistics for all teams"""
    return get_all_teams_stats(25)

def get_scoring_offense():
    """Fetch scoring offense statistics for all teams"""
    return get_all_teams_stats(27)

def get_scoring_defense():
    """Fetch scoring defense statistics for all teams"""
    return get_all_teams_stats(28)

def get_turnover_margin():
    """Fetch turnover margin statistics for all teams"""
    return get_all_teams_stats(29)

def get_team_passing_efficiency_defense():
    """Fetch team passing efficiency defense statistics for all teams"""
    return get_all_teams_stats(40)

def get_kickoff_returns():
    """Fetch kickoff returns statistics for all teams"""
    return get_all_teams_stats(96)

def get_punt_returns():
    """Fetch punt returns statistics for all teams"""
    return get_all_teams_stats(97)

def get_net_punting():
    """Fetch net punting statistics for all teams"""
    return get_all_teams_stats(98)

def get_fumbles_recovered():
    """Fetch fumbles recovered statistics for all teams"""
    return get_all_teams_stats(456)

def get_passes_intercepted():
    """Fetch passes intercepted statistics for all teams"""
    return get_all_teams_stats(457)

def get_fumbles_lost():
    """Fetch fumbles lost statistics for all teams"""
    return get_all_teams_stats(458)

def get_passes_had_intercepted():
    """Fetch passes had intercepted statistics for all teams"""
    return get_all_teams_stats(459)

def get_turnovers_gained():
    """Fetch turnovers gained statistics for all teams"""
    return get_all_teams_stats(460)

def get_turnovers_lost():
    """Fetch turnovers lost statistics for all teams"""
    return get_all_teams_stats(461)

def get_punt_return_defense():
    """Fetch punt return defense statistics for all teams"""
    return get_all_teams_stats(462)

def get_kickoff_return_defense():
    """Fetch kickoff return defense statistics for all teams"""
    return get_all_teams_stats(463)

def get_team_passing_efficiency():
    """Fetch team passing efficiency statistics for all teams"""
    return get_all_teams_stats(465)

def get_team_sacks():
    """Fetch team sacks statistics for all teams"""
    return get_all_teams_stats(466)

def get_team_tackles_for_loss():
    """Fetch team tackles for loss statistics for all teams"""
    return get_all_teams_stats(467)

def get_sacks_allowed():
    """Fetch sacks allowed statistics for all teams"""
    return get_all_teams_stats(468)

def get_first_downs_offense():
    """Fetch first downs offense statistics for all teams"""
    return get_all_teams_stats(693)

def get_first_downs_defense():
    """Fetch first downs defense statistics for all teams"""
    return get_all_teams_stats(694)

def get_passing_yards_allowed():
    """Fetch passing yards allowed statistics for all teams"""
    return get_all_teams_stats(695)

def get_tackles_for_loss_allowed():
    """Fetch tackles for loss allowed statistics for all teams"""
    return get_all_teams_stats(696)

def get_fewest_penalties_per_game():
    """Fetch fewest penalties per game statistics for all teams"""
    return get_all_teams_stats(697)

def get_fewest_penalty_yards_per_game():
    """Fetch fewest penalty yards per game statistics for all teams"""
    return get_all_teams_stats(698)

def get_third_down_conversion_pct():
    """Fetch 3rd down conversion percentage statistics for all teams"""
    return get_all_teams_stats(699)

def get_fourth_down_conversion_pct():
    """Fetch 4th down conversion percentage statistics for all teams"""
    return get_all_teams_stats(700)

def get_third_down_conversion_pct_defense():
    """Fetch 3rd down conversion percentage defense statistics for all teams"""
    return get_all_teams_stats(701)

def get_fourth_down_conversion_pct_defense():
    """Fetch 4th down conversion percentage defense statistics for all teams"""
    return get_all_teams_stats(702)

def get_red_zone_offense():
    """Fetch red zone offense statistics for all teams"""
    return get_all_teams_stats(703)

def get_red_zone_defense():
    """Fetch red zone defense statistics for all teams"""
    return get_all_teams_stats(704)

def get_time_of_possession():
    """Fetch time of possession statistics for all teams"""
    return get_all_teams_stats(705)

def get_passing_yards_per_completion():
    """Fetch passing yards per completion statistics for all teams"""
    return get_all_teams_stats(741)

def get_winning_percentage():
    """Fetch winning percentage statistics for all teams"""
    return get_all_teams_stats(742)

def get_completion_percentage():
    """Fetch completion percentage statistics for all teams"""
    return get_all_teams_stats(756)

def get_blocked_kicks():
    """Fetch blocked kicks statistics for all teams"""
    return get_all_teams_stats(785)

def get_blocked_kicks_allowed():
    """Fetch blocked kicks allowed statistics for all teams"""
    return get_all_teams_stats(786)

def get_blocked_punts():
    """Fetch blocked punts statistics for all teams"""
    return get_all_teams_stats(790)

def get_blocked_punts_allowed():
    """Fetch blocked punts allowed statistics for all teams"""
    return get_all_teams_stats(791)

def get_fewest_penalties():
    """Fetch fewest penalties statistics for all teams"""
    return get_all_teams_stats(876)

def get_fewest_penalty_yards():
    """Fetch fewest penalty yards statistics for all teams"""
    return get_all_teams_stats(877)

def get_defensive_tds():
    """Fetch defensive touchdowns statistics for all teams"""
    return get_all_teams_stats(926)

# Specific team stats

def get_team_offense_stats(team_name):
    """Find a specific team's offense statistics"""
    return get_team_stats(21, team_name)

def get_team_defense_stats(team_name):
    """Find a specific team's defense statistics"""
    return get_team_stats(22, team_name)

def get_team_rushing_offense_stats(team_name):
    """Find a specific team's rushing offense statistics"""
    return get_team_stats(23, team_name)

def get_team_rushing_defense_stats(team_name):
    """Find a specific team's rushing defense statistics"""
    return get_team_stats(24, team_name)

def get_team_passing_offense_stats(team_name):
    """Find a specific team's passing offense statistics"""
    return get_team_stats(25, team_name)

def get_team_scoring_offense_stats(team_name):
    """Find a specific team's scoring offense statistics"""
    return get_team_stats(27, team_name)

def get_team_scoring_defense_stats(team_name):
    """Find a specific team's scoring defense statistics"""
    return get_team_stats(28, team_name)

def get_team_turnover_margin_stats(team_name):
    """Find a specific team's turnover margin statistics"""
    return get_team_stats(29, team_name)

def get_team_passing_efficiency_defense_stats(team_name):
    """Find a specific team's passing efficiency defense statistics"""
    return get_team_stats(40, team_name)

def get_team_kickoff_returns_stats(team_name):
    """Find a specific team's kickoff returns statistics"""
    return get_team_stats(96, team_name)

def get_team_punt_returns_stats(team_name):
    """Find a specific team's punt returns statistics"""
    return get_team_stats(97, team_name)

def get_team_net_punting_stats(team_name):
    """Find a specific team's net punting statistics"""
    return get_team_stats(98, team_name)

def get_team_fumbles_recovered_stats(team_name):
    """Find a specific team's fumbles recovered statistics"""
    return get_team_stats(456, team_name)

def get_team_passes_intercepted_stats(team_name):
    """Find a specific team's passes intercepted statistics"""
    return get_team_stats(457, team_name)

def get_team_fumbles_lost_stats(team_name):
    """Find a specific team's fumbles lost statistics"""
    return get_team_stats(458, team_name)

def get_team_passes_had_intercepted_stats(team_name):
    """Find a specific team's passes had intercepted statistics"""
    return get_team_stats(459, team_name)

def get_team_turnovers_gained_stats(team_name):
    """Find a specific team's turnovers gained statistics"""
    return get_team_stats(460, team_name)

def get_team_turnovers_lost_stats(team_name):
    """Find a specific team's turnovers lost statistics"""
    return get_team_stats(461, team_name)

def get_team_punt_return_defense_stats(team_name):
    """Find a specific team's punt return defense statistics"""
    return get_team_stats(462, team_name)

def get_team_kickoff_return_defense_stats(team_name):
    """Find a specific team's kickoff return defense statistics"""
    return get_team_stats(463, team_name)

def get_team_passing_efficiency_stats(team_name):
    """Find a specific team's passing efficiency statistics"""
    return get_team_stats(465, team_name)

def get_team_sacks_stats(team_name):
    """Find a specific team's sacks statistics"""
    return get_team_stats(466, team_name)

def get_team_tackles_for_loss_stats(team_name):
    """Find a specific team's tackles for loss statistics"""
    return get_team_stats(467, team_name)

def get_team_sacks_allowed_stats(team_name):
    """Find a specific team's sacks allowed statistics"""
    return get_team_stats(468, team_name)

def get_team_first_downs_offense_stats(team_name):
    """Find a specific team's first downs offense statistics"""
    return get_team_stats(693, team_name)

def get_team_first_downs_defense_stats(team_name):
    """Find a specific team's first downs defense statistics"""
    return get_team_stats(694, team_name)

def get_team_passing_yards_allowed_stats(team_name):
    """Find a specific team's passing yards allowed statistics"""
    return get_team_stats(695, team_name)

def get_team_tackles_for_loss_allowed_stats(team_name):
    """Find a specific team's tackles for loss allowed statistics"""
    return get_team_stats(696, team_name)

def get_team_fewest_penalties_per_game_stats(team_name):
    """Find a specific team's fewest penalties per game statistics"""
    return get_team_stats(697, team_name)

def get_team_fewest_penalty_yards_per_game_stats(team_name):
    """Find a specific team's fewest penalty yards per game statistics"""
    return get_team_stats(698, team_name)

def get_team_third_down_conversion_pct_stats(team_name):
    """Find a specific team's 3rd down conversion percentage statistics"""
    return get_team_stats(699, team_name)

def get_team_fourth_down_conversion_pct_stats(team_name):
    """Find a specific team's 4th down conversion percentage statistics"""
    return get_team_stats(700, team_name)

def get_team_third_down_conversion_pct_defense_stats(team_name):
    """Find a specific team's 3rd down conversion percentage defense statistics"""
    return get_team_stats(701, team_name)

def get_team_fourth_down_conversion_pct_defense_stats(team_name):
    """Find a specific team's 4th down conversion percentage defense statistics"""
    return get_team_stats(702, team_name)

def get_team_red_zone_offense_stats(team_name):
    """Find a specific team's red zone offense statistics"""
    return get_team_stats(703, team_name)

def get_team_red_zone_defense_stats(team_name):
    """Find a specific team's red zone defense statistics"""
    return get_team_stats(704, team_name)

def get_team_time_of_possession_stats(team_name):
    """Find a specific team's time of possession statistics"""
    return get_team_stats(705, team_name)

def get_team_passing_yards_per_completion_stats(team_name):
    """Find a specific team's passing yards per completion statistics"""
    return get_team_stats(741, team_name)

def get_team_winning_percentage_stats(team_name):
    """Find a specific team's winning percentage statistics"""
    return get_team_stats(742, team_name)

def get_team_completion_percentage_stats(team_name):
    """Find a specific team's completion percentage statistics"""
    return get_team_stats(756, team_name)

def get_team_blocked_kicks_stats(team_name):
    """Find a specific team's blocked kicks statistics"""
    return get_team_stats(785, team_name)

def get_team_blocked_kicks_allowed_stats(team_name):
    """Find a specific team's blocked kicks allowed statistics"""
    return get_team_stats(786, team_name)

def get_team_blocked_punts_stats(team_name):
    """Find a specific team's blocked punts statistics"""
    return get_team_stats(790, team_name)

def get_team_blocked_punts_allowed_stats(team_name):
    """Find a specific team's blocked punts allowed statistics"""
    return get_team_stats(791, team_name)

def get_team_fewest_penalties_stats(team_name):
    """Find a specific team's fewest penalties statistics"""
    return get_team_stats(876, team_name)

def get_team_fewest_penalty_yards_stats(team_name):
    """Find a specific team's fewest penalty yards statistics"""
    return get_team_stats(877, team_name)

def get_team_defensive_tds_stats(team_name):
    """Find a specific team's defensive touchdowns statistics"""
    return get_team_stats(926, team_name)
