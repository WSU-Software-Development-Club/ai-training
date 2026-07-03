"""Point-in-time correctness: a game's deck never sees post-kickoff signals."""

from __future__ import annotations

from datetime import timedelta

from ml.matchup_intel.logic import filter_point_in_time

from .conftest import KICKOFF, make_signal


def test_signal_before_kickoff_is_visible():
    s = make_signal(
        published_at=KICKOFF - timedelta(days=2),
        as_of_timestamp=KICKOFF - timedelta(days=2),
    )
    assert filter_point_in_time([s], KICKOFF) == [s]


def test_signal_published_after_kickoff_is_invisible():
    # Injury news that broke after the game must not be usable at eval time.
    s = make_signal(
        published_at=KICKOFF + timedelta(hours=1),
        as_of_timestamp=KICKOFF + timedelta(hours=1),
    )
    assert filter_point_in_time([s], KICKOFF) == []


def test_observed_after_kickoff_is_invisible_even_if_published_before():
    # We only learned of it after kickoff — it can't inform the pre-game deck.
    s = make_signal(
        published_at=KICKOFF - timedelta(days=1),
        as_of_timestamp=KICKOFF + timedelta(hours=3),
    )
    assert filter_point_in_time([s], KICKOFF) == []


def test_missing_published_at_falls_back_to_as_of():
    before = make_signal(published_at=None, as_of_timestamp=KICKOFF - timedelta(hours=2))
    after = make_signal(published_at=None, as_of_timestamp=KICKOFF + timedelta(hours=2))
    assert filter_point_in_time([before, after], KICKOFF) == [before]


def test_signal_exactly_at_kickoff_is_visible():
    s = make_signal(published_at=KICKOFF, as_of_timestamp=KICKOFF)
    assert filter_point_in_time([s], KICKOFF) == [s]


def test_mixed_batch_filters_only_future_signals():
    keep = make_signal(as_of_timestamp=KICKOFF - timedelta(days=1),
                       published_at=KICKOFF - timedelta(days=1))
    drop = make_signal(as_of_timestamp=KICKOFF + timedelta(days=1),
                       published_at=KICKOFF + timedelta(days=1))
    result = filter_point_in_time([keep, drop, keep], KICKOFF)
    assert drop not in result
    assert result.count(keep) == 2
