"""Point-in-time feature assembly: excludes post-kickoff and leaky rows.

Pure/in-memory — exercises ``feature_store._latest_asof_by_feature`` (the same
rule the live SQL enforces) without a database.
"""

from __future__ import annotations

from datetime import timedelta

from ml.ensemble.feature_store import _latest_asof_by_feature, normalize_team_name

from .conftest import KICKOFF, make_feature_row


def test_value_before_kickoff_is_visible():
    row = make_feature_row(as_of_timestamp=KICKOFF - timedelta(days=1))
    assert _latest_asof_by_feature([row], KICKOFF) == {"home_sp_rating": 12.5}


def test_value_after_kickoff_is_excluded():
    # A stat that only became known post-kickoff (e.g. a post-game aggregate)
    # must never leak into the pre-game feature vector.
    row = make_feature_row(as_of_timestamp=KICKOFF + timedelta(hours=1))
    assert _latest_asof_by_feature([row], KICKOFF) == {}


def test_value_exactly_at_kickoff_is_visible():
    row = make_feature_row(as_of_timestamp=KICKOFF)
    assert _latest_asof_by_feature([row], KICKOFF) == {"home_sp_rating": 12.5}


def test_point_in_time_unsafe_feature_is_excluded_even_if_before_kickoff():
    row = make_feature_row(
        feature_name="season_final_sp_rating",
        as_of_timestamp=KICKOFF - timedelta(days=1),
        point_in_time_safe=False,
    )
    assert _latest_asof_by_feature([row], KICKOFF) == {}


def test_newest_qualifying_value_wins():
    older = make_feature_row(value_num=10.0, as_of_timestamp=KICKOFF - timedelta(days=5))
    newer = make_feature_row(value_num=14.0, as_of_timestamp=KICKOFF - timedelta(days=1))
    assert _latest_asof_by_feature([older, newer], KICKOFF) == {"home_sp_rating": 14.0}
    # Order in the input list shouldn't matter.
    assert _latest_asof_by_feature([newer, older], KICKOFF) == {"home_sp_rating": 14.0}


def test_future_row_never_beats_a_valid_older_row():
    valid = make_feature_row(value_num=8.0, as_of_timestamp=KICKOFF - timedelta(days=1))
    future = make_feature_row(value_num=99.0, as_of_timestamp=KICKOFF + timedelta(days=1))
    assert _latest_asof_by_feature([valid, future], KICKOFF) == {"home_sp_rating": 8.0}


def test_value_text_used_when_value_num_is_none():
    row = make_feature_row(
        feature_name="injury_status", value_num=None, value_text="questionable",
    )
    assert _latest_asof_by_feature([row], KICKOFF) == {"injury_status": "questionable"}


def test_mixed_features_each_resolved_independently():
    rows = [
        make_feature_row(feature_name="home_sp_rating", value_num=12.5),
        make_feature_row(feature_name="away_sp_rating", value_num=9.0),
        make_feature_row(
            feature_name="future_only", value_num=1.0,
            as_of_timestamp=KICKOFF + timedelta(hours=1),
        ),
    ]
    result = _latest_asof_by_feature(rows, KICKOFF)
    assert result == {"home_sp_rating": 12.5, "away_sp_rating": 9.0}


def test_normalize_team_name_matches_teams_join_key():
    assert normalize_team_name("Washington State") == "washington state"
    assert normalize_team_name("  Ohio   State! ") == "ohio state"
    assert normalize_team_name("") == ""
    assert normalize_team_name(None) == ""
