"""Weather factor scorer (Layer 2) — pure, deterministic, no LLM.

Turns a forecast into (bucket, direction, magnitude, confidence, explanation).
Magnitude comes from condition severity via a calibrated rubric; the LLM is
never asked to judge it. The historical grounder (ground.ground_weather_factor)
later attaches the team's actual win-rate in that bucket, gated by the guard.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherScore:
    bucket: str            # cold | wind | rain | heat | clear
    direction: str         # tailwind | headwind | neutral
    magnitude: float       # 0..1
    confidence: float      # 0..1
    explanation: str


def classify_bucket(conditions: dict) -> str:
    """Map a forecast to a single dominant weather bucket. Order matters: the
    most disruptive condition wins."""
    wind = conditions.get("wind_mph")
    temp = conditions.get("temp_f")
    precip = conditions.get("precip_prob")  # 0..1

    if wind is not None and wind >= 20:
        return "wind"
    if temp is not None and temp <= 32:
        return "cold"
    if temp is not None and temp >= 90:
        return "heat"
    if precip is not None and precip >= 0.6:
        return "rain"
    return "clear"


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def score_weather(conditions: dict) -> WeatherScore:
    """Severity -> calibrated magnitude. Adverse weather is a headwind on the
    offense; clear weather is neutral and low-magnitude."""
    bucket = classify_bucket(conditions)
    wind = conditions.get("wind_mph") or 0
    temp = conditions.get("temp_f")
    precip = conditions.get("precip_prob") or 0

    if bucket == "wind":
        # 20 mph -> ~0.4, 40+ mph -> ~0.8. Wind most disrupts passing/kicking.
        mag = _clamp(0.4 + (wind - 20) * 0.02)
        why = (f"Sustained winds around {wind:.0f} mph hamper the passing and "
               f"kicking game, a headwind for offensive efficiency.")
        return WeatherScore(bucket, "headwind", mag, 0.7, why)
    if bucket == "cold":
        # colder -> larger. 32F -> ~0.3, 0F -> ~0.6.
        mag = _clamp(0.3 + (32 - (temp if temp is not None else 32)) * 0.01)
        why = (f"Freezing conditions (~{temp:.0f}°F) tend to depress scoring "
               f"and ball security, a modest headwind.")
        return WeatherScore(bucket, "headwind", mag, 0.65, why)
    if bucket == "heat":
        mag = _clamp(0.25 + ((temp if temp is not None else 90) - 90) * 0.01)
        why = "Extreme heat raises fatigue/cramping risk late — a mild headwind."
        return WeatherScore(bucket, "headwind", mag, 0.55, why)
    if bucket == "rain":
        mag = _clamp(0.3 + (precip - 0.6) * 0.5)
        why = "Likely rain threatens ball security and the passing game — a headwind."
        return WeatherScore(bucket, "headwind", mag, 0.6, why)
    return WeatherScore(
        "clear", "neutral", 0.1, 0.7,
        "Clear, mild conditions — no meaningful weather effect.",
    )
