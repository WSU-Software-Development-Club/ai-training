"""
Data collection script for College Football Data API
Collects game data and team statistics from 2003-2024 for XGBoost model training
Uses efficient bulk API calls to minimize request count (~200 calls total)

Note: For proper time-series evaluation, it's recommended to split data by season
rather than randomly. This prevents data leakage and better simulates real-world
prediction scenarios where you train on past seasons and test on future seasons.
"""

import os
import time
import requests
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Optional, Any
from collections import defaultdict
from pathlib import Path

# Load environment variables from parent directory (ml/.env)
script_dir = Path(__file__).resolve().parent
parent_dir = script_dir.parent
env_path = parent_dir / '.env'
load_dotenv(dotenv_path=env_path)

# API Configuration
CFBD_API_BASE_URL = "https://api.collegefootballdata.com"
CFBD_API_KEY = os.getenv("CFBD_API_KEY")

# Rate limiting: 10 requests per second max
REQUEST_DELAY = 0.11  # 110ms between requests to stay under limit

# API call counter
api_call_count = 0

def get_api_headers() -> Dict[str, str]:
    """Returns API headers with authentication"""
    if not CFBD_API_KEY:
        raise ValueError("CFBD_API_KEY not found in environment variables. Please add it to .env file.")
    return {
        "Authorization": f"Bearer {CFBD_API_KEY}",
        "Accept": "application/json"
    }

def fetch_with_retry(url: str, params: Optional[Dict] = None, max_retries: int = 3) -> Optional[Any]:
    """Fetch data from API with retry logic and rate limiting"""
    global api_call_count
    headers = get_api_headers()
    
    for attempt in range(max_retries):
        try:
            time.sleep(REQUEST_DELAY)  # Rate limiting
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            api_call_count += 1
            return response.json()
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:  # Rate limit exceeded
                wait_time = 60  # Wait 1 minute
                print(f"  ⚠ Rate limit exceeded. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                continue
            elif response.status_code == 404:
                return None  # Endpoint not found or no data
            else:
                print(f"  ⚠ HTTP error {response.status_code}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None
        except requests.exceptions.RequestException as e:
            print(f"  ⚠ Request error: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
    
    return None


# ============================================================================
# BULK DATA FETCHING FUNCTIONS
# ============================================================================

def fetch_season_games(year: int) -> List[Dict]:
    """
    Fetch all FBS games for a given season
    Endpoint: GET /games
    """
    url = f"{CFBD_API_BASE_URL}/games"
    params = {
        "year": year,
        "seasonType": "regular",
        "division": "fbs"
    }
    
    print(f"  Fetching games... (Call #{api_call_count + 1})")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No data returned from API for {year}")
        return []
    
    if not isinstance(data, list):
        print(f"  ⚠ Expected list, got {type(data)}: {data}")
        return []
    
    print(f"  📊 Received {len(data)} total games")
    
    # Debug: Check first game structure
    if len(data) > 0:
        sample = data[0]
        print(f"  🔍 Sample game keys: {list(sample.keys())}")
        print(f"     completed={sample.get('completed')}, homePoints={sample.get('homePoints')}, awayPoints={sample.get('awayPoints')}")
    
    # Filter only completed games with scores (using camelCase from API)
    completed_games = [
        game for game in data 
        if game.get("completed") == True and 
           game.get("homePoints") is not None and 
           game.get("awayPoints") is not None
    ]
    
    print(f"  ✓ Found {len(completed_games)} completed games")
    
    if len(completed_games) == 0 and len(data) > 0:
        print(f"  ⚠ WARNING: Received {len(data)} games but 0 passed filtering!")
        print(f"     Checking what fields are available...")
        if len(data) > 0:
            for i, game in enumerate(data[:3], 1):
                print(f"     Game {i}: {game}")
    
    return completed_games


def fetch_season_advanced_stats(year: int) -> Dict[str, Dict]:
    """
    Fetch advanced team statistics for all teams in a season
    Endpoint: GET /stats/season/advanced
    Returns: Dictionary keyed by team name
    """
    url = f"{CFBD_API_BASE_URL}/stats/season/advanced"
    params = {"year": year}
    
    print(f"  Fetching advanced stats... (Call #{api_call_count + 1})")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No advanced stats for {year}")
        return {}
    
    # Create lookup dictionary by team
    stats_lookup = {}
    for team_stat in data:
        team = team_stat.get("team")
        if team:
            stats_lookup[team] = team_stat
    
    print(f"  ✓ Advanced stats for {len(stats_lookup)} teams")
    return stats_lookup


def fetch_season_ppa(year: int) -> Dict[str, Dict]:
    """
    Fetch Predicted Points Added (PPA) metrics for all teams
    Endpoint: GET /ppa/teams
    Returns: Dictionary keyed by team name
    """
    url = f"{CFBD_API_BASE_URL}/ppa/teams"
    params = {"year": year}
    
    print(f"  Fetching PPA metrics... (Call #{api_call_count + 1})")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No PPA data for {year}")
        return {}
    
    # Create lookup dictionary by team
    ppa_lookup = {}
    for team_ppa in data:
        team = team_ppa.get("team")
        if team:
            ppa_lookup[team] = team_ppa
    
    print(f"  ✓ PPA data for {len(ppa_lookup)} teams")
    return ppa_lookup


def fetch_season_sp_ratings(year: int) -> Dict[str, Dict]:
    """
    Fetch SP+ ratings for all teams
    Endpoint: GET /ratings/sp
    Returns: Dictionary keyed by team name
    """
    url = f"{CFBD_API_BASE_URL}/ratings/sp"
    params = {"year": year}
    
    print(f"  Fetching SP+ ratings... (Call #{api_call_count + 1})")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No SP+ ratings for {year}")
        return {}
    
    ratings_lookup = {}
    for rating in data:
        team = rating.get("team")
        if team:
            ratings_lookup[team] = rating
    
    print(f"  ✓ SP+ ratings for {len(ratings_lookup)} teams")
    return ratings_lookup


def fetch_season_srs_ratings(year: int) -> Dict[str, Dict]:
    """
    Fetch SRS (Simple Rating System) ratings for all teams
    Endpoint: GET /ratings/srs
    Returns: Dictionary keyed by team name
    """
    url = f"{CFBD_API_BASE_URL}/ratings/srs"
    params = {"year": year}
    
    print(f"  Fetching SRS ratings... (Call #{api_call_count + 1})")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No SRS ratings for {year}")
        return {}
    
    ratings_lookup = {}
    for rating in data:
        team = rating.get("team")
        if team:
            ratings_lookup[team] = rating
    
    print(f"  ✓ SRS ratings for {len(ratings_lookup)} teams")
    return ratings_lookup


def fetch_season_elo_ratings(year: int) -> Dict[str, Dict]:
    """
    Fetch ELO ratings for all teams
    Endpoint: GET /ratings/elo
    Returns: Dictionary keyed by team name
    """
    url = f"{CFBD_API_BASE_URL}/ratings/elo"
    params = {"year": year}
    
    print(f"  Fetching ELO ratings... (Call #{api_call_count + 1})")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No ELO ratings for {year}")
        return {}
    
    ratings_lookup = {}
    for rating in data:
        team = rating.get("team")
        if team:
            ratings_lookup[team] = rating
    
    print(f"  ✓ ELO ratings for {len(ratings_lookup)} teams")
    return ratings_lookup


def fetch_season_fpi_ratings(year: int) -> Dict[str, Dict]:
    """
    Fetch FPI (Football Power Index) ratings for all teams
    Endpoint: GET /ratings/fpi
    Returns: Dictionary keyed by team name
    """
    url = f"{CFBD_API_BASE_URL}/ratings/fpi"
    params = {"year": year}
    
    print(f"  Fetching FPI ratings... (Call #{api_call_count + 1})")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No FPI ratings for {year}")
        return {}
    
    ratings_lookup = {}
    for rating in data:
        team = rating.get("team")
        if team:
            ratings_lookup[team] = rating
    
    print(f"  ✓ FPI ratings for {len(ratings_lookup)} teams")
    return ratings_lookup


def fetch_betting_lines(year: int, season_type: str = "regular") -> Dict[int, Dict]:
    """
    Fetch betting lines for all games in a season
    Endpoint: GET /lines
    Returns: Dictionary keyed by game ID
    """
    url = f"{CFBD_API_BASE_URL}/lines"
    params = {
        "year": year,
        "seasonType": season_type
    }
    
    print(f"  Fetching betting lines... (Call #{api_call_count + 1})")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No betting lines for {year}")
        return {}
    
    # Create lookup dictionary by game ID
    lines_lookup = {}
    for game_lines in data:
        game_id = game_lines.get("id")
        if game_id and game_lines.get("lines"):
            # Get the first available line (usually consensus)
            lines = game_lines.get("lines", [])
            if lines:
                lines_lookup[game_id] = lines[0]  # Take first line
    
    print(f"  ✓ Betting lines for {len(lines_lookup)} games")
    return lines_lookup


def fetch_recruiting_rankings(year: int) -> Dict[str, Dict]:
    """
    Fetch team recruiting rankings/talent composite
    Endpoint: GET /recruiting/teams
    Returns: Dictionary keyed by team name
    """
    url = f"{CFBD_API_BASE_URL}/recruiting/teams"
    params = {"year": year}
    
    print(f"  Fetching recruiting rankings... (Call #{api_call_count + 1})")
    data = fetch_with_retry(url, params)
    
    if data is None:
        print(f"  ⚠ No recruiting data for {year}")
        return {}
    
    recruiting_lookup = {}
    for team_recruiting in data:
        team = team_recruiting.get("team")
        if team:
            recruiting_lookup[team] = team_recruiting
    
    print(f"  ✓ Recruiting data for {len(recruiting_lookup)} teams")
    return recruiting_lookup


# ============================================================================
# FEATURE ENGINEERING FUNCTIONS
# ============================================================================

def build_team_lookup(year: int, advanced_stats: Dict, ppa_data: Dict, 
                     sp_ratings: Dict, srs_ratings: Dict, elo_ratings: Dict,
                     fpi_ratings: Dict, recruiting: Dict) -> Dict[str, Dict]:
    """
    Build comprehensive team feature lookup from all bulk data sources
    Returns: Dictionary with team name as key, containing all pre-game features
    """
    team_lookup = defaultdict(dict)
    
    # Get all unique teams
    all_teams = set()
    all_teams.update(advanced_stats.keys())
    all_teams.update(ppa_data.keys())
    all_teams.update(sp_ratings.keys())
    all_teams.update(recruiting.keys())
    
    for team in all_teams:
        features = {}
        
        # Advanced stats
        if team in advanced_stats:
            stats = advanced_stats[team]
            # Offensive stats
            features["offense_ppa"] = stats.get("offense", {}).get("ppa")
            features["offense_success_rate"] = stats.get("offense", {}).get("successRate")
            features["offense_explosiveness"] = stats.get("offense", {}).get("explosiveness")
            features["offense_power_success"] = stats.get("offense", {}).get("powerSuccess")
            features["offense_stuff_rate"] = stats.get("offense", {}).get("stuffRate")
            features["offense_line_yards"] = stats.get("offense", {}).get("lineYards")
            features["offense_line_yards_avg"] = stats.get("offense", {}).get("lineYardsAverage")
            features["offense_second_level_yards"] = stats.get("offense", {}).get("secondLevelYards")
            features["offense_second_level_yards_avg"] = stats.get("offense", {}).get("secondLevelYardsAverage")
            features["offense_open_field_yards"] = stats.get("offense", {}).get("openFieldYards")
            features["offense_open_field_yards_avg"] = stats.get("offense", {}).get("openFieldYardsAverage")
            features["offense_standard_downs_ppa"] = stats.get("offense", {}).get("standardDowns", {}).get("ppa")
            features["offense_standard_downs_success_rate"] = stats.get("offense", {}).get("standardDowns", {}).get("successRate")
            features["offense_passing_downs_ppa"] = stats.get("offense", {}).get("passingDowns", {}).get("ppa")
            features["offense_passing_downs_success_rate"] = stats.get("offense", {}).get("passingDowns", {}).get("successRate")
            features["offense_rushing_plays_ppa"] = stats.get("offense", {}).get("rushingPlays", {}).get("ppa")
            features["offense_rushing_plays_success_rate"] = stats.get("offense", {}).get("rushingPlays", {}).get("successRate")
            features["offense_passing_plays_ppa"] = stats.get("offense", {}).get("passingPlays", {}).get("ppa")
            features["offense_passing_plays_success_rate"] = stats.get("offense", {}).get("passingPlays", {}).get("successRate")
            
            # Defensive stats
            features["defense_ppa"] = stats.get("defense", {}).get("ppa")
            features["defense_success_rate"] = stats.get("defense", {}).get("successRate")
            features["defense_explosiveness"] = stats.get("defense", {}).get("explosiveness")
            features["defense_power_success"] = stats.get("defense", {}).get("powerSuccess")
            features["defense_stuff_rate"] = stats.get("defense", {}).get("stuffRate")
            features["defense_line_yards"] = stats.get("defense", {}).get("lineYards")
            features["defense_line_yards_avg"] = stats.get("defense", {}).get("lineYardsAverage")
            features["defense_second_level_yards"] = stats.get("defense", {}).get("secondLevelYards")
            features["defense_second_level_yards_avg"] = stats.get("defense", {}).get("secondLevelYardsAverage")
            features["defense_open_field_yards"] = stats.get("defense", {}).get("openFieldYards")
            features["defense_open_field_yards_avg"] = stats.get("defense", {}).get("openFieldYardsAverage")
            features["defense_standard_downs_ppa"] = stats.get("defense", {}).get("standardDowns", {}).get("ppa")
            features["defense_standard_downs_success_rate"] = stats.get("defense", {}).get("standardDowns", {}).get("successRate")
            features["defense_passing_downs_ppa"] = stats.get("defense", {}).get("passingDowns", {}).get("ppa")
            features["defense_passing_downs_success_rate"] = stats.get("defense", {}).get("passingDowns", {}).get("successRate")
            features["defense_rushing_plays_ppa"] = stats.get("defense", {}).get("rushingPlays", {}).get("ppa")
            features["defense_rushing_plays_success_rate"] = stats.get("defense", {}).get("rushingPlays", {}).get("successRate")
            features["defense_passing_plays_ppa"] = stats.get("defense", {}).get("passingPlays", {}).get("ppa")
            features["defense_passing_plays_success_rate"] = stats.get("defense", {}).get("passingPlays", {}).get("successRate")
        
        # PPA metrics
        if team in ppa_data:
            ppa = ppa_data[team]
            features["overall_ppa"] = ppa.get("overall", {}).get("overall")
            features["passing_ppa"] = ppa.get("passing", {}).get("overall")
            features["rushing_ppa"] = ppa.get("rushing", {}).get("overall")
        
        # SP+ ratings
        if team in sp_ratings:
            sp = sp_ratings[team]
            features["sp_rating"] = sp.get("rating")
            features["sp_ranking"] = sp.get("ranking")
            features["sp_offense"] = sp.get("offense", {}).get("rating")
            features["sp_defense"] = sp.get("defense", {}).get("rating")
            features["sp_special_teams"] = sp.get("specialTeams", {}).get("rating")
        
        # SRS ratings
        if team in srs_ratings:
            features["srs_rating"] = srs_ratings[team].get("rating")
            features["srs_ranking"] = srs_ratings[team].get("ranking")
        
        # ELO ratings
        if team in elo_ratings:
            features["elo_rating"] = elo_ratings[team].get("elo")
        
        # FPI ratings
        if team in fpi_ratings:
            features["fpi_rating"] = fpi_ratings[team].get("fpi")
            features["fpi_ranking"] = fpi_ratings[team].get("ranking")
        
        # Recruiting
        if team in recruiting:
            rec = recruiting[team]
            features["recruiting_rank"] = rec.get("rank")
            features["recruiting_points"] = rec.get("points")
        
        team_lookup[team] = features
    
    return dict(team_lookup)


def calculate_rolling_features(team: str, all_games: List[Dict], 
                               current_date: str, window: int = 5,
                               decay: float = 0.85) -> Dict[str, Any]:
    """
    Calculate rolling averages for last N games before current date.
    
    Enhanced features include:
    - Exponentially weighted averages (more recent games weighted higher)
    - Separate home and away performance metrics
    - Win streak tracking
    
    Args:
        team: Team name
        all_games: List of all games in the season
        current_date: Date of current game (ISO format string)
        window: Number of recent games to consider
        decay: Weight decay factor (0.85 = most recent game has 100%, next has 85%, etc.)
    
    Returns:
        Dictionary of rolling features
    """
    # Filter games for this team that occurred before current date
    team_games = []
    for game in all_games:
        game_date = game.get("startDate", "")
        if game_date >= current_date:
            continue  # Skip future games
        
        home_team = game.get("homeTeam")
        away_team = game.get("awayTeam")
        
        if team == home_team or team == away_team:
            is_home = (team == home_team)
            team_games.append({
                'game': game,
                'is_home': is_home,
                'date': game_date
            })
    
    # Sort by date (most recent first)
    team_games.sort(key=lambda x: x['date'], reverse=True)
    
    # Take last N games
    recent_games = team_games[:window]
    
    # Initialize default features
    default_features = {
        "rolling_games_played": 0,
        "rolling_wins": 0,
        "rolling_win_pct": 0.0,
        "rolling_points_scored": 0.0,
        "rolling_points_allowed": 0.0,
        "rolling_point_diff": 0.0,
        "rolling_total_points": 0.0,
        # Weighted features
        "rolling_weighted_points_scored": 0.0,
        "rolling_weighted_points_allowed": 0.0,
        "rolling_weighted_point_diff": 0.0,
        # Home/Away splits
        "rolling_home_games": 0,
        "rolling_home_wins": 0,
        "rolling_home_points_scored": 0.0,
        "rolling_home_points_allowed": 0.0,
        "rolling_away_games": 0,
        "rolling_away_wins": 0,
        "rolling_away_points_scored": 0.0,
        "rolling_away_points_allowed": 0.0,
        # Streak features
        "rolling_win_streak": 0,
        "rolling_loss_streak": 0,
    }
    
    if not recent_games:
        return default_features
    
    # Calculate statistics
    wins = 0
    points_scored = []
    points_allowed = []
    weights = []
    
    # Home/away tracking
    home_games = 0
    home_wins = 0
    home_points_scored = []
    home_points_allowed = []
    away_games = 0
    away_wins = 0
    away_points_scored = []
    away_points_allowed = []
    
    # Streak tracking
    current_streak = 0
    streak_type = None  # 'win' or 'loss'
    
    for i, game_info in enumerate(recent_games):
        game = game_info['game']
        is_home = game_info['is_home']
        
        home_points = game.get("homePoints", 0) or 0
        away_points = game.get("awayPoints", 0) or 0
        
        # Calculate weight (exponential decay)
        weight = decay ** i
        weights.append(weight)
        
        if is_home:
            team_scored = home_points
            team_allowed = away_points
            won = home_points > away_points
            
            home_games += 1
            home_points_scored.append(home_points)
            home_points_allowed.append(away_points)
            if won:
                home_wins += 1
        else:
            team_scored = away_points
            team_allowed = home_points
            won = away_points > home_points
            
            away_games += 1
            away_points_scored.append(away_points)
            away_points_allowed.append(home_points)
            if won:
                away_wins += 1
        
        points_scored.append(team_scored)
        points_allowed.append(team_allowed)
        
        if won:
            wins += 1
        
        # Track streak (only for most recent consecutive games)
        if i == 0:
            streak_type = 'win' if won else 'loss'
            current_streak = 1
        elif (streak_type == 'win' and won) or (streak_type == 'loss' and not won):
            current_streak += 1
        # Streak breaks once pattern changes (we only count from start)
    
    num_games = len(recent_games)
    total_weight = sum(weights)
    
    # Simple averages
    avg_scored = sum(points_scored) / num_games
    avg_allowed = sum(points_allowed) / num_games
    
    # Weighted averages
    weighted_scored = sum(s * w for s, w in zip(points_scored, weights)) / total_weight
    weighted_allowed = sum(a * w for a, w in zip(points_allowed, weights)) / total_weight
    
    # Home averages
    home_avg_scored = sum(home_points_scored) / home_games if home_games > 0 else 0.0
    home_avg_allowed = sum(home_points_allowed) / home_games if home_games > 0 else 0.0
    
    # Away averages
    away_avg_scored = sum(away_points_scored) / away_games if away_games > 0 else 0.0
    away_avg_allowed = sum(away_points_allowed) / away_games if away_games > 0 else 0.0
    
    return {
        # Basic rolling features
        "rolling_games_played": num_games,
        "rolling_wins": wins,
        "rolling_win_pct": wins / num_games,
        "rolling_points_scored": avg_scored,
        "rolling_points_allowed": avg_allowed,
        "rolling_point_diff": avg_scored - avg_allowed,
        "rolling_total_points": avg_scored + avg_allowed,
        # Weighted features (more recent games weighted higher)
        "rolling_weighted_points_scored": weighted_scored,
        "rolling_weighted_points_allowed": weighted_allowed,
        "rolling_weighted_point_diff": weighted_scored - weighted_allowed,
        # Home performance
        "rolling_home_games": home_games,
        "rolling_home_wins": home_wins,
        "rolling_home_points_scored": home_avg_scored,
        "rolling_home_points_allowed": home_avg_allowed,
        # Away performance
        "rolling_away_games": away_games,
        "rolling_away_wins": away_wins,
        "rolling_away_points_scored": away_avg_scored,
        "rolling_away_points_allowed": away_avg_allowed,
        # Streak features
        "rolling_win_streak": current_streak if streak_type == 'win' else 0,
        "rolling_loss_streak": current_streak if streak_type == 'loss' else 0,
    }


def calculate_matchup_features(home_features: Dict, away_features: Dict) -> Dict[str, Any]:
    """
    Calculate matchup-specific interaction features.
    
    These features capture how teams match up against each other, which is
    more predictive than looking at team stats in isolation.
    
    Args:
        home_features: Dictionary of home team features (prefixed with 'home_')
        away_features: Dictionary of away team features (prefixed with 'away_')
    
    Returns:
        Dictionary of matchup features
    """
    matchup = {}
    
    # Helper function to safely get numeric value
    def safe_get(features: Dict, key: str, default: float = 0.0) -> float:
        val = features.get(key)
        return float(val) if val is not None else default
    
    # === Rating Differentials ===
    # Overall team strength differentials (home advantage is implicit in the diff)
    matchup["matchup_sp_diff"] = safe_get(home_features, "home_sp_rating") - safe_get(away_features, "away_sp_rating")
    matchup["matchup_elo_diff"] = safe_get(home_features, "home_elo_rating") - safe_get(away_features, "away_elo_rating")
    matchup["matchup_fpi_diff"] = safe_get(home_features, "home_fpi_rating") - safe_get(away_features, "away_fpi_rating")
    matchup["matchup_srs_diff"] = safe_get(home_features, "home_srs_rating") - safe_get(away_features, "away_srs_rating")
    
    # === Offense vs Defense Matchups ===
    # Home offense vs Away defense (positive = home offense advantage)
    matchup["matchup_home_off_vs_away_def_ppa"] = (
        safe_get(home_features, "home_offense_ppa") - safe_get(away_features, "away_defense_ppa")
    )
    matchup["matchup_home_off_vs_away_def_sp"] = (
        safe_get(home_features, "home_sp_offense") + safe_get(away_features, "away_sp_defense")  # Note: defensive SP+ is negative for good defense
    )
    
    # Away offense vs Home defense (positive = away offense advantage)
    matchup["matchup_away_off_vs_home_def_ppa"] = (
        safe_get(away_features, "away_offense_ppa") - safe_get(home_features, "home_defense_ppa")
    )
    matchup["matchup_away_off_vs_home_def_sp"] = (
        safe_get(away_features, "away_sp_offense") + safe_get(home_features, "home_sp_defense")
    )
    
    # === Style Matchups (Rush vs Rush Defense, Pass vs Pass Defense) ===
    # Home rushing attack vs away rush defense
    matchup["matchup_home_rush_vs_away_rush_def"] = (
        safe_get(home_features, "home_offense_rushing_plays_ppa") - 
        safe_get(away_features, "away_defense_rushing_plays_ppa")
    )
    
    # Home passing attack vs away pass defense
    matchup["matchup_home_pass_vs_away_pass_def"] = (
        safe_get(home_features, "home_offense_passing_plays_ppa") - 
        safe_get(away_features, "away_defense_passing_plays_ppa")
    )
    
    # Away rushing attack vs home rush defense
    matchup["matchup_away_rush_vs_home_rush_def"] = (
        safe_get(away_features, "away_offense_rushing_plays_ppa") - 
        safe_get(home_features, "home_defense_rushing_plays_ppa")
    )
    
    # Away passing attack vs home pass defense
    matchup["matchup_away_pass_vs_home_pass_def"] = (
        safe_get(away_features, "away_offense_passing_plays_ppa") - 
        safe_get(home_features, "home_defense_passing_plays_ppa")
    )
    
    # === Success Rate Matchups ===
    matchup["matchup_home_success_vs_away_def_success"] = (
        safe_get(home_features, "home_offense_success_rate") - 
        safe_get(away_features, "away_defense_success_rate")
    )
    matchup["matchup_away_success_vs_home_def_success"] = (
        safe_get(away_features, "away_offense_success_rate") - 
        safe_get(home_features, "home_defense_success_rate")
    )
    
    # === Explosiveness Matchups ===
    matchup["matchup_home_explosiveness_vs_away_def"] = (
        safe_get(home_features, "home_offense_explosiveness") - 
        safe_get(away_features, "away_defense_explosiveness")
    )
    matchup["matchup_away_explosiveness_vs_home_def"] = (
        safe_get(away_features, "away_offense_explosiveness") - 
        safe_get(home_features, "home_defense_explosiveness")
    )
    
    # === Recruiting/Talent Differential ===
    matchup["matchup_recruiting_diff"] = (
        safe_get(home_features, "home_recruiting_points") - 
        safe_get(away_features, "away_recruiting_points")
    )
    
    # === Rolling Performance Differentials ===
    matchup["matchup_rolling_point_diff"] = (
        safe_get(home_features, "home_rolling_point_diff") - 
        safe_get(away_features, "away_rolling_point_diff")
    )
    matchup["matchup_rolling_win_pct_diff"] = (
        safe_get(home_features, "home_rolling_win_pct") - 
        safe_get(away_features, "away_rolling_win_pct")
    )
    
    # === Weighted Rolling Performance Differentials ===
    matchup["matchup_weighted_point_diff"] = (
        safe_get(home_features, "home_rolling_weighted_point_diff") - 
        safe_get(away_features, "away_rolling_weighted_point_diff")
    )
    
    # === Streak Differential ===
    # Positive = home team on win streak, negative = away team on win streak
    matchup["matchup_streak_diff"] = (
        safe_get(home_features, "home_rolling_win_streak") - 
        safe_get(home_features, "home_rolling_loss_streak") -
        safe_get(away_features, "away_rolling_win_streak") + 
        safe_get(away_features, "away_rolling_loss_streak")
    )
    
    return matchup


def merge_game_features(game: Dict, team_lookup: Dict[str, Dict], 
                       home_rolling: Dict, away_rolling: Dict,
                       betting_lines: Dict[int, Dict]) -> Dict[str, Any]:
    """
    Merge all features for a single game into one row
    """
    features = {}
    
    # Game identifiers (using camelCase from API)
    game_id = game.get("id")
    features["game_id"] = game_id
    features["season"] = game.get("season")
    features["week"] = game.get("week")
    features["date"] = game.get("startDate")
    features["home_team"] = game.get("homeTeam")
    features["away_team"] = game.get("awayTeam")
    features["neutral_site"] = 1 if game.get("neutralSite") else 0
    features["conference_game"] = 1 if game.get("conferenceGame") else 0
    
    home_team = game.get("homeTeam")
    away_team = game.get("awayTeam")
    
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
    
    # Calculate matchup-specific interaction features
    home_features = {k: v for k, v in features.items() if k.startswith('home_')}
    away_features = {k: v for k, v in features.items() if k.startswith('away_')}
    matchup_features = calculate_matchup_features(home_features, away_features)
    features.update(matchup_features)
    
    # Target variables (actual scores) - using camelCase from API
    features["home_score"] = game.get("homePoints")
    features["away_score"] = game.get("awayPoints")
    
    return features


# ============================================================================
# MAIN PROCESSING PIPELINE
# ============================================================================

def process_season(year: int, prior_year_data: Optional[Dict] = None) -> List[Dict]:
    """
    Process a complete season: fetch all data and create training rows
    
    Uses PRIOR SEASON's ratings (SP+, SRS, ELO, FPI, etc.) to prevent data leakage.
    Season-aggregate stats like SP+ are computed at end of season, so using current
    season's ratings for all games would be using future information.
    
    Args:
        year: Season year to process
        prior_year_data: Optional pre-fetched data from prior season to avoid duplicate API calls
    """
    print(f"\n{'='*70}")
    print(f"PROCESSING SEASON {year}")
    print(f"{'='*70}")
    
    # Fetch current season games
    games = fetch_season_games(year)
    if not games:
        print(f"Skipping {year} - no games found")
        return []
    
    # Use PRIOR SEASON for ratings to prevent data leakage
    # These are end-of-season aggregates that shouldn't be known during the season
    prior_year = year - 1
    print(f"  📊 Using prior season ({prior_year}) for team ratings (prevents data leakage)")
    
    if prior_year_data:
        # Use pre-fetched prior year data
        advanced_stats = prior_year_data.get('advanced_stats', {})
        ppa_data = prior_year_data.get('ppa_data', {})
        sp_ratings = prior_year_data.get('sp_ratings', {})
        srs_ratings = prior_year_data.get('srs_ratings', {})
        elo_ratings = prior_year_data.get('elo_ratings', {})
        fpi_ratings = prior_year_data.get('fpi_ratings', {})
        recruiting = prior_year_data.get('recruiting', {})
    else:
        # Fetch prior season ratings (prevents data leakage)
        advanced_stats = fetch_season_advanced_stats(prior_year)
        ppa_data = fetch_season_ppa(prior_year)
        sp_ratings = fetch_season_sp_ratings(prior_year)
        srs_ratings = fetch_season_srs_ratings(prior_year)
        elo_ratings = fetch_season_elo_ratings(prior_year)
        fpi_ratings = fetch_season_fpi_ratings(prior_year)
        # Recruiting uses prior year's class (recruits from year before)
        recruiting = fetch_recruiting_rankings(prior_year)
    
    # Betting lines are game-specific and available before games, so use current season
    betting_lines = fetch_betting_lines(year)
    
    # Build team lookup dictionary using prior year ratings
    print(f"  Building team lookup (from {prior_year} ratings)...")
    team_lookup = build_team_lookup(
        prior_year, advanced_stats, ppa_data, sp_ratings, srs_ratings,
        elo_ratings, fpi_ratings, recruiting
    )
    print(f"  ✓ Team features prepared for {len(team_lookup)} teams")
    
    # Sort games chronologically (using camelCase)
    games_sorted = sorted(games, key=lambda x: (x.get("week", 0), x.get("startDate", "")))
    
    # Process each game
    print(f"  Processing {len(games_sorted)} games...")
    season_data = []
    
    for idx, game in enumerate(games_sorted, 1):
        home_team = game.get("homeTeam")
        away_team = game.get("awayTeam")
        game_date = game.get("startDate", "")
        week = game.get("week")
        
        # Calculate rolling features (only using games before this one)
        home_rolling = calculate_rolling_features(home_team, games_sorted, game_date, window=5)
        away_rolling = calculate_rolling_features(away_team, games_sorted, game_date, window=5)
        
        # Merge all features
        game_features = merge_game_features(
            game, team_lookup, home_rolling, away_rolling, betting_lines
        )
        
        season_data.append(game_features)
        
        # Progress update
        if idx % 100 == 0:
            print(f"    Progress: {idx}/{len(games_sorted)} games")
    
    print(f"  ✓ Completed {len(season_data)} games for {year}")
    return season_data


def fetch_season_ratings(year: int) -> Dict[str, Any]:
    """
    Fetch all season ratings data for a given year.
    Returns dictionary with all rating types that can be passed to process_season.
    """
    return {
        'advanced_stats': fetch_season_advanced_stats(year),
        'ppa_data': fetch_season_ppa(year),
        'sp_ratings': fetch_season_sp_ratings(year),
        'srs_ratings': fetch_season_srs_ratings(year),
        'elo_ratings': fetch_season_elo_ratings(year),
        'fpi_ratings': fetch_season_fpi_ratings(year),
        'recruiting': fetch_recruiting_rankings(year),
    }


def main():
    """
    Main function to orchestrate data collection across all seasons.
    
    Uses prior season ratings to prevent data leakage - each season uses
    the previous season's end-of-year ratings for team statistics.
    """
    global api_call_count
    
    if not CFBD_API_KEY:
        print("ERROR: CFBD_API_KEY not found in environment variables.")
        print(f"Please create a .env file at: {env_path}")
        print("With contents:")
        print("CFBD_API_KEY=your_api_key_here")
        return
    
    print("="*70)
    print("COLLEGE FOOTBALL DATA COLLECTION")
    print("(Using prior season ratings to prevent data leakage)")
    print("="*70)
    print(f"API Base URL: {CFBD_API_BASE_URL}")
    print(f"API Key: {'*' * 10}{CFBD_API_KEY[-4:] if len(CFBD_API_KEY) > 4 else '****'}")
    print(f"Seasons: 2003-2024 (22 seasons)")
    print("="*70)
    
    all_data = []
    years = range(2003, 2025)  # 2003 to 2024 inclusive (22 seasons)
    
    # Pre-fetch first prior year's data (2002 for 2003 season)
    print(f"\n  Pre-fetching 2002 ratings for first season...")
    prior_year_data = fetch_season_ratings(2002)
    
    for year in years:
        try:
            # Use cached prior year data
            season_data = process_season(year, prior_year_data)
            all_data.extend(season_data)
            
            # Cache current year's ratings for next iteration
            # This year's end-of-season ratings become next year's prior season data
            print(f"  Caching {year} ratings for {year + 1} season...")
            prior_year_data = fetch_season_ratings(year)
            
            # Save checkpoint after each season
            if season_data:
                checkpoint_df = pd.DataFrame(all_data)
                checkpoint_file = f"training_data_checkpoint_{year}.csv"
                checkpoint_df.to_csv(checkpoint_file, index=False)
                print(f"  💾 Checkpoint saved: {checkpoint_file}")
        
        except Exception as e:
            print(f"ERROR processing {year}: {e}")
            # Still try to get ratings for this year for next iteration
            try:
                prior_year_data = fetch_season_ratings(year)
            except:
                pass
            continue
    
    # Create final DataFrame
    if not all_data:
        print("\n" + "="*70)
        print("ERROR: No data collected!")
        print("="*70)
        print(f"Total API calls made: {api_call_count}")
        print("\nPossible issues:")
        print("1. API response structure may be different than expected")
        print("2. Check the debug output above for API response details")
        print("3. Verify API key is valid for the endpoints being used")
        
        # Create empty CSV as placeholder
        empty_df = pd.DataFrame()
        output_file = "training_data.csv"
        empty_df.to_csv(output_file, index=False)
        print(f"\n📄 Empty CSV created: {output_file}")
        return
    
    print(f"\n{'='*70}")
    print(f"DATA COLLECTION COMPLETE!")
    print(f"{'='*70}")
    print(f"Total games collected: {len(all_data)}")
    print(f"Total API calls made: {api_call_count}")
    
    df = pd.DataFrame(all_data)
    
    # Sort by season, week, date
    df = df.sort_values(["season", "week", "date"])
    
    # Save final CSV
    output_file = "training_data.csv"
    df.to_csv(output_file, index=False)
    
    print(f"\n📊 Final dataset saved: {output_file}")
    print(f"   Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    
    # Show basic statistics
    print(f"\n📈 Dataset Statistics:")
    print(f"   Seasons: {df['season'].min()} - {df['season'].max()}")
    


if __name__ == "__main__":
    main()
