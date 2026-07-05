"""
Scoreboard service for fetching NCAA football game data by week
Includes predictions from the Postgres database when available
"""

import os
from datetime import datetime

import requests
from api_vars import CFBD_API_BASE_URL, NCAA_API_BASE_URL
from services.team_service import canonical_team_key
from utils.db import get_db
from utils.helpers import get_current_season_year

def process_games(raw_data: dict, predictions_map: dict = None, season: int = None, week: int = None, db=None):
    """
    Process games and include predictions if available

    Args:
        raw_data: Raw game data from NCAA API
        predictions_map: Dictionary mapping ncaa_game_id to predictions (fast-path
            lookup; pre-filtered by season/week by the caller, so it can miss
            rows whose stored week numbering doesn't match - see db fallback below)
        season: Season year requested (debug logging only - not used for matching)
        week: Week number requested (debug logging only - not used for matching)
        db: PredictionsDB instance for the id-only fallback lookup (matches on the
            UNIQUE ncaa_game_id alone, so it's unaffected by week-numbering
            mismatches between the ML writer and the NCAA scoreboard)
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
        
        # Add prediction if available - match by NCAA game ID alone.
        # ncaa_game_id is UNIQUE in the predictions table (db/schema.sql), so
        # it's a precise match on its own; gating on season/week additionally
        # is wrong because the ML writer's week numbering (CFBD week, with
        # postseason stored as cfbd_week+15) does not line up with the NCAA
        # scoreboard's display week.
        prediction = None
        if ncaa_game_id:
            # First try quick lookup from predictions_map
            if ncaa_game_id in predictions_map:
                prediction = predictions_map[ncaa_game_id]
                print(f"Debug: ✓ Prediction found in map for NCAA game ID: {ncaa_game_id}")

            # If not found in map, try direct lookup (fallback)
            if prediction is None and db and db.is_connected:
                prediction = db.get_prediction_by_ncaa_game_id(ncaa_game_id)
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
        

def _iso_to_epoch(iso):
    """Convert a CFBD ISO-8601 startDate to a Unix epoch (seconds), or None."""
    if not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp())
    except (ValueError, AttributeError):
        return None


def _fetch_cfbd_games(year, week):
    """Fetch a week's FBS games from CFBD (schedule source when the NCAA feed
    has none — e.g. a future season). Returns a list, or [] on any miss."""
    api_key = os.environ.get("CFBD_API_KEY")
    if not api_key:
        return []
    try:
        resp = requests.get(
            f"{CFBD_API_BASE_URL}/games",
            params={"year": year, "week": week, "seasonType": "regular",
                    "classification": "fbs"},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json() or []
    except (requests.exceptions.RequestException, ValueError):
        return []


def _build_games_from_cfbd(cfbd_games, predictions_by_name):
    """Shape CFBD games into the scoreboard game dicts the frontend renders.

    CFBD carries no NCAA game id, so predictions (and the ncaa_game_id that
    powers the matchup link) are matched by normalized home/away team name from
    `predictions_by_name` — keyed (canonical_home, canonical_away)."""
    games = []
    for g in cfbd_games:
        home_name = g.get("homeTeam") or ""
        away_name = g.get("awayTeam") or ""
        completed = bool(g.get("completed"))
        home_pts = g.get("homePoints")
        away_pts = g.get("awayPoints")

        game_data = {
            "game_state": {
                "isUpcoming": not completed,
                "isLive": False,   # CFBD schedule has no in-progress state
                "isFinished": completed,
            },
            "away": {
                "score": away_pts if away_pts is not None else None,
                "names": {"full": away_name, "short": away_name, "char6": away_name},
                "rank": None,
                "conference": g.get("awayConference"),
            },
            "home": {
                "score": home_pts if home_pts is not None else None,
                "names": {"full": home_name, "short": home_name, "char6": home_name},
                "rank": None,
                "conference": g.get("homeConference"),
            },
            "epoch": _iso_to_epoch(g.get("startDate")),
        }

        pred = predictions_by_name.get(
            (canonical_team_key(home_name), canonical_team_key(away_name))
        )
        if pred:
            game_data["prediction"] = {
                "id": pred.get("id"),
                "game_id": pred.get("game_id"),
                "ncaa_game_id": pred.get("ncaa_game_id"),
                "season": pred.get("season"),
                "week": pred.get("week"),
                "game_date": pred.get("game_date"),
                "home_team": pred.get("home_team"),
                "away_team": pred.get("away_team"),
                "home_score": pred.get("predicted_home_score"),
                "away_score": pred.get("predicted_away_score"),
                "winner": pred.get("predicted_winner"),
                "margin": pred.get("predicted_margin"),
                "predicted_total": pred.get("predicted_total"),
                "betting_over_under": pred.get("betting_over_under"),
                "over_probability": pred.get("over_probability"),
                "under_probability": pred.get("under_probability"),
                "neutral_site": pred.get("neutral_site", False),
                "predicted_at": pred.get("prediction_made_at"),
                "created_at": pred.get("created_at"),
            }

        games.append(game_data)
    return games


def _cfbd_scoreboard_fallback(week, year):
    """Build the scoreboard payload from CFBD for a week the NCAA feed doesn't
    cover (e.g. a season NCAA.com hasn't published yet). Returns the same
    game_data shape as the NCAA path, or None when CFBD also has nothing."""
    cfbd_games = _fetch_cfbd_games(year, week)
    if not cfbd_games:
        return None

    # Match any stored predictions for this week by team name (CFBD games have
    # no NCAA id to join on).
    predictions_by_name = {}
    try:
        db = get_db()
        if db.is_connected:
            for pred in db.get_predictions_by_week(year, week):
                if pred.get("season") == year and pred.get("week") == week:
                    key = (canonical_team_key(pred.get("home_team")),
                           canonical_team_key(pred.get("away_team")))
                    predictions_by_name[key] = pred
    except Exception as e:
        print(f"Warning: Could not fetch predictions for CFBD fallback: {e}")

    processed_games = _build_games_from_cfbd(cfbd_games, predictions_by_name)
    return {
        "week": week,
        "year": year,
        "updatedAt": None,
        "games": processed_games,
        "totalGames": len(cfbd_games),
        "hasPredictions": any("prediction" in g for g in processed_games),
        "source": "cfbd",   # flag so callers/UI know this is schedule-only data
    }


def get_scoreboard_data(week, year=None):
    """
    Args:
        week (int): Week number (required)
        year (int, optional): Season year. Defaults to the current CFB season
            year (not the calendar year - see get_current_season_year), so an
            offseason (Jan-Jul) call without an explicit year queries the
            season that just finished rather than the season that hasn't
            started yet.
    Returns:
        dict or None: Scoreboard data or None if error occurred

        Data Processing: Loop through games and extract/format each one
        Includes predictions from the Postgres database if available
    """
    if year is None:
        year = get_current_season_year()
    try:
        # Fetch scoreboard data from NCAA API
        raw_response = requests.get(f"{NCAA_API_BASE_URL}/scoreboard/football/fbs/{year}/{week:02d}/all-conf", timeout=10)
        raw_response.raise_for_status()
        raw_data = raw_response.json()

        # The NCAA feed only publishes the current/most-recent season, so a
        # future season (or any week it hasn't posted) comes back empty. Fall
        # back to the CFBD schedule so those games still show (schedule-only —
        # no live scores until NCAA posts them).
        if not raw_data.get("games"):
            fallback = _cfbd_scoreboard_fallback(week, year)
            if fallback is not None:
                return fallback

        # Fetch predictions from the database
        predictions_map = {}
        db = None
        try:
            db = get_db()
            if db.is_connected:
                predictions = db.get_predictions_by_week(year, week)
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
        
        # Process games with predictions, passing season, week, and db for precise matching
        processed_games = process_games(raw_data, predictions_map, season=year, week=week, db=db)

        game_data = {
            'week': week,
            'year': year,
            'updatedAt': raw_data.get('updated_at'),
            'games': processed_games,
            'totalGames': len(raw_data.get('games', [])),
            # Derived from what actually attached (not from predictions_map,
            # which is pre-filtered by season/week and can under-count when a
            # prediction's stored week numbering doesn't match the scoreboard's).
            'hasPredictions': any('prediction' in g for g in processed_games)
        }

        return game_data

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        # A future/unpublished week can 404 on the NCAA feed — try CFBD before
        # giving up so a season NCAA.com hasn't posted yet still populates.
        fallback = _cfbd_scoreboard_fallback(week, year)
        if fallback is not None:
            return fallback
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
    return None