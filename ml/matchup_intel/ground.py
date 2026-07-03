"""Layer 4 — historical grounding.

For each factor, ask the historical database "how has this factor type performed
historically?" and populate ``historical_rate`` + ``sample_size``. The sample-size
GUARD itself lives in serve.py (the serving boundary); this stage only produces
the honest counts. Grounding is dispatched per category so new factor types plug
in without touching the others.

QB v1 (approved): we have no historical injury-outcome dataset, so QB grounding
returns sample_size=0 — which makes the guard withhold any rate. That's the
reference demonstration of intellectual honesty, not a shortcut.
"""

from __future__ import annotations

from typing import Callable

from . import db
from .schemas import Factor


def ground_qb_factor(factor: Factor, conn=None) -> Factor:
    """No injury-outcome history exists yet -> no rate, sample_size 0."""
    return factor.model_copy(update={
        "historical_rate": None,
        "sample_size": 0,
        "grounding": {
            "method": "none",
            "reason": "no historical injury-outcome dataset available in v1; "
                      "sample-size guard withholds any rate",
        },
    })


def ground_weather_factor(factor: Factor, conn=None) -> Factor:
    """Real historical grounding: the team's win-rate in this weather bucket.
    Produces the honest counts; the sample-size guard (at serving) decides
    whether the rate is actually shown. The bucket is carried on the factor's
    grounding dict by the weather scorer step."""
    bucket = (factor.grounding or {}).get("condition_bucket")
    if conn is None or bucket is None:
        return factor.model_copy(update={
            "historical_rate": None, "sample_size": 0,
            "grounding": {"method": "weather_history", "reason": "no bucket/conn"},
        })
    wins, total = db.get_weather_history_rate(conn, factor.team_id, bucket)
    rate = (wins / total) if total > 0 else None
    return factor.model_copy(update={
        "historical_rate": rate,
        "sample_size": total,
        "scoring_method": "hybrid",   # model magnitude + historical rate
        "grounding": {
            "method": "weather_history",
            "condition_bucket": bucket,
            "wins": wins,
            "total": total,
        },
    })


# Registry: category -> grounding function. Every new factor type is a variation
# of one of these two templates (guard-null vs real historical query).
_GROUNDERS: dict[str, Callable[..., Factor]] = {
    "QB": ground_qb_factor,
    "weather": ground_weather_factor,
}


def ground_factor(factor: Factor, conn=None) -> Factor:
    grounder = _GROUNDERS.get(factor.category)
    if grounder is None:
        # Unknown category: stay honest — no rate, record that it wasn't grounded.
        return factor.model_copy(update={
            "historical_rate": None,
            "sample_size": 0,
            "grounding": {"method": "none", "reason": "no grounder for category"},
        })
    return grounder(factor, conn)
