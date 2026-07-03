"""The sample-size guard withholds historical rates below threshold."""

from __future__ import annotations

from ml.matchup_intel.logic import apply_sample_size_guard, assemble_deck

from .conftest import make_factor

THRESHOLD = 30


def test_below_threshold_withholds_rate():
    f = make_factor(historical_rate=0.71, sample_size=5, scoring_method="historical")
    view = apply_sample_size_guard(f, THRESHOLD)
    assert view["historical_rate"] is None
    assert view["historical_rate_withheld"] is True
    # Direction + explanation are still shown — the fan gets the nuance, not a number.
    assert view["direction"] == f.direction
    assert view["explanation"] == f.explanation


def test_at_threshold_exposes_rate():
    f = make_factor(historical_rate=0.64, sample_size=THRESHOLD, scoring_method="historical")
    view = apply_sample_size_guard(f, THRESHOLD)
    assert view["historical_rate"] == 0.64
    assert view["historical_rate_withheld"] is False


def test_above_threshold_exposes_rate():
    f = make_factor(historical_rate=0.58, sample_size=120, scoring_method="historical")
    view = apply_sample_size_guard(f, THRESHOLD)
    assert view["historical_rate"] == 0.58
    assert view["historical_rate_withheld"] is False


def test_null_rate_with_large_sample_is_still_withheld():
    # No rate computed at all -> nothing to expose, regardless of sample_size.
    f = make_factor(historical_rate=None, sample_size=500)
    view = apply_sample_size_guard(f, THRESHOLD)
    assert view["historical_rate"] is None
    assert view["historical_rate_withheld"] is True


def test_qb_v1_case_shows_direction_no_percentage():
    # The approved QB v1 behaviour: no injury history -> sample_size 0 -> the
    # guard engages and the factor shows a direction + why but no rate.
    qb = make_factor(scoring_method="llm", historical_rate=None, sample_size=0)
    view = apply_sample_size_guard(qb, THRESHOLD)
    assert view["historical_rate"] is None
    assert view["historical_rate_withheld"] is True
    assert view["explanation"]


def test_assemble_deck_applies_guard_to_every_factor():
    factors = [
        make_factor(category="QB", historical_rate=None, sample_size=0),
        make_factor(category="weather", historical_rate=0.9, sample_size=3,
                    scoring_method="historical"),
    ]
    deck = assemble_deck(factors, THRESHOLD)
    assert all(v["historical_rate"] is None for v in deck)  # both sub-threshold
