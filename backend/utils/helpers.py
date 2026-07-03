"""Simple utility functions"""

import logging
from datetime import date

def setup_logging():
    """Setup basic logging"""
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)


def get_current_season_year(today: date = None) -> int:
    """CFB season year for 'no ?year given' defaults.

    Mirrors the frontend's getCurrentYear (frontend/src/utils/helpers.js):
    Jan-Jul roll back to the previous season (the season that just finished
    postseason play); Aug onward is the season currently in progress. Using
    the plain calendar year here would silently query the wrong season
    during the offseason.
    """
    today = today or date.today()
    if today.month < 8:
        return today.year - 1
    return today.year
