"""Layer-2 weather scorer: buckets + calibrated, monotonic magnitudes (no LLM)."""

from __future__ import annotations

from ml.matchup_intel.score.weather import classify_bucket, score_weather


def test_buckets():
    assert classify_bucket({"wind_mph": 25, "temp_f": 40}) == "wind"      # wind wins
    assert classify_bucket({"wind_mph": 5, "temp_f": 30}) == "cold"
    assert classify_bucket({"wind_mph": 5, "temp_f": 95}) == "heat"
    assert classify_bucket({"wind_mph": 5, "temp_f": 60, "precip_prob": 0.8}) == "rain"
    assert classify_bucket({"wind_mph": 5, "temp_f": 65, "precip_prob": 0.1}) == "clear"


def test_clear_is_neutral_low_magnitude():
    s = score_weather({"wind_mph": 4, "temp_f": 68, "precip_prob": 0.0})
    assert s.direction == "neutral"
    assert s.magnitude <= 0.15


def test_adverse_weather_is_headwind():
    s = score_weather({"wind_mph": 30, "temp_f": 50})
    assert s.direction == "headwind"
    assert s.bucket == "wind"
    assert 0.0 <= s.magnitude <= 1.0


def test_magnitude_is_monotonic_in_severity():
    mild = score_weather({"wind_mph": 22})
    gnarly = score_weather({"wind_mph": 45})
    assert gnarly.magnitude > mild.magnitude


def test_magnitude_always_bounded():
    for w in (20, 60, 100):
        s = score_weather({"wind_mph": w})
        assert 0.0 <= s.magnitude <= 1.0
