"""
Scoreboard service for fetching NCAA football game data by week
"""

import requests
from datetime import date
from api_vars import NCAA_API_BASE_URL

def process_games(raw_data: dict):
    processed_games = []

    for game_wrapper in raw_data.get('games', []):
        game = game_wrapper.get('game', {})
        away_team = game.get('away', {}) or {}
        home_team = game.get('home', {}) or {}

        game_data = {
            'game_state':  { 
                'isUpcoming': True if game.get('gameState') == "pre" else False,
                'isLive': True if game.get('gameState') == "live" else False,
                'isFinished': True if game.get('gameState') == "final" else False
                },
            'away': {
                'score': None if away_team.get('score') in ('', None) else int(away_team.get('score')),
                'names': away_team.get('names', {}),
                'rank': None if away_team.get('rank') in ('', None) else int(away_team.get('rank')),
                'conference': (
                    away_team.get('conferences', [{}])[0].get('conferenceName')
                    if away_team.get('conferences') else None
                )
                },

            'home': {
                'score': None if home_team.get('score') in ('', None) else int(home_team.get('score')),
                'names': home_team.get('names', {}),
                'rank': None if home_team.get('rank') in ('', None) else int(home_team.get('rank')),
                'conference': (
                    home_team.get('conferences', [{}])[0].get('conferenceName')
                    if home_team.get('conferences') else None
                )
                },
            'epoch': game.get('startTimeEpoch')
            # 'date': game.get('startDate'),
            # 'time': game.get('startTimeEpoch')
        }
        processed_games.append(game_data)

    return processed_games
        

def get_scoreboard_data(week, year = date.today().year):
    """
    Args:
        week (int): Week number (required)
        year (int): Season year
    Returns:
        dict or None: Scoreboard data or None if error occurred

        Data Processing: Loop through games and extract/format each one
    """ 
    try:
        raw_response = requests.get(f"{NCAA_API_BASE_URL}/scoreboard/football/fbs/{year}/{week:02d}/all-conf", timeout=10)
        raw_response.raise_for_status()
        raw_data = raw_response.json()
        processed_games = process_games(raw_data)

        game_data = {
            'week': week,
            'year': year,
            'updatedAt': raw_data.get('updated_at'),
            'games': processed_games,
            'totalGames': len(raw_data.get('games', []))
        }

        return game_data

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
    return None