"""
Service file for team-specific data like record, ppg, etc.
"""

def normalize_team_name(name):
    """
    Normalize a team name for comparisons on case the name is not always consistent.

    Has to be implemented after frontend methods are implemented.
    """
    raise NotImplementedError


def get_team_record(team_name):
    """
    Expected return shape (example):
    {
        "school": str,
        "conference": str,
        "conference_w": str,
        "conference_l": str,
        "overall_w": str,
        "overall_l": str,
        "overall_pf": str,
        "overall_pa": str,
        "home": str,
        "away": str,
        "streak": str,
        "updated": str,
    }
    """
    raise NotImplementedError

