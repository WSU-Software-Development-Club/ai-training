"""Stage-2 flag math: upset detection, mispricing edge math, and graceful
null-market handling (no market must never crash or silently look "aligned").
"""

from __future__ import annotations

import pytest

from ml.ensemble.upset_mispricing import (
    GamePrediction,
    detect_mispricing,
    detect_upset,
    market_implied_home_win_prob,
    moneyline_to_implied_prob,
    predicted_winner,
    score_game,
    spread_to_implied_prob,
)

# --- predicted_winner --------------------------------------------------------


def test_predicted_winner_home_favored():
    g = GamePrediction(1, "Home", "Away", predicted_margin=7.0, home_win_prob=0.7)
    assert predicted_winner(g) == "Home"


def test_predicted_winner_away_favored():
    g = GamePrediction(1, "Home", "Away", predicted_margin=-3.0, home_win_prob=0.3)
    assert predicted_winner(g) == "Away"


def test_predicted_winner_tiebreak_uses_win_prob():
    g = GamePrediction(1, "Home", "Away", predicted_margin=0.0, home_win_prob=0.51)
    assert predicted_winner(g) == "Home"
    g2 = GamePrediction(1, "Home", "Away", predicted_margin=0.0, home_win_prob=0.49)
    assert predicted_winner(g2) == "Away"


# --- detect_upset -------------------------------------------------------------


def test_no_signal_when_both_teams_unranked():
    result = detect_upset(
        home_team="Home", away_team="Away", predicted_winner_team="Home",
        home_rank=None, away_rank=None, min_rank_gap=10,
    )
    assert result["flagged"] is False
    assert result["reason"] == "both_unranked"


def test_no_upset_when_favorite_is_unranked():
    # Ranked home team predicted to win over an unranked away team is not an
    # upset — there's no ranked favorite being upset.
    result = detect_upset(
        home_team="Home", away_team="Away", predicted_winner_team="Home",
        home_rank=5, away_rank=None, min_rank_gap=10,
    )
    assert result["flagged"] is False
    assert result["reason"] == "no_ranked_favorite"


def test_unranked_predicted_to_beat_ranked_is_always_an_upset():
    result = detect_upset(
        home_team="Home", away_team="Away", predicted_winner_team="Away",
        home_rank=3, away_rank=None, min_rank_gap=10,
    )
    assert result["flagged"] is True
    assert result["reason"] == "unranked_predicted_to_beat_ranked"


def test_upset_flagged_when_rank_gap_meets_threshold():
    # #25 predicted to beat #2 -> gap = 23, threshold 10 -> flagged.
    result = detect_upset(
        home_team="Home", away_team="Away", predicted_winner_team="Home",
        home_rank=25, away_rank=2, min_rank_gap=10,
    )
    assert result["flagged"] is True
    assert result["rank_gap"] == 23


def test_upset_not_flagged_when_rank_gap_below_threshold():
    # #4 predicted to beat #2 -> gap = 2, below threshold of 10.
    result = detect_upset(
        home_team="Home", away_team="Away", predicted_winner_team="Home",
        home_rank=4, away_rank=2, min_rank_gap=10,
    )
    assert result["flagged"] is False
    assert result["rank_gap"] == 2


def test_better_ranked_predicted_winner_is_never_an_upset():
    # #2 predicted to beat #25 -> negative gap, never flagged regardless of threshold.
    result = detect_upset(
        home_team="Home", away_team="Away", predicted_winner_team="Home",
        home_rank=2, away_rank=25, min_rank_gap=1,
    )
    assert result["flagged"] is False
    assert result["rank_gap"] == -23


# --- market conversions -------------------------------------------------------


def test_moneyline_to_implied_prob_favorite_and_underdog():
    # -200 favorite -> 200/300 = 0.667; +150 underdog -> 100/250 = 0.4
    assert moneyline_to_implied_prob(-200) == pytest.approx(0.6667, abs=1e-3)
    assert moneyline_to_implied_prob(150) == pytest.approx(0.4, abs=1e-3)


def test_moneyline_to_implied_prob_none_is_none():
    assert moneyline_to_implied_prob(None) is None


def test_spread_to_implied_prob_home_favored_is_above_half():
    # Home favored by 10 (spread = -10) should imply > 50% win prob.
    assert spread_to_implied_prob(-10) > 0.5
    assert spread_to_implied_prob(10) < 0.5
    assert spread_to_implied_prob(0) == pytest.approx(0.5, abs=1e-6)


def test_spread_to_implied_prob_none_is_none():
    assert spread_to_implied_prob(None) is None


def test_market_implied_prob_prefers_polymarket_over_vegas():
    panel = {
        "polymarket": {"home_win_prob": 0.62},
        "vegas": {"home_moneyline": -500},  # would imply ~0.83 if used
    }
    prob, source = market_implied_home_win_prob(panel)
    assert prob == 0.62
    assert source == "polymarket"


def test_market_implied_prob_falls_back_to_moneyline():
    panel = {"polymarket": None, "vegas": {"home_moneyline": -200}}
    prob, source = market_implied_home_win_prob(panel)
    assert prob == pytest.approx(0.6667, abs=1e-3)
    assert source == "vegas_moneyline"


def test_market_implied_prob_falls_back_to_spread():
    panel = {"polymarket": None, "vegas": {"home_moneyline": None, "spread": -7}}
    prob, source = market_implied_home_win_prob(panel)
    assert prob is not None
    assert source == "vegas_spread"


def test_market_implied_prob_none_when_panel_is_none():
    assert market_implied_home_win_prob(None) == (None, None)


def test_market_implied_prob_none_when_panel_has_no_usable_signal():
    panel = {"polymarket": None, "vegas": {"home_moneyline": None, "spread": None}}
    assert market_implied_home_win_prob(panel) == (None, None)


# --- detect_mispricing: the null-market case must never crash ---------------


def test_mispricing_no_market_is_not_a_crash():
    result = detect_mispricing(model_home_win_prob=0.7, reference_panel=None, threshold=0.15)
    assert result["flagged"] is False
    assert result["reason"] == "no_market"
    assert result["edge"] is None
    assert result["market_prob"] is None


def test_mispricing_panel_present_but_no_usable_market_signal():
    panel = {"polymarket": None, "vegas": {"home_moneyline": None, "spread": None}}
    result = detect_mispricing(model_home_win_prob=0.7, reference_panel=panel, threshold=0.15)
    assert result["flagged"] is False
    assert result["reason"] == "no_market"


def test_mispricing_flags_when_edge_exceeds_threshold():
    panel = {"polymarket": {"home_win_prob": 0.5}}
    result = detect_mispricing(model_home_win_prob=0.7, reference_panel=panel, threshold=0.15)
    assert result["flagged"] is True
    assert result["edge"] == pytest.approx(0.2)
    assert result["direction"] == "model_favors_home"


def test_mispricing_not_flagged_within_threshold():
    panel = {"polymarket": {"home_win_prob": 0.65}}
    result = detect_mispricing(model_home_win_prob=0.7, reference_panel=panel, threshold=0.15)
    assert result["flagged"] is False
    assert result["edge"] == pytest.approx(0.05)


def test_mispricing_negative_edge_direction():
    panel = {"polymarket": {"home_win_prob": 0.8}}
    result = detect_mispricing(model_home_win_prob=0.5, reference_panel=panel, threshold=0.15)
    assert result["flagged"] is True
    assert result["direction"] == "model_favors_away"


def test_mispricing_threshold_boundary_is_inclusive():
    panel = {"polymarket": {"home_win_prob": 0.5}}
    result = detect_mispricing(model_home_win_prob=0.65, reference_panel=panel, threshold=0.15)
    assert result["flagged"] is True  # exactly at threshold


# --- score_game: full stage-1 -> stage-2 orchestration -----------------------


def test_score_game_combines_upset_and_mispricing_with_null_market():
    game = GamePrediction(
        ncaa_game_id=42, home_team="Home", away_team="Away",
        predicted_margin=3.0, home_win_prob=0.6,
        home_rank=20, away_rank=3,
    )
    result = score_game(
        game, reference_panel=None, upset_rank_gap=10, mispricing_threshold=0.15,
    )
    assert result["predicted_winner"] == "Home"
    assert result["upset"]["flagged"] is True   # #20 beating #3, gap=17 >= 10
    assert result["mispricing"]["flagged"] is False
    assert result["mispricing"]["reason"] == "no_market"
