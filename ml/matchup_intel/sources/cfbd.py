"""College Football Data API client — the teams/venues dimension source.

Authenticated (Bearer CFBD_API_KEY), read-only. Mirrors the retry/backoff +
rate-limit pattern in ml/training_data/collect_data.py, kept dependency-free.

Only the pieces the matchup engine needs live here: the FBS team list, which
CFBD returns WITH its nested venue ``location`` (lat/lon, IANA timezone, venue
name) — so one call yields the full teams dimension the weather backfill needs.
The key is passed in explicitly (from Config) rather than read from the module
env, so this stays a pure client with no import-time secret access.
"""

from __future__ import annotations

import time
from typing import Optional

import requests

CFBD_API_BASE_URL = "https://api.collegefootballdata.com"

_REQUEST_DELAY = 0.11  # ~10 req/s ceiling, matching collect_data.py


def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}


def _get_with_retry(
    url: str, api_key: str, params: Optional[dict], timeout: int, max_retries: int = 3
):
    """GET with rate-limiting + 429/backoff. Returns parsed JSON, or None on a
    404. Raises RuntimeError once retries are exhausted — the teams dimension is
    a required foundation, so a persistent failure must fail loudly rather than
    silently seed an empty/partial teams table."""
    headers = _headers(api_key)
    for attempt in range(max_retries):
        try:
            time.sleep(_REQUEST_DELAY)
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            if resp.status_code == 429:
                if attempt < max_retries - 1:
                    time.sleep(60)
                    continue
            elif resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"CFBD request failed after {max_retries} attempts: {url} "
                    f"params={params}"
                ) from exc
            time.sleep(2 ** attempt)
    raise RuntimeError(
        f"CFBD retries exhausted after {max_retries} attempts: {url} params={params}"
    )


def fetch_fbs_teams(api_key: str, year: int, timeout: int = 30) -> list[dict]:
    """All FBS teams for a season, each with its nested venue ``location``.

    Returns the raw CFBD team objects (list of dicts). Relevant fields:
        id, school, conference,
        location: {venue, latitude, longitude, timezone, dome, ...}
    ``[]`` if CFBD returns nothing (404/empty)."""
    data = _get_with_retry(
        f"{CFBD_API_BASE_URL}/teams/fbs",
        api_key,
        {"year": year},
        timeout,
    )
    return data if isinstance(data, list) else []


def team_venue(team: dict) -> dict:
    """Flatten one CFBD team object into the fields the teams dimension stores.

    Returns {name, cfbd_id, conference, venue_name, lat, lon, timezone}. lat/lon/
    timezone are None when CFBD has no venue on file for the team (e.g. a program
    with no stadium record) — the caller stores the team either way; only the
    weather backfill needs coords, and it already skips coord-less teams."""
    loc = team.get("location") or {}
    return {
        "name": team.get("school"),
        "cfbd_id": team.get("id"),
        "conference": team.get("conference"),
        "venue_name": loc.get("venue"),
        "lat": loc.get("latitude"),
        "lon": loc.get("longitude"),
        "timezone": loc.get("timezone"),
    }
