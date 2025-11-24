"""
Scoreboard service for fetching NCAA football game data by week
Includes predictions from Supabase when available
"""

import requests
from datetime import date
from api_vars import NCAA_API_BASE_URL
from utils.supabase_client import get_supabase_client

def process_games(raw_data: dict, predictions_map: dict = None):
    """
    Process games and include predictions if available
    
    Args:
        raw_data: Raw game data from NCAA API
        predictions_map: Dictionary mapping team names to predictions
    """
    processed_games = []
    
    if predictions_map is None:
        predictions_map = {}

    for game_wrapper in raw_data.get('games', []):
        game = game_wrapper.get('game', {})
        away_team = game.get('away', {}) or {}
        home_team = game.get('home', {}) or {}
        
        # Get team names for prediction lookup
        home_team_name = home_team.get('names', {}).get('full', '')
        away_team_name = away_team.get('names', {}).get('full', '')
        
        # Debug: Print team names
        if predictions_map:  # Only print if we have predictions to match
            print(f"Debug: Scoreboard game - {away_team_name} @ {home_team_name}")

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
        }
        
        # Add prediction if available (match by both team names)
        prediction_key = f"{home_team_name}|{away_team_name}"
        if prediction_key in predictions_map:
            prediction = predictions_map[prediction_key]
            game_data['prediction'] = {
                'home_score': prediction.get('predicted_home_score'),
                'away_score': prediction.get('predicted_away_score'),
                'winner': prediction.get('predicted_winner'),
                'margin': prediction.get('predicted_margin'),
                'predicted_at': prediction.get('prediction_made_at')
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
        Includes predictions from Supabase if available
    """ 
    try:
        # Fetch scoreboard data from NCAA API
        raw_response = requests.get(f"{NCAA_API_BASE_URL}/scoreboard/football/fbs/{year}/{week:02d}/all-conf", timeout=10)
        raw_response.raise_for_status()
        raw_data = raw_response.json()
        
        # Fetch predictions from Supabase
        predictions_map = {}
        try:
            supabase = get_supabase_client()
            if supabase.is_connected:
                predictions = supabase.get_predictions_by_week(year, week)
                print(f"Debug: Found {len(predictions)} predictions in database for week {week}, year {year}")
                
                # Create a map for quick lookup: "home_team|away_team" -> prediction
                for pred in predictions:
                    key = f"{pred.get('home_team')}|{pred.get('away_team')}"
                    predictions_map[key] = pred
                    print(f"Debug: Added prediction key: {key}")
        except Exception as e:
            print(f"Warning: Could not fetch predictions: {e}")
            # Continue without predictions
        
        # Process games with predictions
        processed_games = process_games(raw_data, predictions_map)

        game_data = {
            'week': week,
            'year': year,
            'updatedAt': raw_data.get('updated_at'),
            'games': processed_games,
            'totalGames': len(raw_data.get('games', [])),
            'hasPredictions': len(predictions_map) > 0
        }

        return game_data

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
    return None