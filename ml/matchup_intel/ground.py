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

from typing import Callable, Optional

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


# Registry: category -> grounding function. Weather (slice #2) will register a
# real Open-Meteo-archive-backed query here; every other category is a variation.
_GROUNDERS: dict[str, Callable[..., Factor]] = {
    "QB": ground_qb_factor,
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
