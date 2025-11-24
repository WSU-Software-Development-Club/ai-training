"""
Weekly College Football Score Predictions
Uses trained XGBoost models to predict upcoming game scores
Fetches data from College Football Data API and saves predictions to Supabase
"""

import os
import sys
import json
import time
import requests
import pandas as pd
import numpy as np
import xgboost as xgb
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Add training_data directory to path to import data collection functions
script_dir = Path(__file__).resolve().parent
ml_dir = script_dir.parent
training_data_dir = ml_dir / 'training_data'
sys.path.insert(0, str(training_data_dir))

# Import data collection functions
# Note: collect_data is in ml/training_data/ and added to sys.path above
try:
    from collect_data import (  # type: ignore
        get_api_headers,
        fetch_with_retry,
        fetch_season_advanced_stats,
        fetch_season_ppa,
        fetch_season_sp_ratings,
        fetch_season_srs_ratings,
        fetch_season_elo_ratings,
        fetch_season_fpi_ratings,
        fetch_betting_lines,
        fetch_recruiting_rankings,
        build_team_lookup,
        calculate_rolling_features,
        CFBD_API_BASE_URL,
        api_call_count
    )
except ImportError as e:
    print("Error: Could not import collect_data module.")
    print(f"Make sure collect_data.py exists in: {training_data_dir}")
    print(f"Import error: {e}")
    sys.exit(1)

# Load environment variables
env_path = ml_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Configuration
MODEL_DIR = script_dir / 'models'
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Supabase client initialization
try:
    from supabase import create_client, Client
    if SUPABASE_URL and SUPABASE_KEY:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    else:
        print("⚠ Warning: Supabase credentials not found. Predictions will not be saved.")
        supabase = None
except ImportError:
    print("⚠ Warning: Supabase client not installed. Run: pip install supabase")
    supabase = None


def fetch_upcoming_games(year: int, week: int) -> List[Dict]:
    """
    Fetch upcoming games for a specific week
    Endpoint: GET /games
    """
    url = f"{CFBD_API_BASE_URL}/games"
    params = {
        "year": year,
        "week": week,
        "seasonType": "regular",
        "division": "fbs"
    }
    
    print(f"  Fetching games for Week {week}, {year}...")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No data returned from API for Week {week}, {year}")
        return []
    
    if not isinstance(data, list):
        print(f"  ⚠ Expected list, got {type(data)}: {data}")
        return []
    
    print(f"  ✓ Found {len(data)} games for Week {week}")
    return data


def fetch_completed_games(year: int) -> List[Dict]:
    """
    Fetch all completed games for the current season (for rolling features)
    """
    url = f"{CFBD_API_BASE_URL}/games"
    params = {
        "year": year,
        "seasonType": "regular",
        "division": "fbs"
    }
    
    print(f"  Fetching completed games for {year}...")
    data = fetch_with_retry(url, params)
    
    if data is None:
        return []
    
    # Filter only completed games
    completed_games = [
        game for game in data 
        if game.get("completed") == True and 
           game.get("homePoints") is not None and 
           game.get("awayPoints") is not None
    ]
    
    print(f"  ✓ Found {len(completed_games)} completed games")
    return completed_games


def load_models() -> tuple:
    """
    Load trained XGBoost models and required features
    Returns: (home_model, away_model, home_features, away_features)
    """
    print("\n" + "="*70)
    print("LOADING TRAINED MODELS")
    print("="*70)
    
    # Load home score model
    home_model_path = MODEL_DIR / 'home_score_model.json'
    home_model = xgb.XGBRegressor()
    home_model.load_model(home_model_path)
    print(f"✓ Loaded home score model from {home_model_path}")
    
    # Load away score model
    away_model_path = MODEL_DIR / 'away_score_model.json'
    away_model = xgb.XGBRegressor()
    away_model.load_model(away_model_path)
    print(f"✓ Loaded away score model from {away_model_path}")
    
    # Load feature lists
    home_features_path = MODEL_DIR / 'home_score_features.json'
    with open(home_features_path, 'r') as f:
        home_features = json.load(f)
    print(f"✓ Loaded {len(home_features)} home score features")
    
    away_features_path = MODEL_DIR / 'away_score_features.json'
    with open(away_features_path, 'r') as f:
        away_features = json.load(f)
    print(f"✓ Loaded {len(away_features)} away score features")
    
    return home_model, away_model, home_features, away_features


def build_prediction_features(game: Dict, team_lookup: Dict[str, Dict],
                              all_completed_games: List[Dict],
                              betting_lines: Dict[int, Dict],
                              home_features: List[str],
                              away_features: List[str]) -> Optional[Dict]:
    """
    Build feature vectors for a single game prediction
    Returns: Dictionary with home and away feature DataFrames
    """
    home_team = game.get("homeTeam")
    away_team = game.get("awayTeam")
    game_date = game.get("startDate", "")
    game_id = game.get("id")
    
    if not home_team or not away_team:
        print(f"  ⚠ Missing team information for game {game_id}")
        return None
    
    # Calculate rolling features for both teams
    home_rolling = calculate_rolling_features(home_team, all_completed_games, game_date, window=5)
    away_rolling = calculate_rolling_features(away_team, all_completed_games, game_date, window=5)
    
    # Build feature dictionary
    features = {}
    
    # Game context features
    features["season"] = game.get("season")
    features["week"] = game.get("week")
    features["neutral_site"] = 1 if game.get("neutralSite") else 0
    features["conference_game"] = 1 if game.get("conferenceGame") else 0
    
    # Home team pre-game features
    if home_team in team_lookup:
        for key, value in team_lookup[home_team].items():
            features[f"home_{key}"] = value
    
    # Away team pre-game features
    if away_team in team_lookup:
        for key, value in team_lookup[away_team].items():
            features[f"away_{key}"] = value
    
    # Home team rolling features
    for key, value in home_rolling.items():
        features[f"home_{key}"] = value
    
    # Away team rolling features
    for key, value in away_rolling.items():
        features[f"away_{key}"] = value
    
    # Betting lines
    if game_id in betting_lines:
        line = betting_lines[game_id]
        features["betting_spread"] = line.get("spread")
        features["betting_over_under"] = line.get("overUnder")
        features["betting_home_moneyline"] = line.get("homeMoneyline")
        features["betting_away_moneyline"] = line.get("awayMoneyline")
    
    # Create DataFrames with proper feature alignment
    df = pd.DataFrame([features])
    
    # Align with model features (fill missing with 0) and ensure numeric types
    home_df = pd.DataFrame(columns=home_features)
    away_df = pd.DataFrame(columns=away_features)
    
    for feat in home_features:
        if feat in df.columns:
            # Convert to float, replacing None/NaN with 0.0
            value = df[feat].iloc[0] if not df[feat].isna().iloc[0] else 0.0
            home_df.loc[0, feat] = float(value) if value is not None else 0.0
        else:
            home_df.loc[0, feat] = 0.0
    
    for feat in away_features:
        if feat in df.columns:
            # Convert to float, replacing None/NaN with 0.0
            value = df[feat].iloc[0] if not df[feat].isna().iloc[0] else 0.0
            away_df.loc[0, feat] = float(value) if value is not None else 0.0
        else:
            away_df.loc[0, feat] = 0.0
    
    # Ensure all columns are float type
    home_df = home_df.astype(float)
    away_df = away_df.astype(float)
    
    return {
        'game': game,
        'home_features': home_df,
        'away_features': away_df,
        'home_team': home_team,
        'away_team': away_team
    }


def predict_games(games: List[Dict], year: int) -> List[Dict]:
    """
    Generate predictions for a list of games
    Returns: List of prediction dictionaries
    """
    print("\n" + "="*70)
    print(f"GENERATING PREDICTIONS FOR {len(games)} GAMES")
    print("="*70)
    
    # Load models
    home_model, away_model, home_features, away_features = load_models()
    
    # Fetch current season data (bulk API calls)
    print("\n" + "="*70)
    print(f"FETCHING SEASON DATA FOR {year}")
    print("="*70)
    
    completed_games = fetch_completed_games(year)
    advanced_stats = fetch_season_advanced_stats(year)
    ppa_data = fetch_season_ppa(year)
    sp_ratings = fetch_season_sp_ratings(year)
    srs_ratings = fetch_season_srs_ratings(year)
    elo_ratings = fetch_season_elo_ratings(year)
    fpi_ratings = fetch_season_fpi_ratings(year)
    betting_lines = fetch_betting_lines(year)
    recruiting = fetch_recruiting_rankings(year)
    
    # Build team lookup
    print(f"\n  Building team lookup...")
    team_lookup = build_team_lookup(
        year, advanced_stats, ppa_data, sp_ratings, srs_ratings,
        elo_ratings, fpi_ratings, recruiting
    )
    print(f"  ✓ Team features prepared for {len(team_lookup)} teams")
    
    # Generate predictions
    print("\n" + "="*70)
    print("MAKING PREDICTIONS")
    print("="*70)
    
    predictions = []
    
    for idx, game in enumerate(games, 1):
        game_id = game.get("id")
        home_team = game.get("homeTeam")
        away_team = game.get("awayTeam")
        
        print(f"\n[{idx}/{len(games)}] {away_team} @ {home_team}")
        
        # Build features
        prediction_data = build_prediction_features(
            game, team_lookup, completed_games, betting_lines,
            home_features, away_features
        )
        
        if prediction_data is None:
            print(f"  ⚠ Skipping game {game_id} - could not build features")
            continue
        
        # Make predictions
        home_score_pred = home_model.predict(prediction_data['home_features'])[0]
        away_score_pred = away_model.predict(prediction_data['away_features'])[0]
        
        # Round to reasonable values
        home_score_pred = max(0, round(home_score_pred, 1))
        away_score_pred = max(0, round(away_score_pred, 1))
        
        # Determine winner
        if home_score_pred > away_score_pred:
            predicted_winner = home_team
            predicted_margin = home_score_pred - away_score_pred
        else:
            predicted_winner = away_team
            predicted_margin = away_score_pred - home_score_pred
        
        prediction = {
            'game_id': game_id,
            'season': game.get('season'),
            'week': game.get('week'),
            'game_date': game.get('startDate'),
            'home_team': home_team,
            'away_team': away_team,
            'predicted_home_score': float(home_score_pred),
            'predicted_away_score': float(away_score_pred),
            'predicted_winner': predicted_winner,
            'predicted_margin': float(round(predicted_margin, 1)),
            'neutral_site': game.get('neutralSite', False),
            'prediction_made_at': datetime.utcnow().isoformat()
        }
        
        predictions.append(prediction)
        
        print(f"  Prediction: {home_team} {home_score_pred:.1f} - {away_team} {away_score_pred:.1f}")
        print(f"  Winner: {predicted_winner} by {predicted_margin:.1f}")
    
    return predictions


def save_to_supabase(predictions: List[Dict]) -> bool:
    """
    Save predictions to Supabase database
    Returns: True if successful, False otherwise
    """
    if not supabase:
        print("\n⚠ Supabase client not available. Saving predictions to local file instead.")
        # Save to local JSON file as backup
        output_file = script_dir / f'predictions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump(predictions, f, indent=2)
        print(f"✓ Predictions saved to {output_file}")
        return False
    
    print("\n" + "="*70)
    print(f"SAVING {len(predictions)} PREDICTIONS TO SUPABASE")
    print("="*70)
    
    try:
        # Insert predictions into database
        response = supabase.table('predictions').insert(predictions).execute()
        print(f"✓ Successfully saved {len(predictions)} predictions to Supabase")
        return True
    except Exception as e:
        print(f"⚠ Error saving to Supabase: {e}")
        print(f"   Saving to local file as backup...")
        
        # Save to local JSON file as backup
        output_file = script_dir / f'predictions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump(predictions, f, indent=2)
        print(f"✓ Predictions saved to {output_file}")
        return False


def get_current_week() -> tuple:
    """
    Determine the current college football season and week
    Returns: (year, week)
    """
    from datetime import timezone
    now = datetime.now(timezone.utc)
    
    # College football season typically runs from late August to early December
    # If it's January-July, use previous year
    if now.month < 8:
        year = now.year - 1
    else:
        year = now.year
    
    # Try to fetch current calendar to determine week
    url = f"{CFBD_API_BASE_URL}/calendar"
    params = {"year": year}
    
    print(f"\nDetermining current week...")
    data = fetch_with_retry(url, params)
    
    if data:
        # Find the current or next week
        for week_data in data:
            first_game_start = week_data.get('firstGameStart')
            last_game_start = week_data.get('lastGameStart')
            
            if first_game_start and last_game_start:
                start_date = datetime.fromisoformat(first_game_start.replace('Z', '+00:00'))
                end_date = datetime.fromisoformat(last_game_start.replace('Z', '+00:00'))
                
                # If we're in this week or it's upcoming within 7 days
                days_until_start = (start_date - now).days
                if -7 <= days_until_start <= 7:
                    week = week_data.get('week')
                    print(f"✓ Detected current/upcoming week: {week}")
                    return year, week
    
    # Default to week 1 if can't determine
    print(f"⚠ Could not determine current week, defaulting to week 1")
    return year, 1


def main():
    """
    Main function to orchestrate weekly predictions
    """
    print("="*70)
    print("COLLEGE FOOTBALL WEEKLY PREDICTIONS")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Determine current week (or use command line args)
    if len(sys.argv) >= 3:
        year = int(sys.argv[1])
        week = int(sys.argv[2])
        print(f"Using provided year={year}, week={week}")
    else:
        year, week = get_current_week()
        # Predict next week
        week += 1
        print(f"Predicting for next week: Year={year}, Week={week}")
    
    # Fetch upcoming games
    upcoming_games = fetch_upcoming_games(year, week)
    
    if not upcoming_games:
        print(f"\n⚠ No upcoming games found for Week {week}, {year}")
        print("   This may be the off-season or the week number is invalid.")
        return
    
    # Generate predictions
    predictions = predict_games(upcoming_games, year)
    
    if not predictions:
        print("\n⚠ No predictions generated")
        return
    
    # Save to Supabase
    save_to_supabase(predictions)
    
    # Summary
    print("\n" + "="*70)
    print("PREDICTION SUMMARY")
    print("="*70)
    print(f"Total games predicted: {len(predictions)}")
    print(f"API calls made: {api_call_count}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


if __name__ == "__main__":
    main()

