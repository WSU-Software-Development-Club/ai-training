"""Seed the weather slice (Layer 0 + historical store).

Adds:
  - current-game weather forecast raw_signals (source_type='weather'), and
  - weather_history rows deliberately sized to demonstrate BOTH sides of the
    sample-size guard:
      * Washington State / wind  -> 40 games (>= threshold): rate WILL be served
      * Oregon State / cold      ->  8 games (<  threshold): rate WITHHELD

Later this is replaced by CFBD results x Open-Meteo archive by stadium coords;
the schema + scorer + grounder are identical.
"""

from __future__ import annotations

from datetime import datetime, timezone

from .. import db

# (ncaa_game_id, team display name, forecast conditions, kickoff)
_FORECASTS = [
    (990001, "Washington State",
     {"temp_f": 54, "wind_mph": 28, "precip_prob": 0.2,
      "description": "Blustery, sustained winds 25-30 mph"},
     "2024-10-12T19:30:00Z"),
    (990002, "Oregon State",
     {"temp_f": 28, "wind_mph": 8, "precip_prob": 0.1,
      "description": "Cold and clear, around 28°F at kickoff"},
     "2024-10-12T23:00:00Z"),
]

# team -> (bucket, [(season, won), ...])  sized around the default threshold (30)
_HISTORY = {
    "Washington State": ("wind", [(2010 + i, i % 3 != 0) for i in range(40)]),   # ~27/40 wins, n=40
    "Oregon State":     ("cold", [(2016 + i, i % 2 == 0) for i in range(8)]),    # 4/8 wins, n=8
}


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
            source_name="Open-Meteo (seed)", source_url="https://open-meteo.com/",
            team_id=team_id, ncaa_game_id=ncaa_game_id,
        )
        if raw_id:
            signals += 1

    hist_rows = 0
    for team, (bucket, results) in _HISTORY.items():
        team_id = db.upsert_team(conn, team)
        db.reset_weather_history(conn, team_id, bucket)   # idempotent re-seed
        db.insert_weather_history_bulk(conn, team_id, bucket, results, source="seed")
        hist_rows += len(results)

    db.set_watermark(conn, "seed_weather", cursor=str(len(_FORECASTS)))
    return {"weather_signals": signals, "history_rows": hist_rows}
