"""Shared fixtures/helpers for the matchup_intel tests.

These tests exercise the *pure* layers (schemas + logic) only — no DB, no
Ollama — so they run anywhere `pydantic` is installed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from ml.matchup_intel.schemas import Factor, RawSignalRef

KICKOFF = datetime(2024, 10, 12, 19, 0, tzinfo=timezone.utc)


def make_factor(**overrides) -> Factor:
    """A valid Factor with sensible defaults; override any field per test."""
    data = dict(
        ncaa_game_id=1234,
        team_id=uuid4(),
        category="QB",
        raw_signal="Starter QB questionable; blue-chip backup has looked sharp.",
        direction="headwind",
        magnitude=0.4,
        confidence=0.6,
        explanation="Starter is banged up, but the backup is a former 5-star who "
        "played well last week — net headwind is reduced.",
        scoring_method="llm",
        historical_rate=None,
        sample_size=0,
        as_of_timestamp=KICKOFF - timedelta(days=1),
    )
    data.update(overrides)
    return Factor(**data)


def make_signal(**overrides) -> RawSignalRef:
    data = dict(
        raw_id=uuid4(),
        source_type="injury_report",
        ncaa_game_id=1234,
        published_at=KICKOFF - timedelta(days=1),
        as_of_timestamp=KICKOFF - timedelta(days=1),
    )
    data.update(overrides)
    return RawSignalRef(**data)
