"""
Scoreboard service for fetching NCAA football game data by week
Includes predictions from Supabase when available
"""

import requests
from datetime import date
from api_vars import NCAA_API_BASE_URL
from utils.supabase_client import get_supabase_client

def process_games(raw_data: dict, predictions_map: dict = None, season: int = None, week: int = None, supabase=None):
    """
    Process games and include predictions if available
    
    Args:
        raw_data: Raw game data from NCAA API
        predictions_map: Dictionary mapping ncaa_game_id to predictions (for quick lookup)
        season: Season year for precise prediction matching
        week: Week number for precise prediction matching
        supabase: Supabase client instance for direct lookups if needed
    """
    processed_games = []
    
    if predictions_map is None:
        predictions_map = {}

    for game_wrapper in raw_data.get('games', []):
        game = game_wrapper.get('game', {})
        away_team = game.get('away', {}) or {}
        home_team = game.get('home', {}) or {}
        
        # Get NCAA gameID for prediction lookup (ensure it's an integer)
        ncaa_game_id = game.get('gameID')
        if ncaa_game_id is not None:
            ncaa_game_id = int(ncaa_game_id)
        
        # Debug: Print game info
        if predictions_map:  # Only print if we have predictions to match
            # Use 'short' if 'full' is empty
            home_names = home_team.get('names', {})
            away_names = away_team.get('names', {})
            home_team_name = home_names.get('full') or home_names.get('short', '')
            away_team_name = away_names.get('full') or away_names.get('short', '')
            print(f"Debug: Scoreboard game - {away_team_name} @ {home_team_name} (NCAA ID: {ncaa_game_id})")

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
                    away_team.get('conferences', [{}])[0].get('conferenceSeo')
                    if away_team.get('conferences') else None
                )
                },

            'home': {
                'score': None if home_team.get('score') in ('', None) else int(home_team.get('score')),
                'names': home_team.get('names', {}),
                'rank': None if home_team.get('rank') in ('', None) else int(home_team.get('rank')),
                'conference': (
                    home_team.get('conferences', [{}])[0].get('conferenceSeo')
                    if home_team.get('conferences') else None
                )
                },
            'epoch': game.get('startTimeEpoch')
        }
        
        # Add prediction if available - match by NCAA game ID, season, and week
        prediction = None
        if ncaa_game_id and season and week:
            # First try quick lookup from predictions_map
            if ncaa_game_id in predictions_map:
                pred = predictions_map[ncaa_game_id]
                # Verify season and week match for accuracy
                if pred.get('season') == season and pred.get('week') == week:
                    prediction = pred
                    print(f"Debug: ✓ Prediction found in map for NCAA game ID: {ncaa_game_id}")
                else:
                    print(f"Debug: ⚠ Prediction in map doesn't match season/week for NCAA game ID: {ncaa_game_id}")
            
            # If not found in map, try direct lookup (fallback)
            if prediction is None and supabase and supabase.is_connected:
                prediction = supabase.get_prediction_by_ncaa_game_id(ncaa_game_id, season, week)
                if prediction:
                    print(f"Debug: ✓ Prediction found via direct lookup for NCAA game ID: {ncaa_game_id}")
        
        # Add complete prediction data if found
        if prediction:
            game_data['prediction'] = {
                'id': prediction.get('id'),
                'game_id': prediction.get('game_id'),
                'ncaa_game_id': prediction.get('ncaa_game_id'),
                'season': prediction.get('season'),
                'week': prediction.get('week'),
                'game_date': prediction.get('game_date'),
                'home_team': prediction.get('home_team'),
                'away_team': prediction.get('away_team'),
                'home_score': prediction.get('predicted_home_score'),
                'away_score': prediction.get('predicted_away_score'),
                'winner': prediction.get('predicted_winner'),
                'margin': prediction.get('predicted_margin'),
                'predicted_total': prediction.get('predicted_total'),
                'betting_over_under': prediction.get('betting_over_under'),
                'over_probability': prediction.get('over_probability'),
                'under_probability': prediction.get('under_probability'),
                'neutral_site': prediction.get('neutral_site', False),
                'predicted_at': prediction.get('prediction_made_at'),
                'created_at': prediction.get('created_at')
            }
        elif ncaa_game_id:
            print(f"Debug: ⚠ No prediction found for NCAA game ID: {ncaa_game_id}, season: {season}, week: {week}")
        
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
        supabase = None
        try:
            supabase = get_supabase_client()
            if supabase.is_connected:
                predictions = supabase.get_predictions_by_week(year, week)
                print(f"Debug: Found {len(predictions)} predictions in database for week {week}, year {year}")
                
                # Create a map for quick lookup: ncaa_game_id (int) -> prediction
                # Only include predictions that match the season and week
                for pred in predictions:
                    ncaa_game_id = pred.get('ncaa_game_id')
                    pred_season = pred.get('season')
                    pred_week = pred.get('week')
                    
                    # Verify season and week match before adding to map
                    if ncaa_game_id and pred_season == year and pred_week == week:
                        # Ensure gameID is an integer for consistent lookup
                        ncaa_game_id = int(ncaa_game_id)
                        predictions_map[ncaa_game_id] = pred
                        print(f"Debug: Added prediction with NCAA game ID: {ncaa_game_id}, season: {pred_season}, week: {pred_week}")
                    elif ncaa_game_id:
                        print(f"Debug: Skipping prediction - season/week mismatch (NCAA ID: {ncaa_game_id}, season: {pred_season}, week: {pred_week})")
                    else:
                        # Legacy predictions without NCAA game ID
                        print(f"Debug: Skipping prediction without NCAA game ID (game_id: {pred.get('game_id')})")
        except Exception as e:
            print(f"Warning: Could not fetch predictions: {e}")
            # Continue without predictions
        
        # Process games with predictions, passing season, week, and supabase for precise matching
        processed_games = process_games(raw_data, predictions_map, season=year, week=week, supabase=supabase)

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