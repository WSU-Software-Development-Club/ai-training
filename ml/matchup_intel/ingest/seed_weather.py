"""Seed the weather slice's current-game FORECAST signals (Layer 0).

Off-season there are no real upcoming games to forecast, so these two forecasts
are seeded to give the demo games something to score. The historical grounding
store (weather_history) is populated separately and for real by
ingest/weather_backfill.py (real results x Open-Meteo archive) — NOT here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import db

# (ncaa_game_id, team display name, forecast conditions, kickoff). The WSU
# forecast is windy and OSU cold so the two demo games hit different buckets.
_FORECASTS = [
    # Cold WSU game -> real 'cold' history is 24 games (< 30) -> rate WITHHELD.
    (990001, "Washington State",
     {"temp_f": 30, "wind_mph": 10, "precip_prob": 0.1,
      "description": "Cold, around 30°F at kickoff"},
     "2024-10-12T19:30:00Z"),
    # Rainy OSU game -> real 'rain' history is 43 games (>= 30) -> rate SERVED.
    (990002, "Oregon State",
     {"temp_f": 55, "wind_mph": 10, "precip_prob": 0.85,
      "description": "Steady rain likely through kickoff"},
     "2024-10-12T23:00:00Z"),
]


def ingest_weather_seed(conn) -> dict:
    observed = datetime(2024, 10, 11, 12, 0, tzinfo=timezone.utc)  # forecast pulled the day before
    signals = 0
    for ncaa_game_id, team, conditions, _kickoff in _FORECASTS:
        team_id = db.upsert_team(conn, team)
        payload = {
            "category": "weather",
            "text": f"Forecast for {team}: {conditions['description']}.",
            "conditions": conditions,
            "sources": [{
                "url": "https://open-meteo.com/",
                "source_type": "weather",
                "snippet": conditions["description"],
                "published_at": observed.isoformat(),
            }],
        }
        raw_id = db.insert_raw_signal(
            conn, source_type="weather", payload=payload,
            as_of_timestamp=observed, published_at=observed,
            source_name="Open-Meteo (seed forecast)", source_url="https://open-meteo.com/",
            team_id=team_id, ncaa_game_id=ncaa_game_id,
        )
        if raw_id:
            signals += 1

    db.set_watermark(conn, "seed_weather", cursor=str(len(_FORECASTS)))
    return {"weather_signals": signals}
