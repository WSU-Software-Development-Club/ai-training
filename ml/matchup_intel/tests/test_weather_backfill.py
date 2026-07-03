"""_local_date(): UTC kickoff -> stadium-local calendar date (join key for the
live weather backfill). Regression test for the tz-wrong date join bug."""

from __future__ import annotations

from ml.matchup_intel.ingest.weather_backfill import _local_date


def test_evening_pacific_kickoff_rolls_back_a_utc_day():
    # 2003-11-09T00:00:00Z is 2003-11-08 16:00 PST at Martin Stadium (Pullman,
    # WA) — naive date_iso[:10] slicing would (wrongly) key this to 11-09.
    assert _local_date("2003-11-09T00:00:00.000Z", "America/Los_Angeles") == "2003-11-08"


def test_late_night_kickoff_rolls_back_a_utc_day():
    # 2005-09-02T02:00:00Z is 2005-09-01 19:00 PDT — another UTC-day rollover.
    assert _local_date("2005-09-02T02:00:00.000Z", "America/Los_Angeles") == "2005-09-01"


def test_daytime_kickoff_matches_the_utc_date():
    # An early-afternoon PT kickoff stays on the same calendar day both ways.
    assert _local_date("2003-09-20T21:00:00.000Z", "America/Los_Angeles") == "2003-09-20"
