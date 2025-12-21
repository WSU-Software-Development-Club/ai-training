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
from datetime import datetime, timezone
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict

# Try to import dateutil for flexible date parsing
try:
    from dateutil import parser as date_parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False

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
        print("[WARNING] Supabase credentials not found. Predictions will not be saved.")
        supabase = None
except ImportError:
    print("[WARNING] Supabase client not installed. Run: pip install supabase")
    supabase = None


# NCAA API base URL for game matching
NCAA_API_BASE_URL = "https://ncaa-api.henrygd.me"


def normalize_team_name(name: str) -> str:
    """
    Normalize team names for matching between CFBD and NCAA APIs
    
    Args:
        name: Team name from either API
    
    Returns:
        Normalized team name for comparison
    """
    if not name:
        return ""
    
    # Convert to lowercase for case-insensitive comparison
    original = name.lower().strip()
    
    # Handle specific abbreviations and variations FIRST (before general cleanup)
    # This prevents "University of Miami" from becoming "of miami"
    # Expanded with alternate names from cfb_teams.csv
    abbreviations = {
        # Miami variations
        "miami (fl)": "miami",
        "miami fl": "miami",
        "miami (fla.)": "miami",
        "miami (ohio)": "miami oh",
        "miami (oh)": "miami oh",
        "miami oh": "miami oh",
        "m-oh": "miami oh",
        "university of miami": "miami",
        # USC/California
        "southern california": "usc",
        "university of southern california": "usc",
        "california": "cal",
        "university of california": "cal",
        # Religious schools
        "texas christian": "tcu",
        "southern methodist": "smu",
        "brigham young": "byu",
        # Louisiana schools
        "louisiana state": "lsu",
        "ul lafayette": "louisiana",
        "la lafayette": "louisiana",
        "la-lafayette": "louisiana",
        # Texas A&M
        "texas a&m": "texas am",
        "texas a&amp;m": "texas am",
        "ta&m": "texas am",
        "tx a&m": "texas am",
        # State schools with abbreviations
        "middle tennessee": "mtsu",
        "middle tennessee state": "mtsu",
        "mississippi st.": "mississippi state",
        "mississippi st": "mississippi state",
        "msst": "mississippi state",
        "southern miss": "southern mississippi",
        "southern mississippi": "southern mississippi",
        "usm": "southern mississippi",
        "ole miss": "mississippi",
        "miss": "mississippi",
        # New England
        "massachusetts": "umass",
        "mass": "umass",
        "connecticut": "uconn",
        "conn": "uconn",
        # Nevada schools
        "nevada las vegas": "unlv",
        "nevada-las vegas": "unlv",
        # Michigan schools
        "western mich.": "western michigan",
        "western mich": "western michigan",
        "wmu": "western michigan",
        "w michigan": "western michigan",
        "eastern mich.": "eastern michigan",
        "eastern mich": "eastern michigan",
        "emu": "eastern michigan",
        "e michigan": "eastern michigan",
        "central mich.": "central michigan",
        "central mich": "central michigan",
        "cmu": "central michigan",
        "c michigan": "central michigan",
        # Military academies
        "army west point": "army",
        "army west pt": "army",
        # North Carolina
        "nc state": "north carolina state",
        "north carolina st.": "north carolina state",
        "north carolina st": "north carolina state",
        "ncsu": "north carolina state",
        # Florida schools
        "ucf": "central florida",
        "central florida": "central florida",
        "florida international": "fiu",
        "florida intl": "fiu",
        # Texas schools
        "utsa": "texas san antonio",
        "texas-san antonio": "texas san antonio",
        "texas san antonio": "texas san antonio",
        "utep": "texas el paso",
        "texas-el paso": "texas el paso",
        "texas el paso": "texas el paso",
        # Pittsburgh
        "pitt": "pittsburgh",
        "pittsburgh": "pittsburgh",
        # Hawaii (handle apostrophe)
        "hawai'i": "hawaii",
        "hawaii": "hawaii",
        "haw": "hawaii",
        # Boise State
        "boise st": "boise state",
        "boise st.": "boise state",
        "bois": "boise state",
        # Appalachian State
        "app state": "appalachian state",
        "appalachian state": "appalachian state",
        "app st": "appalachian state",
        "app": "appalachian state",
        # Arizona
        "arizona st": "arizona state",
        "arizona st.": "arizona state",
        "asu": "arizona state",
        # Other state abbreviations
        "arkansas st": "arkansas state",
        "arkansas st.": "arkansas state",
        "arst": "arkansas state",
        "colorado st": "colorado state",
        "colorado st.": "colorado state",
        "csu": "colorado state",
        "florida st": "florida state",
        "florida st.": "florida state",
        "fsu": "florida state",
        "fresno st": "fresno state",
        "fresno st.": "fresno state",
        "fres": "fresno state",
        "georgia st": "georgia state",
        "georgia st.": "georgia state",
        "gast": "georgia state",
        "iowa st": "iowa state",
        "iowa st.": "iowa state",
        "isu": "iowa state",
        "kansas st": "kansas state",
        "kansas st.": "kansas state",
        "ksu": "kansas state",
        "kennesaw st": "kennesaw state",
        "kennesaw st.": "kennesaw state",
        "kenn": "kennesaw state",
        "kent st": "kent state",
        "kent st.": "kent state",
        "kent": "kent state",
        "louisiana tech": "louisiana tech",
        "la tech": "louisiana tech",
        "lt": "louisiana tech",
        "michigan st": "michigan state",
        "michigan st.": "michigan state",
        "msu": "michigan state",
        "missouri st": "missouri state",
        "missouri st.": "missouri state",
        "most": "missouri state",
        "new mexico st": "new mexico state",
        "new mexico st.": "new mexico state",
        "nmsu": "new mexico state",
        "oklahoma st": "oklahoma state",
        "oklahoma st.": "oklahoma state",
        "okst": "oklahoma state",
        "oregon st": "oregon state",
        "oregon st.": "oregon state",
        "orst": "oregon state",
        "penn st": "penn state",
        "penn st.": "penn state",
        "psu": "penn state",
        "san diego st": "san diego state",
        "san diego st.": "san diego state",
        "sdsu": "san diego state",
        "san jose st": "san jose state",
        "san jose st.": "san jose state",
        "san josé st": "san jose state",
        "san josé st.": "san jose state",
        "sjsu": "san jose state",
        "texas st": "texas state",
        "texas st.": "texas state",
        "txst": "texas state",
        "utah st": "utah state",
        "utah st.": "utah state",
        "usu": "utah state",
        "washington st": "washington state",
        "washington st.": "washington state",
        "wsu": "washington state",
        # NCAA-specific short forms
        "south fla": "south florida",
        "south fla.": "south florida",
        "usf": "south florida",
        "ga southern": "georgia southern",
        "ga. southern": "georgia southern",
        "gaso": "georgia southern",
        "jax state": "jacksonville state",
        "jax st": "jacksonville state",
        "jax st.": "jacksonville state",
        "jxst": "jacksonville state",
        "c mich": "central michigan",
        "c mich.": "central michigan",
        "w mich": "western michigan",
        "w mich.": "western michigan",
        "e mich": "eastern michigan",
        "e mich.": "eastern michigan",
        "n mex": "new mexico",
        "no tex": "north texas",
        "e car": "east carolina",
        "co car": "coastal carolina",
        "coastal caro": "coastal carolina",
        "w ky": "western kentucky",
        "western ky": "western kentucky",
        "pennst": "penn state",
        "gatech": "georgia tech",
        "ariz": "arizona",
        "az st": "arizona state",
        "missst": "mississippi state",
        "ohiost": "ohio state",
        "okla": "oklahoma",
        "oregn": "oregon",
        "washst": "washington state",
        "latech": "louisiana tech",
        "la tech": "louisiana tech",
        "s miss": "southern mississippi",
        "s miss.": "southern mississippi",
        "kensaw": "kennesaw state",
    }
    
    # Check for exact matches or substring matches in abbreviation dictionary
    for full_name, abbrev in abbreviations.items():
        if full_name == original or full_name in original:
            return abbrev
    
    # General cleanup for other teams
    normalized = original
    
    # Normalize "state" abbreviations consistently
    # Always use full "state" word for consistency
    normalized = normalized.replace(" st.", " state")
    normalized = normalized.replace(" st ", " state ")
    if normalized.endswith(" st"):
        normalized = normalized[:-3] + " state"
    
    # Remove common prefixes and suffixes
    remove_words = [
        "the university of ",
        "university of ",
        "university ",
        "state university",
        " college",
        "the ",
    ]
    
    for word in remove_words:
        normalized = normalized.replace(word, " ")
    
    # Remove special characters
    normalized = normalized.replace("-", " ").replace("(", "").replace(")", "").replace(".", "")
    
    # Remove extra whitespace
    normalized = " ".join(normalized.split()).strip()
    
    return normalized


def fetch_ncaa_games(year: int, week: Optional[int] = None, season_type: str = "regular") -> tuple:
    """
    Fetch games from NCAA API for matching with CFBD games
    
    Args:
        year: Season year
        week: Week number - Optional, will try multiple weeks if None for postseason
        season_type: Season type from CFBD ("regular" or "postseason")
    
    Returns:
        Tuple of (List of game dictionaries, NCAA week number used)
    
    Notes:
        - Regular season: NCAA API uses week numbers (01, 02, ..., 15)
        - Postseason: NCAA API uses week numbers (16, 17, 18, 19, etc.)
        - URL format: {base}/scoreboard/football/fbs/{year}/{week}/all-conf
    """
    games = []
    ncaa_week = week
    
    if season_type == "postseason":
        # Postseason: Try multiple NCAA weeks to find games (16-20)
        # If a specific week is provided, use that; otherwise try all postseason weeks
        if week is not None:
            weeks_to_try = [week]
        else:
            # Try common postseason weeks (16-20)
            weeks_to_try = [16, 17, 18, 19, 20]
        
        for try_week in weeks_to_try:
            print(f"  Fetching NCAA postseason games for Week {try_week}, {year}...")
            url = f"{NCAA_API_BASE_URL}/scoreboard/football/fbs/{year}/{try_week}/all-conf"
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                # Extract games from the NCAA API response structure
                week_games = []
                for game_wrapper in data.get('games', []):
                    game = game_wrapper.get('game', {})
                    if game:
                        # Add the NCAA week to the game data for later reference
                        game['ncaa_week'] = try_week
                        week_games.append(game)
                
                if week_games:
                    print(f"    Found {len(week_games)} games in postseason week {try_week}")
                    games.extend(week_games)
                    # If we're trying multiple weeks, collect all; otherwise use first match
                    if week is not None:
                        ncaa_week = try_week
                        break
            
            except requests.exceptions.RequestException as e:
                print(f"  [WARNING] Error fetching NCAA postseason week {try_week}: {e}")
        
        # If we tried multiple weeks, we don't have a single week number
        if week is None and games:
            print(f"    Found {len(games)} total postseason games across multiple weeks")
    
    else:
        # Regular season - use the week number (zero-padded for NCAA API)
        if week is None:
            print(f"  [WARNING] Week number required for regular season NCAA games")
            return [], None
        
        # Format week with zero-padding (01, 02, 03, etc.)
        week_formatted = f"{week:02d}"
        print(f"  Fetching NCAA games for Week {week} ({week_formatted}), {year}...")
        url = f"{NCAA_API_BASE_URL}/scoreboard/football/fbs/{year}/{week_formatted}/all-conf"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract games from the NCAA API response structure
            for game_wrapper in data.get('games', []):
                game = game_wrapper.get('game', {})
                if game:
                    games.append(game)
            
            if games:
                print(f"    Found {len(games)} games in week {week}")
        
        except requests.exceptions.RequestException as e:
            print(f"  [WARNING] Error fetching NCAA games for week {week}: {e}")
    
    print(f"  [OK] Found {len(games)} total NCAA games")
    
    # Print sample of games for debugging
    if games:
        print(f"  [DEBUG] Sample NCAA games (first 3):")
        for i, game in enumerate(games[:3]):
            home = game.get('home', {}).get('names', {})
            away = game.get('away', {}).get('names', {})
            home_name = home.get('short', 'Unknown')
            away_name = away.get('short', 'Unknown')
            ncaa_week_str = f" (Week {game.get('ncaa_week')})" if 'ncaa_week' in game else ""
            print(f"    {i+1}. {away_name} @ {home_name}{ncaa_week_str}")
    
    return games, ncaa_week


def match_cfbd_to_ncaa(cfbd_game: Dict, ncaa_games: List[Dict], debug: bool = False, 
                       used_ncaa_ids: Optional[Dict] = None, cfbd_game_id: Optional[int] = None) -> tuple:
    """
    Match a CFBD game to an NCAA game using date-based matching with dual team validation.
    
    Strategy: BOTH teams must match between CFBD and NCAA on the same date.
    Prevents duplicate NCAA game IDs by tracking already-matched games.
    
    Args:
        cfbd_game: Game data from CFBD API
        ncaa_games: List of games from NCAA API
        debug: If True, print debug information about matching attempts
        used_ncaa_ids: Dictionary tracking already-matched NCAA game IDs to prevent duplicates
        cfbd_game_id: CFBD game ID for logging purposes
    
    Returns:
        Tuple of (NCAA gameID (integer), NCAA week number) if match found, (None, None) otherwise
    """
    if used_ncaa_ids is None:
        used_ncaa_ids = {}
    cfbd_home = cfbd_game.get('homeTeam', '')
    cfbd_away = cfbd_game.get('awayTeam', '')
    cfbd_date = cfbd_game.get('startDate', '')
    
    if not cfbd_home or not cfbd_away or not cfbd_date:
        return None, None
    
    # Parse CFBD game date to get the date (YYYY-MM-DD)
    cfbd_game_date = None
    try:
        if HAS_DATEUTIL:
            cfbd_datetime = date_parser.parse(cfbd_date)
        else:
            cfbd_datetime = datetime.fromisoformat(cfbd_date.replace('Z', '+00:00'))
        # Extract just the date portion for comparison
        cfbd_game_date = cfbd_datetime.date()
    except Exception as e:
        if debug:
            print(f"  [WARNING] Could not parse CFBD date '{cfbd_date}': {e}")
        return None, None
    
    # Normalize CFBD team names
    norm_cfbd_home = normalize_team_name(cfbd_home)
    norm_cfbd_away = normalize_team_name(cfbd_away)
    
    if debug:
        print(f"  DEBUG: Looking for match on {cfbd_game_date}")
        print(f"    CFBD: {cfbd_away} ({norm_cfbd_away}) @ {cfbd_home} ({norm_cfbd_home})")
    
    # Group NCAA games by date and search for matches
    for idx, ncaa_game in enumerate(ncaa_games):
        # Parse NCAA game date
        ncaa_timestamp = ncaa_game.get('startTimeEpoch')
        if not ncaa_timestamp:
            continue
        
        try:
            # NCAA API returns epoch time in SECONDS (not milliseconds)
            ncaa_datetime = datetime.fromtimestamp(int(ncaa_timestamp), tz=timezone.utc)
            ncaa_game_date = ncaa_datetime.date()
        except Exception as e:
            if debug and idx < 5:
                print(f"    [WARNING] Could not parse NCAA timestamp: {e}")
            continue
        
        # Skip games on different dates
        if cfbd_game_date != ncaa_game_date:
            continue
        
        # Games are on the same date - now check if any team matches
        home_team = ncaa_game.get('home', {}) or {}
        away_team = ncaa_game.get('away', {}) or {}
        
        home_names = home_team.get('names', {})
        away_names = away_team.get('names', {})
        ncaa_home = home_names.get('full') or home_names.get('short', '')
        ncaa_away = away_names.get('full') or away_names.get('short', '')
        
        if not ncaa_home or not ncaa_away:
            continue
        
        # Normalize NCAA team names
        norm_ncaa_home = normalize_team_name(ncaa_home)
        norm_ncaa_away = normalize_team_name(ncaa_away)
        
        if debug:
            print(f"    NCAA game on {ncaa_game_date}: {ncaa_away} ({norm_ncaa_away}) @ {ncaa_home} ({norm_ncaa_home})")
        
        # STRICT MATCHING: BOTH teams must match between CFBD and NCAA
        # This prevents false positives when multiple games happen on same day with shared teams
        # (e.g., Arizona vs ASU and Arizona vs UCLA on same day)
        
        match_found = False
        matched_pairs = []
        match_type_description = ""
        
        # Helper function to check if two team names match
        def teams_match(cfbd_team: str, ncaa_team: str) -> tuple:
            """Returns (is_match, match_type)"""
            # Exact match
            if cfbd_team == ncaa_team:
                return True, "exact"
            
            # Partial/word overlap matching
            if len(cfbd_team) > 0 and len(ncaa_team) > 0:
                cfbd_words = set(cfbd_team.split())
                ncaa_words = set(ncaa_team.split())
                
                # Remove common filler words
                filler_words = {'state', 'university', 'college', 'of', 'the'}
                cfbd_sig_words = cfbd_words - filler_words
                ncaa_sig_words = ncaa_words - filler_words
                
                # If they share significant words, it's a match
                shared_words = cfbd_sig_words & ncaa_sig_words
                if len(shared_words) > 0:
                    return True, f"partial:{shared_words}"
            
            # Substring containment (for cases like "boise" in "boise state")
            if len(cfbd_team) >= 4 and len(ncaa_team) >= 4:
                if cfbd_team in ncaa_team or ncaa_team in cfbd_team:
                    return True, "substring"
            
            return False, ""
        
        # Check if BOTH teams match in CORRECT positions
        # Case 1: Normal matching (home-to-home, away-to-away)
        home_match, home_type = teams_match(norm_cfbd_home, norm_ncaa_home)
        away_match, away_type = teams_match(norm_cfbd_away, norm_ncaa_away)
        
        if home_match and away_match:
            match_found = True
            matched_pairs.append((norm_cfbd_home, norm_ncaa_home, home_type))
            matched_pairs.append((norm_cfbd_away, norm_ncaa_away, away_type))
            match_type_description = "normal (home↔home, away↔away)"
        
        # Case 2: Reversed matching (APIs have home/away swapped)
        if not match_found:
            home_to_away_match, home_to_away_type = teams_match(norm_cfbd_home, norm_ncaa_away)
            away_to_home_match, away_to_home_type = teams_match(norm_cfbd_away, norm_ncaa_home)
            
            if home_to_away_match and away_to_home_match:
                match_found = True
                matched_pairs.append((norm_cfbd_home, norm_ncaa_away, home_to_away_type))
                matched_pairs.append((norm_cfbd_away, norm_ncaa_home, away_to_home_type))
                match_type_description = "reversed (home↔away, away↔home)"
        
        if match_found:
            game_id = ncaa_game.get('gameID')
            ncaa_week = ncaa_game.get('ncaa_week')  # Get the NCAA week stored in the game
            if game_id is not None:
                # Check if this NCAA game ID has already been matched
                if game_id in used_ncaa_ids:
                    if debug:
                        prev_match = used_ncaa_ids[game_id]
                        print(f"      ✗ DUPLICATE DETECTED!")
                        print(f"        NCAA gameID {game_id} already matched to:")
                        print(f"        CFBD game {prev_match['cfbd_game_id']}: {prev_match['matchup']}")
                        print(f"        Current game: CFBD {cfbd_game_id}: {cfbd_away} @ {cfbd_home}")
                        print(f"        Skipping this NCAA game and continuing search...")
                    continue  # Skip this NCAA game, try next one
                
                if debug:
                    print(f"      ✓ MATCH FOUND! ({match_type_description})")
                    for cfbd_t, ncaa_t, match_type in matched_pairs:
                        print(f"        {cfbd_t} ↔ {ncaa_t} ({match_type})")
                    print(f"      NCAA gameID: {game_id}, Week: {ncaa_week}")
                
                # Register this NCAA game ID as used
                used_ncaa_ids[game_id] = {
                    'cfbd_game_id': cfbd_game_id,
                    'matchup': f"{cfbd_away} @ {cfbd_home}"
                }
                
                return int(game_id), ncaa_week
        else:
            if debug:
                print(f"      ✗ No match: Both teams must match (CFBD home={norm_cfbd_home}, away={norm_cfbd_away}; NCAA home={norm_ncaa_home}, away={norm_ncaa_away})")
    
    if debug:
        print(f"    No match found for this game")
    
    return None, None


def fetch_upcoming_games(year: int, week: Optional[int] = None, season_type: str = "both") -> List[Dict]:
    """
    Fetch upcoming games for a specific week
    Endpoint: GET /games
    """
    url = f"{CFBD_API_BASE_URL}/games"
    # Base params: year + season_type behave like other required context
    params = {
        "year": year,
        "seasonType": season_type,
        "classification": "fbs"  # Only FBS games (not FCS/D2/D3)
    }
    # If week is provided, filter to that week; otherwise, get all games
    # for the given year/seasonType (e.g., all postseason games)
    if week is not None:
        params["week"] = week
    
    print(f"  Fetching games for Week {week}, {year}...")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  [WARNING] No data returned from API for Week {week}, {year}")
        return []
    
    if not isinstance(data, list):
        print(f"  [WARNING] Expected list, got {type(data)}: {data}")
        return []
    
    print(f"  [OK] Found {len(data)} games for Week {week}")
    return data


def fetch_completed_games(year: int, season_type: str = "both") -> List[Dict]:
    """
    Fetch all completed games for the current season (for rolling features)
    """
    url = f"{CFBD_API_BASE_URL}/games"
    # Keep season_type behavior aligned with fetch_upcoming_games:
    # explicit key in params with default "both"
    params = {
        "year": year,
        "seasonType": season_type,
        "classification": "fbs"  # Only FBS games (not FCS/D2/D3)
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
    
    print(f"  [OK] Found {len(completed_games)} completed games")
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
    home_model = xgb.XGBRegressor(objective='reg:squarederror')
    home_model.load_model(home_model_path)
    print(f"[OK] Loaded home score model from {home_model_path}")
    
    # Load away score model
    away_model_path = MODEL_DIR / 'away_score_model.json'
    away_model = xgb.XGBRegressor(objective='reg:squarederror')
    away_model.load_model(away_model_path)
    print(f"[OK] Loaded away score model from {away_model_path}")
    
    # Load feature lists
    home_features_path = MODEL_DIR / 'home_score_features.json'
    with open(home_features_path, 'r') as f:
        home_features = json.load(f)
    print(f"[OK] Loaded {len(home_features)} home score features")
    
    away_features_path = MODEL_DIR / 'away_score_features.json'
    with open(away_features_path, 'r') as f:
        away_features = json.load(f)
    print(f"[OK] Loaded {len(away_features)} away score features")
    
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
        print(f"  [WARNING] Missing team information for game {game_id}")
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


def predict_games(games: List[Dict], year: int, season_type: str = "both", ncaa_games: List[Dict] = None) -> tuple:
    """
    Generate predictions for a list of games
    
    Args:
        games: List of CFBD games to predict
        year: Season year
        ncaa_games: Optional list of NCAA games for matching
    
    Returns: Tuple of (predictions list, skipped_count, matched_count, used_ncaa_game_ids dict)
    """
    print("\n" + "="*70)
    print(f"GENERATING PREDICTIONS FOR {len(games)} GAMES")
    print("="*70)
    
    # Load models
    home_model, away_model, home_features, away_features = load_models()
    
    # Fetch current season data (bulk API calls)
    print("\n" + "="*70)
    print(f"FETCHING SEASON DATA FOR {year} (seasonType={season_type})")
    print("="*70)
    
    completed_games = fetch_completed_games(year, season_type)
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
    print(f"  [OK] Team features prepared for {len(team_lookup)} teams")
    
    # Generate predictions
    print("\n" + "="*70)
    print("MAKING PREDICTIONS")
    print("="*70)
    
    predictions = []
    skipped_count = 0
    matched_count = 0
    duplicate_attempts = 0
    used_ncaa_game_ids = {}  # Track NCAA game IDs to prevent duplicates
    
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
            print(f"  [WARNING] Skipping game {game_id} - could not build features")
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
        
        # Match to NCAA game if NCAA games provided
        ncaa_game_id = None
        ncaa_week = None
        if ncaa_games:
            # Enable debug for first 3 games to see what's happening
            debug_mode = (idx <= 3)
            initial_duplicate_count = len([gid for gid, info in used_ncaa_game_ids.items()])
            
            ncaa_game_id, ncaa_week = match_cfbd_to_ncaa(
                game, ncaa_games, 
                debug=debug_mode, 
                used_ncaa_ids=used_ncaa_game_ids,
                cfbd_game_id=game_id
            )
            
            # Check if we encountered duplicates during matching
            # The matching function will log duplicates, we just need to count them
            # Note: used_ncaa_game_ids is updated inside match_cfbd_to_ncaa when a match is found
            
            if ncaa_game_id:
                print(f"  [OK] Matched to NCAA gameID: {ncaa_game_id}, Week: {ncaa_week}")
                matched_count += 1
            else:
                print(f"  [SKIPPED] No NCAA match found - prediction not saved")
                skipped_count += 1
                continue  # Skip this game entirely - don't create prediction
        
        # Determine week number to store
        # For postseason: use NCAA week if available, otherwise use CFBD week + 15
        # For regular season: use CFBD week
        game_week = game.get('week')
        if season_type == "postseason":
            if ncaa_week is not None:
                # Use the NCAA week number directly (16, 17, 18, 19, etc.)
                game_week = ncaa_week
            elif game_week is not None:
                # Fallback: Add 15 to postseason weeks so they continue from regular season
                # Postseason week 1 → week 16, week 2 → week 17, etc.
                game_week = game_week + 15
        
        # Only create prediction if we have NCAA match (or NCAA games not provided)
        prediction = {
            'game_id': game_id,
            'ncaa_game_id': ncaa_game_id,
            'season': game.get('season'),
            'week': game_week,
            'game_date': game.get('startDate'),
            'home_team': home_team,
            'away_team': away_team,
            'predicted_home_score': float(home_score_pred),
            'predicted_away_score': float(away_score_pred),
            'predicted_winner': predicted_winner,
            'predicted_margin': float(round(predicted_margin, 1)),
            'neutral_site': game.get('neutralSite', False),
            'prediction_made_at': datetime.now(timezone.utc).isoformat()
        }
        
        predictions.append(prediction)
        
        print(f"  Prediction: {home_team} {home_score_pred:.1f} - {away_team} {away_score_pred:.1f}")
        print(f"  Winner: {predicted_winner} by {predicted_margin:.1f}")
    
    return predictions, skipped_count, matched_count, used_ncaa_game_ids


def save_to_supabase(predictions: List[Dict]) -> bool:
    """
    Save predictions to Supabase database using upsert.
    If a prediction with the same ncaa_game_id exists, it will be updated.
    This allows re-running predictions for the same week without creating duplicates.
    
    Returns: True if successful, False otherwise
    """
    
    print("\n" + "="*70)
    print(f"SAVING {len(predictions)} PREDICTIONS TO SUPABASE")
    print("="*70)
    
    try:
        # Upsert predictions into database (update if ncaa_game_id exists, insert if new)
        # The 'on_conflict' parameter specifies which column to use for conflict resolution
        response = supabase.table('predictions').upsert(
            predictions,
            on_conflict='ncaa_game_id'
        ).execute()
        print(f"[OK] Successfully upserted {len(predictions)} predictions to Supabase")
        print(f"     (Existing predictions with same NCAA game IDs were updated)")
        return True
    except Exception as e:
        print(f"[WARNING] Error saving to Supabase: {e}")
        print(f"   Saving to local file as backup...")
        
        # Save to local JSON file as backup
        output_file = script_dir / f'predictions_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump(predictions, f, indent=2)
        print(f"[OK] Predictions saved to {output_file}")
        return False


def detect_season_phase(year: int = None, current_date: datetime = None) -> Dict[str, Any]:
    """
    Determine if we're in regular season, postseason, or offseason.
    
    Args:
        year: Season year (defaults to current year based on month)
        current_date: Date to check (defaults to now)
    
    Returns:
        Dictionary with:
            - phase: 'regular' | 'postseason' | 'offseason'
            - year: Season year
            - week: Week number (for regular season) or None
            - season_type: 'regular' | 'postseason'
    """
    if current_date is None:
        current_date = datetime.now(timezone.utc)
    
    # Determine season year if not provided
    if year is None:
        # College football season typically runs from late August to early January
        # If it's January-July, use previous year
        if current_date.month < 8:
            year = current_date.year - 1
        else:
            year = current_date.year
    
    # Fetch calendar to determine season structure
    url = f"{CFBD_API_BASE_URL}/calendar"
    params = {"year": year}
    
    print(f"\nDetecting season phase for {year}...")
    data = fetch_with_retry(url, params)
    
    if not data:
        print(f"[WARNING] Could not fetch calendar for {year}, defaulting to offseason")
        return {
            'phase': 'offseason',
            'year': year,
            'week': None,
            'season_type': 'regular'
        }
    
    # Parse calendar data and find current phase
    regular_season_weeks = []
    postseason_weeks = []
    
    for week_data in data:
        week_num = week_data.get('week')
        season_type = week_data.get('seasonType', '').lower()
        first_game_start = week_data.get('firstGameStart')
        last_game_start = week_data.get('lastGameStart')
        
        if not first_game_start or not last_game_start:
            continue
        
        try:
            start_date = datetime.fromisoformat(first_game_start.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(last_game_start.replace('Z', '+00:00'))
            
            week_info = {
                'week': week_num,
                'season_type': season_type,
                'start_date': start_date,
                'end_date': end_date
            }
            
            if season_type == 'regular':
                regular_season_weeks.append(week_info)
            elif season_type == 'postseason':
                postseason_weeks.append(week_info)
        except Exception as e:
            continue
    
    # Check if current date falls in any week
    # Look ahead up to 7 days to catch upcoming games
    check_window_start = current_date
    check_window_end = current_date + pd.Timedelta(days=7)
    
    # Check regular season first
    for week_info in regular_season_weeks:
        # If the current date or upcoming window overlaps with this week
        if (week_info['start_date'] <= check_window_end and 
            week_info['end_date'] >= check_window_start):
            # Week 16+ is postseason (bowl games), even if calendar says "regular"
            if week_info['week'] >= 16:
                print(f"[OK] Detected postseason (week {week_info['week']} >= 16)")
                return {
                    'phase': 'postseason',
                    'year': year,
                    'week': week_info['week'],
                    'season_type': 'postseason'
                }
            print(f"[OK] Detected regular season week {week_info['week']}")
            return {
                'phase': 'regular',
                'year': year,
                'week': week_info['week'],
                'season_type': 'regular'
            }
    
    # Check postseason
    for week_info in postseason_weeks:
        if (week_info['start_date'] <= check_window_end and 
            week_info['end_date'] >= check_window_start):
            print(f"[OK] Detected postseason (bowl games)")
            return {
                'phase': 'postseason',
                'year': year,
                'week': week_info['week'],  # CFBD uses week numbers for postseason
                'season_type': 'postseason'
            }
    
    # If no match found, we're in offseason
    print(f"[INFO] Currently in offseason for {year}")
    return {
        'phase': 'offseason',
        'year': year,
        'week': None,
        'season_type': 'regular'
    }


def get_current_week() -> tuple:
    """
    Determine the current college football season and week
    Returns: (year, week)
    
    DEPRECATED: Use detect_season_phase() instead for better postseason handling
    """
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
                    print(f"[OK] Detected current/upcoming week: {week}")
                    return year, week
    
    # Default to week 1 if can't determine
    print(f"[WARNING] Could not determine current week, defaulting to week 1")
    return year, 1


def main():
    """
    Main function to orchestrate weekly predictions with auto-detection
    
    Auto-detects whether we're in regular season or postseason and fetches
    appropriate games. No command-line arguments needed for GitHub Actions.
    
    Optional command-line arguments for manual override:
        python predict_upcoming.py [year] [week|postseason]
    """
    print("="*70)
    print("COLLEGE FOOTBALL WEEKLY PREDICTIONS")
    print("="*70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check for command-line arguments to override auto-detection
    if len(sys.argv) >= 2:
        # Manual override mode
        year = int(sys.argv[1])
        
        if len(sys.argv) >= 3:
            second_arg = sys.argv[2].lower()
            
            if second_arg == "postseason":
                # Explicit postseason request
                season_type = "postseason"
                phase = "postseason"
                week = None  # Postseason doesn't need week number
                print(f"\n[MANUAL] Postseason - Year {year} (command-line override)")
            else:
                # Treat as week number for regular season
                try:
                    week = int(second_arg)
                    season_type = "regular"
                    phase = "regular"
                    print(f"\n[MANUAL] Regular Season - Year {year}, Week {week} (command-line override)")
                except ValueError:
                    print(f"\n[ERROR] Invalid argument '{second_arg}'. Use a week number or 'postseason'")
                    return
        else:
            # Only year provided - auto-detect phase for that year
            print(f"\n[AUTO-DETECT] Year {year} specified, detecting phase...")
            phase_info = detect_season_phase(year=year)
            week = phase_info['week']
            season_type = phase_info['season_type']
            phase = phase_info['phase']
    else:
        # No arguments - full auto-detection
        print(f"\n[AUTO-DETECT] No arguments provided, detecting current phase...")
        phase_info = detect_season_phase()
        year = phase_info['year']
        week = phase_info['week']
        season_type = phase_info['season_type']
        phase = phase_info['phase']
        
        # Display detected phase
        if phase == 'regular':
            print(f"[DETECTED] Regular Season - Year {year}, Week {week}")
        elif phase == 'postseason':
            print(f"[DETECTED] Postseason - Year {year} (Bowl Games)")
    
    # Exit if offseason
    if phase == 'offseason':
        print(f"\n[INFO] Currently in offseason for {year}. No games to predict.")
        print("   College football season typically runs from late August to early January.")
        return
    
    # Fetch upcoming games from CFBD
    print("\n" + "="*70)
    print("FETCHING UPCOMING GAMES")
    print("="*70)
    
    if phase == 'postseason':
        # Postseason: fetch all postseason games (don't filter by week)
        upcoming_games = fetch_upcoming_games(year, week=None, season_type="postseason")
    else:
        # Regular season: fetch specific week
        upcoming_games = fetch_upcoming_games(year, week=week, season_type="regular")
    
    if not upcoming_games:
        print(f"\n[WARNING] No upcoming games found for {phase} {year}")
        if phase == 'regular':
            print(f"   Week {week} may not have any games scheduled.")
        return
    
    # Fetch NCAA games for matching
    print("\n" + "="*70)
    print("FETCHING NCAA GAMES FOR MATCHING")
    print("="*70)
    
    ncaa_week_used = None
    if phase == 'postseason':
        # Postseason: NCAA uses week numbers (16+), fetch all postseason weeks
        ncaa_games, ncaa_week_used = fetch_ncaa_games(year, week=None, season_type="postseason")
    else:
        # Regular season: NCAA uses week number
        ncaa_games, ncaa_week_used = fetch_ncaa_games(year, week=week, season_type="regular")
    
    if not ncaa_games:
        print(f"  [WARNING] No NCAA games found - predictions will not have NCAA game IDs")
    
    # Generate predictions with NCAA matching
    predictions, skipped_count, matched_count, used_ncaa_game_ids = predict_games(upcoming_games, year, season_type, ncaa_games)
    
    if not predictions:
        print("\n[WARNING] No predictions generated (all games skipped due to no NCAA match)")
        return
    
    # Save to Supabase
    if supabase:
        save_to_supabase(predictions)
    else:
        print("\n[INFO] Supabase not configured - skipping save")
    
    # Summary
    print("\n" + "="*70)
    print("PREDICTION SUMMARY")
    print("="*70)
    print(f"Season Phase: {phase.upper()}")
    print(f"Year: {year}")
    if phase == 'regular':
        print(f"Week: {week}")
    
    # Game statistics
    total_cfbd_games = len(upcoming_games)
    print(f"\nTotal CFBD games fetched: {total_cfbd_games}")
    print(f"Predictions generated: {len(predictions)}")
    print(f"Skipped (no NCAA match): {skipped_count}")
    
    # Match rate
    if total_cfbd_games > 0:
        match_rate = (matched_count / total_cfbd_games * 100)
        print(f"\nMatch rate: {matched_count}/{total_cfbd_games} ({match_rate:.1f}%)")
        
        if match_rate < 90:
            print(f"  [NOTE] Match rate below 90% - some games may have name mismatches")
        elif match_rate >= 95:
            print(f"  [SUCCESS] Excellent match rate!")
    
    # Duplicate prevention report
    print(f"\nDuplicate Prevention:")
    unique_ncaa_ids = len(used_ncaa_game_ids)
    print(f"  Unique NCAA game IDs matched: {unique_ncaa_ids}")
    print(f"  Predictions with NCAA IDs: {len(predictions)}")
    
    # Check for any duplicate NCAA IDs in predictions (should be zero with our fix)
    ncaa_ids_in_predictions = [p.get('ncaa_game_id') for p in predictions if p.get('ncaa_game_id')]
    duplicate_count = len(ncaa_ids_in_predictions) - len(set(ncaa_ids_in_predictions))
    
    if duplicate_count > 0:
        print(f"  [ERROR] {duplicate_count} DUPLICATE NCAA IDs FOUND IN PREDICTIONS!")
        # List the duplicates
        from collections import Counter
        id_counts = Counter(ncaa_ids_in_predictions)
        duplicates = {ncaa_id: count for ncaa_id, count in id_counts.items() if count > 1}
        for ncaa_id, count in duplicates.items():
            games_with_id = [p for p in predictions if p.get('ncaa_game_id') == ncaa_id]
            print(f"    NCAA ID {ncaa_id} appears {count} times:")
            for game in games_with_id:
                print(f"      - CFBD {game['game_id']}: {game['away_team']} @ {game['home_team']}")
    else:
        print(f"  [SUCCESS] No duplicate NCAA game IDs detected! All IDs are unique.")
    
    print(f"\nAPI calls made: {api_call_count}")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)


if __name__ == "__main__":
    main()

