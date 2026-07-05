"""
Service file for team-specific data like record, ppg, etc.
"""

import os
import re
import unicodedata
from datetime import datetime, timezone

import requests
from api_vars import CFBD_API_BASE_URL, NCAA_API_BASE_URL

# Oldest season the year dropdown offers. CFBD has data well before this, but a
# ~25-season window keeps the list sane and covers the modern era.
EARLIEST_SEASON = 2000


def current_season_year():
    """The football season currently in scope. A CFB season is named for the
    calendar year it starts in and runs Aug–Jan, so from August onward we're in
    the new season; before that the most recent completed season is last year.
    (In July 2026, this returns 2025 — matching what the NCAA feed serves.)"""
    now = datetime.now(timezone.utc)
    return now.year if now.month >= 8 else now.year - 1


def available_seasons():
    """Descending list of seasons the UI can request, newest first."""
    return list(range(current_season_year(), EARLIEST_SEASON - 1, -1))


# NCAA standings abbreviate a school's state with a period ("South Fla.",
# "Central Mich."), while the frontend's team CSV spells it out ("South
# Florida", "Central Michigan"). Expanding these abbreviations to the full word
# on BOTH sides of the comparison makes the two feeds join. Only unambiguous
# state-name abbreviations belong here — a token that could name more than one
# school (e.g. "miss" for Mississippi vs. Southern Miss) is safe because the
# expansion is applied identically to both spellings, so it can never split a
# match, only merge the two spellings of the same word.
_STATE_ABBREVIATIONS = {
    "ala": "alabama",
    "ariz": "arizona",
    "ark": "arkansas",
    "calif": "california",
    "colo": "colorado",
    "conn": "connecticut",
    "fla": "florida",
    "ga": "georgia",
    "ill": "illinois",
    "ind": "indiana",
    "ky": "kentucky",
    "mich": "michigan",
    "minn": "minnesota",
    "miss": "mississippi",
    "okla": "oklahoma",
    "ore": "oregon",
    "tenn": "tennessee",
    "tex": "texas",
    "wash": "washington",
    "wis": "wisconsin",
}

# A handful of schools can't be reconciled by word-level expansion because the
# two feeds use entirely different names: an acronym on one side and the full
# name on the other, or an extra/parenthetical qualifier. These map a
# normalized (already state-expanded) name to a shared canonical key. Applied to
# both the requested name and the standings name, so either spelling resolves.
_TEAM_ALIASES = {
    "fiu": "florida international",
    "niu": "northern illinois",
    "ulm": "ul monroe",
    "army west point": "army",
    "miami fl": "miami",              # standings "Miami (FL)"; keeps Miami (OH) distinct
    "southern california": "usc",
    "hawai i": "hawaii",             # CSV "Hawai'i" -> "hawai i"; standings "Hawaii"
}


def normalize_team_name(name):
    """
    Normalize a team name so different spellings resolve to the same team.

    Different data sources (NCAA standings, the scoreboard feed, and the
    frontend's team CSV) spell the same school differently, e.g.
    "Washington St.", "Washington State", and "washington st". This makes
    comparisons robust to:
      - letter case ("USC" vs "usc")
      - punctuation and accents ("San José St." vs "San Jose St")
      - the "State"/"St." abbreviation (both collapse to a single token)
      - state-name abbreviations ("Fla." -> "florida", "Central Mich." ->
        "central michigan") via {@link _STATE_ABBREVIATIONS}

    Args:
        name (str): Team name to normalize.
    Returns:
        str: A canonical, lowercase, whitespace-collapsed form.
    """
    if not name:
        return ""

    # Strip accents/diacritics (é -> e) so ASCII and non-ASCII spellings match.
    stripped = "".join(
        c
        for c in unicodedata.normalize("NFKD", str(name))
        if not unicodedata.combining(c)
    )

    lowered = stripped.lower()
    # Replace any non-alphanumeric character (periods, parens, etc.) with space.
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)

    tokens = []
    for token in cleaned.split():
        # Treat "state" and "st" as the same word so "Washington State" matches
        # "Washington St.".
        if token == "state":
            token = "st"
        else:
            token = _STATE_ABBREVIATIONS.get(token, token)
        tokens.append(token)

    return " ".join(tokens)


def canonical_team_key(name):
    """Normalized team name with acronym/special-case aliases folded in, so two
    feeds that name the same school entirely differently (e.g. "FIU" vs.
    "Florida International") still compare equal. Use this for cross-feed team
    lookups; use {@link normalize_team_name} when you only need spelling
    normalization."""
    normalized = normalize_team_name(name)
    return _TEAM_ALIASES.get(normalized, normalized)


def get_team_record(team_name, year=None):
    """
    Fetch a team's season record.

    The current season comes from the NCAA standings feed (richest data: points
    for/against and current streak). Any earlier season comes from the College
    Football Data API, which supplies win/loss splits but not points or streak —
    those fields are returned as None for past years.

    Args:
        team_name (str): Team name (required).
        year (int, optional): Season to fetch. Defaults to the current season.
    Returns:
        dict or None: Team record row (NCAA standings shape) or None if not
        found / the upstream fetch failed.
    """
    season = year or current_season_year()
    if int(season) == current_season_year():
        return _get_team_record_ncaa(team_name)
    return _get_team_record_cfbd(team_name, int(season))


def _get_team_record_ncaa(team_name):
    """Current-season record from the NCAA standings feed."""
    try:
        response = requests.get(f'{NCAA_API_BASE_URL}/standings/football/fbs', timeout=10)
        response.raise_for_status()
        raw_data = response.json()
        target = canonical_team_key(team_name)
        for conf_block in raw_data.get('data', []):
            for row in conf_block.get('standings', []):
                school = row.get("School", "")
                if canonical_team_key(school) == target:
                    return row
        return None

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
        return None


def _wl(games):
    """Format a CFBD wins/losses block as a "W-L" string, or None if absent."""
    if not games:
        return None
    return f"{games.get('wins', 0)}-{games.get('losses', 0)}"


def _cfbd_get(path, params, api_key):
    """GET a CFBD endpoint with the Bearer token. Returns parsed JSON, or None
    on any network/parse failure."""
    try:
        response = requests.get(
            f'{CFBD_API_BASE_URL}/{path}',
            params=params,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"CFBD request error occurred: {e}")
        return None
    except ValueError:
        return None


def _cfbd_points_and_streak(team_name, year, api_key):
    """Points for/against and the end-of-season streak for a team, computed from
    that season's completed games (CFBD /records carries none of these).

    Returns (points_for, points_against, streak) where streak is a string like
    "Won 3"/"Lost 4" matching the NCAA feed's format, or (None, None, None) if
    the games can't be fetched or none are completed."""
    games = _cfbd_get("games", {"year": year, "team": team_name, "seasonType": "both"}, api_key)
    if not games:
        return None, None, None

    played = [
        g for g in games
        if g.get("completed")
        and g.get("homePoints") is not None
        and g.get("awayPoints") is not None
    ]
    if not played:
        return None, None, None

    played.sort(key=lambda g: g.get("startDate") or "")
    points_for = points_against = 0
    results = []  # "W" / "L" / "T" in chronological order
    for g in played:
        is_home = g.get("homeTeam") == team_name
        mine, opp = (
            (g["homePoints"], g["awayPoints"]) if is_home
            else (g["awayPoints"], g["homePoints"])
        )
        points_for += mine
        points_against += opp
        results.append("W" if mine > opp else "L" if mine < opp else "T")

    # Trailing run of the most recent result → "Won N" / "Lost N" / "Tied N".
    last = results[-1]
    run = 0
    for r in reversed(results):
        if r != last:
            break
        run += 1
    label = {"W": "Won", "L": "Lost", "T": "Tied"}[last]
    return points_for, points_against, f"{label} {run}"


def _get_team_record_cfbd(team_name, year):
    """Historical (past-season) record from the College Football Data API,
    reshaped to the NCAA standings row the frontend already renders. Win/loss
    splits come from /records; points for/against and the streak are derived
    from that season's games (see {@link _cfbd_points_and_streak}).

    Returns None if the CFBD key is unset, the request fails, or the team has no
    record for that season. CFBD team names match the frontend CSV school names,
    so the requested name is passed through directly."""
    api_key = os.environ.get('CFBD_API_KEY')
    if not api_key:
        print("CFBD_API_KEY not set — cannot fetch historical team records.")
        return None

    rows = _cfbd_get("records", {"year": year, "team": team_name}, api_key)
    if not rows:
        return None

    rec = rows[0]
    total = rec.get("total") or {}
    conf = rec.get("conferenceGames") or {}
    # CFBD names the team consistently across endpoints; use its spelling so the
    # per-game home/away comparison in the points/streak helper lines up.
    cfbd_team = rec.get("team", team_name)
    points_for, points_against, streak = _cfbd_points_and_streak(cfbd_team, year, api_key)
    return {
        "School": cfbd_team,
        "Conference W": conf.get("wins", 0),
        "Conference L": conf.get("losses", 0),
        "Overall W": total.get("wins", 0),
        "Overall L": total.get("losses", 0),
        "Overall PF": points_for,
        "Overall PA": points_against,
        "Overall HOME": _wl(rec.get("homeGames")),
        "Overall AWAY": _wl(rec.get("awayGames")),
        "Overall STREAK": streak,
        "year": rec.get("year", year),
    }


def get_all_teams():
    """
    Fetch all teams with their conferences and records from NCAA API standings
    
    Returns:
        list or None: List of team dictionaries with name, conference, record, and stats, or None if error occurred
    """
    try:
        response = requests.get(f'{NCAA_API_BASE_URL}/standings/football/fbs', timeout=10)
        response.raise_for_status()
        raw_data = response.json()
        
        teams = []
        for conf_block in raw_data.get('data', []):
            # Handle conference field - it can be a string or an object
            conference_obj = conf_block.get('conference', {})
            if isinstance(conference_obj, dict):
                conference_name = conference_obj.get('name', '')
                conference_seo = conference_obj.get('seo', '')
                # Prefer SEO format to match HomePage format, fallback to name
                conference = conference_seo or conference_name or 'Independent'
            else:
                # If conference is a string, use it directly
                conference = conference_obj if conference_obj else 'Independent'
            
            for row in conf_block.get('standings', []):
                school = row.get("School", "")
                # Use "Overall W" and "Overall L" from API response
                wins = int(row.get("Overall W", 0) or 0)
                losses = int(row.get("Overall L", 0) or 0)
                ties = int(row.get("Ties", 0) or 0)
                
                # Format record as "W-L" or "W-L-T" if ties exist
                if ties > 0:
                    record = f"{wins}-{losses}-{ties}"
                else:
                    record = f"{wins}-{losses}"
                
                # Get all available stats from API
                games_played = wins + losses + ties
                overall_pf = float(row.get("Overall PF", 0) or 0)
                overall_pa = float(row.get("Overall PA", 0) or 0)
                
                # Calculate PPG and PAPG if games played > 0
                if games_played > 0:
                    points_per_game = round(overall_pf / games_played, 1)
                    points_allowed = round(overall_pa / games_played, 1)
                else:
                    points_per_game = 0.0
                    points_allowed = 0.0
                
                # Get all other available fields
                conference_w = row.get("Conference W", "")
                conference_l = row.get("Conference L", "")
                overall_home = row.get("Overall HOME", "")
                overall_away = row.get("Overall AWAY", "")
                overall_streak = row.get("Overall STREAK", "")
                
                # Total yards per game might not be in standings, set to 0.0
                total_yards = float(row.get("Total Yards Per Game", 0) or 0)
                
                team_data = {
                    'id': len(teams) + 1,  # Simple ID based on order
                    'name': school,
                    'conference': conference,
                    'record': record,
                    'stats': {
                        'pointsPerGame': round(points_per_game, 1) if points_per_game else 0.0,
                        'pointsAllowed': round(points_allowed, 1) if points_allowed else 0.0,
                        'totalYards': round(total_yards, 1) if total_yards else 0.0,
                        'overallPF': int(overall_pf) if overall_pf else 0,
                        'overallPA': int(overall_pa) if overall_pa else 0,
                        'conferenceW': conference_w,
                        'conferenceL': conference_l,
                        'conferenceRecord': f"{conference_w}-{conference_l}" if conference_w and conference_l else "",
                        'overallHome': overall_home,
                        'overallAway': overall_away,
                        'overallStreak': overall_streak,
                    }
                }
                teams.append(team_data)
        
        return teams

    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error occurred: {e}")
        return None