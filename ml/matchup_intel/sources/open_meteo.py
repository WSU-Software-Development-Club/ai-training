"""Open-Meteo client — free, no API key. Forecast + historical archive.

- archive_daily(): past daily weather by lat/lon (for grounding backfill).
- forecast_daily(): upcoming daily weather (for live game forecasts).
Units are requested in °F / mph / inch so they match score/weather.py directly.
"""

from __future__ import annotations

import time

import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

_DAILY = "temperature_2m_max,temperature_2m_min,wind_speed_10m_max,precipitation_sum"
_UNITS = {
    "temperature_unit": "fahrenheit",
    "wind_speed_unit": "mph",
    "precipitation_unit": "inch",
    "timezone": "auto",
}


def _get_with_retry(url: str, params: dict, timeout: int, max_retries: int = 3) -> dict:
    """GET with polite rate-limiting + backoff (mirrors collect_data's pattern).

    Raises RuntimeError once retries are exhausted (including repeated 429s) —
    a rate-limited/failed request must fail loudly, not silently degrade to
    "zero games" for whatever season/team was being fetched.
    """
    last_status = None
    for attempt in range(max_retries):
        try:
            time.sleep(0.3)  # be gentle on the free tier
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429:
                last_status = 429
                if attempt < max_retries - 1:
                    time.sleep(60)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    f"Open-Meteo request failed after {max_retries} attempts: "
                    f"{url} params={params}"
                ) from exc
            time.sleep(2 ** attempt)
    raise RuntimeError(
        f"Open-Meteo retries exhausted (last status={last_status}) after "
        f"{max_retries} attempts: {url} params={params}"
    )


def _rows_by_date(data: dict) -> dict[str, dict]:
    daily = data.get("daily", {})
    times = daily.get("time", []) or []

    def col(name, i):
        vals = daily.get(name) or []
        return vals[i] if i < len(vals) else None

    out: dict[str, dict] = {}
    for i, day in enumerate(times):
        out[day] = {
            "temp_max_f": col("temperature_2m_max", i),
            "temp_min_f": col("temperature_2m_min", i),
            "wind_mph": col("wind_speed_10m_max", i),
            "precip_in": col("precipitation_sum", i),
        }
    return out


def archive_daily(lat: float, lon: float, start_date: str, end_date: str,
                  timeout: int = 60, timezone: str = "auto") -> dict[str, dict]:
    """{ 'YYYY-MM-DD': {temp_max_f, temp_min_f, wind_mph, precip_in} } for a range,
    keyed by the given IANA timezone's local date. Defaults to "auto" (Open-Meteo
    picks the location's local tz), but callers that need to join against a
    date computed in Python (e.g. a specific stadium's tz) should pass that same
    IANA name explicitly so the join key matches exactly."""
    params = {"latitude": lat, "longitude": lon,
              "start_date": start_date, "end_date": end_date,
              "daily": _DAILY, **_UNITS, "timezone": timezone}
    return _rows_by_date(_get_with_retry(ARCHIVE_URL, params, timeout))


def forecast_daily(lat: float, lon: float, timeout: int = 60) -> dict[str, dict]:
    """Upcoming days' daily weather (for live game forecasts)."""
    params = {"latitude": lat, "longitude": lon, "daily": _DAILY,
              "forecast_days": 16, **_UNITS}
    return _rows_by_date(_get_with_retry(FORECAST_URL, params, timeout))


def daily_to_conditions(day: dict) -> dict:
    """Adapt a daily archive/forecast row to the score/weather.py conditions shape.
    Uses the daily MIN for cold detection and MAX for heat/wind; precip_sum maps
    to a pseudo-probability so the same classify_bucket() applies to both."""
    precip = day.get("precip_in") or 0.0
    # Cold is driven by the low; heat/wind by the high — pick the temp that most
    # affects bucketing (min if it's freezing, else the max).
    tmin = day.get("temp_min_f")
    tmax = day.get("temp_max_f")
    temp = tmin if (tmin is not None and tmin <= 32) else tmax
    return {
        "temp_f": temp,
        "wind_mph": day.get("wind_mph"),
        "precip_prob": 0.8 if precip >= 0.1 else 0.0,
    }
