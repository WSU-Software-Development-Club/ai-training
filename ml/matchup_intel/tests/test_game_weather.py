"""Unit tests for the observed-weather-per-game payload builder (pure logic)."""

from __future__ import annotations

from datetime import datetime, timezone

from ml.matchup_intel.ingest.game_weather import build_payload

_AS_OF = datetime(2025, 12, 31, 12, 0, tzinfo=timezone.utc)


def test_build_payload_dry_conditions():
    conditions = {"temp_f": 21.8, "wind_mph": 15.0, "precip_prob": 0.0}
    payload = build_payload("Ohio State", conditions, _AS_OF)

    assert payload["conditions"] is conditions
    assert "Ohio State" in payload["text"]
    assert "~22°F" in payload["text"]        # rounded temp
    assert "wind 15 mph" in payload["text"]
    assert "dry" in payload["text"]
    # provenance: a single self-referential weather source, stamped at as_of
    assert len(payload["sources"]) == 1
    src = payload["sources"][0]
    assert src["source_type"] == "weather"
    assert src["published_at"] == _AS_OF.isoformat()


def test_build_payload_wet_when_precip_high():
    conditions = {"temp_f": 59.4, "wind_mph": 9.5, "precip_prob": 0.8}
    payload = build_payload("Mississippi State", conditions, _AS_OF)
    assert "wet" in payload["text"]


def test_build_payload_treats_missing_precip_as_dry():
    conditions = {"temp_f": 60.0, "wind_mph": 10.0}  # no precip_prob key
    payload = build_payload("Georgia", conditions, _AS_OF)
    assert "dry" in payload["text"]
