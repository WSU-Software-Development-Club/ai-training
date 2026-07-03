"""Shared fixtures/helpers for ml/ensemble tests.

These tests exercise the *pure* layers only — no live Postgres, no Ollama —
so they run anywhere the packages in requirements.txt are installed.
"""

from __future__ import annotations

from datetime import datetime, timezone

KICKOFF = datetime(2024, 10, 12, 19, 0, tzinfo=timezone.utc)


def make_feature_row(**overrides) -> dict:
    """A single feature_values-shaped row, defaults are point-in-time-safe
    and observed well before KICKOFF; override any field per test."""
    from datetime import timedelta

    data = dict(
        feature_name="home_sp_rating",
        value_num=12.5,
        value_text=None,
        as_of_timestamp=KICKOFF - timedelta(days=2),
        point_in_time_safe=True,
    )
    data.update(overrides)
    return data
