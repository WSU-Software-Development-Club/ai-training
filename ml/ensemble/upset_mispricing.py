"""Two-stage upset + market-mispricing detection.

STAGE 1 (input to this module, produced elsewhere): the stacked ensemble's
game prediction — predicted margin and/or home win probability. See
``stack.StackingEnsemble`` for how that's produced; this module is deliberately
decoupled from it (takes a plain ``GamePrediction``) so stage 2 is unit
testable without ever fitting a model.

STAGE 2 (this module): given the stage-1 prediction plus context (AP/Coaches
rank, and a reference panel of market odds), flag two independent things:
  (a) UPSET — the model's predicted winner is the underdog by rank.
  (b) MISPRICING — |model win prob - market implied win prob| exceeds a
      configurable threshold. The market side comes from the reference panel
      (Vegas moneyline/spread, or Polymarket, whichever is present) built the
      same way ``ml/matchup_intel/db.get_model_reference_panel`` builds it
      (predictions + latest polymarket raw_signals row) — reimplemented here,
      not imported, to keep this package decoupled from ml/matchup_intel.

Both flags degrade gracefully to "no signal" (never an exception) when their
inputs are missing: no rank -> no upset signal; no market -> no mispricing
signal. A null market is NOT an error — most CFB games have no tracked market.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


# --- stage 1 input (produced by stack.StackingEnsemble at inference time) --


@dataclass
class GamePrediction:
    """The ensemble's stage-1 output for one game — the only interface stage 2
    needs, so stage 2 can be tested without ever fitting a real model."""

    ncaa_game_id: int
    home_team: str
    away_team: str
    predicted_margin: float          # home_score - away_score, model's estimate
    home_win_prob: float             # model's probability the home team wins, 0..1
    home_rank: Optional[int] = None  # AP/Coaches poll rank, 1 = best, None = unranked
    away_rank: Optional[int] = None


def predicted_winner(game: GamePrediction) -> str:
    """Margin is the primary signal (matches ml/m1's convention); win_prob is
    the tiebreaker if margin is exactly 0."""
    if game.predicted_margin > 0:
        return game.home_team
    if game.predicted_margin < 0:
        return game.away_team
    return game.home_team if game.home_win_prob >= 0.5 else game.away_team


# --- stage 2a: upset detection ----------------------------------------------


def detect_upset(
    *,
    home_team: str,
    away_team: str,
    predicted_winner_team: str,
    home_rank: Optional[int],
    away_rank: Optional[int],
    min_rank_gap: int,
) -> dict:
    """Flag when the model's predicted winner is the ranked-worse (or
    unranked) side beating a ranked favorite. Rank convention: 1 = best
    (AP/Coaches Poll style); None = unranked. Never raises — missing ranks
    just mean no signal, not an error.
    """
    if home_rank is None and away_rank is None:
        return {"flagged": False, "reason": "both_unranked", "rank_gap": None}

    predicted_home_wins = predicted_winner_team == home_team
    winner_rank = home_rank if predicted_home_wins else away_rank
    loser_rank = away_rank if predicted_home_wins else home_rank

    if loser_rank is None:
        # The predicted LOSER isn't ranked at all, so there's no "favorite"
        # being upset — a ranked team beating an unranked team is expected.
        return {"flagged": False, "reason": "no_ranked_favorite", "rank_gap": None}

    if winner_rank is None:
        # Unranked side predicted to beat a ranked side — always an upset,
        # magnitude not quantifiable as a numeric gap.
        return {
            "flagged": True, "reason": "unranked_predicted_to_beat_ranked",
            "rank_gap": None, "predicted_winner": predicted_winner_team,
        }

    rank_gap = winner_rank - loser_rank  # positive => winner ranked worse than loser
    flagged = rank_gap >= min_rank_gap
    return {
        "flagged": flagged,
        "reason": "rank_gap_exceeds_threshold" if flagged else "insufficient_rank_gap",
        "rank_gap": rank_gap,
        "predicted_winner": predicted_winner_team,
    }


# --- stage 2b: market mispricing --------------------------------------------


def moneyline_to_implied_prob(moneyline: Optional[float]) -> Optional[float]:
    """American moneyline -> implied win probability (vig NOT removed)."""
    if moneyline is None:
        return None
    if moneyline > 0:
        return 100.0 / (moneyline + 100.0)
    return -moneyline / (-moneyline + 100.0)


def spread_to_implied_prob(spread: Optional[float], scale: float = 0.15) -> Optional[float]:
    """Rough point-spread -> home win probability via a logistic curve.

    ``spread`` uses the usual home-team sign convention (negative = home
    favored). This is a coarse, UNCALIBRATED approximation (no historical
    spread/outcome fit exists yet — that data isn't wired). Only used as a
    last-resort fallback when neither Polymarket nor a moneyline is present.
    """
    if spread is None:
        return None
    return float(1.0 / (1.0 + np.exp(scale * spread)))


def market_implied_home_win_prob(
    reference_panel: Optional[dict],
) -> tuple[Optional[float], Optional[str]]:
    """Pick the best available market signal from a reference panel shaped like
    ``{"vegas": {"spread": ..., "home_moneyline": ...}, "polymarket": {"home_win_prob": ...}}``.
    Preference order: Polymarket (best-effort probability market) > Vegas
    moneyline > Vegas spread (coarsest). Returns (prob, source) or
    (None, None) if the panel has no usable market signal at all — the
    expected case for most CFB games.
    """
    if not reference_panel:
        return None, None

    polymarket = reference_panel.get("polymarket") or {}
    if polymarket.get("home_win_prob") is not None:
        return float(polymarket["home_win_prob"]), "polymarket"

    vegas = reference_panel.get("vegas") or {}
    ml_prob = moneyline_to_implied_prob(vegas.get("home_moneyline"))
    if ml_prob is not None:
        return ml_prob, "vegas_moneyline"

    spread_prob = spread_to_implied_prob(vegas.get("spread"))
    if spread_prob is not None:
        return spread_prob, "vegas_spread"

    return None, None


def detect_mispricing(
    *,
    model_home_win_prob: float,
    reference_panel: Optional[dict],
    threshold: float,
) -> dict:
    """Flag |model - market| >= threshold. A null/missing market (no
    Polymarket row, no Vegas line) returns a clean "no signal" dict — never
    raises, and is indistinguishable in shape from a below-threshold result
    except for ``reason``/``market_prob`` being None.
    """
    market_prob, market_source = market_implied_home_win_prob(reference_panel)
    if market_prob is None:
        return {
            "flagged": False, "reason": "no_market", "edge": None,
            "market_prob": None, "market_source": None,
            "model_prob": model_home_win_prob,
        }

    edge = model_home_win_prob - market_prob
    flagged = bool(abs(edge) >= threshold)
    direction = "model_favors_home" if edge > 0 else ("model_favors_away" if edge < 0 else "aligned")
    return {
        "flagged": flagged,
        "reason": "edge_exceeds_threshold" if flagged else "within_threshold",
        "edge": edge,
        "market_prob": market_prob,
        "market_source": market_source,
        "model_prob": model_home_win_prob,
        "direction": direction,
    }


# --- orchestration: stage 1 -> stage 2 --------------------------------------


def score_game(
    game: GamePrediction,
    *,
    reference_panel: Optional[dict],
    upset_rank_gap: int,
    mispricing_threshold: float,
) -> dict:
    """Full two-stage evaluation for one game: stage-1 prediction (already
    computed, passed in as ``game``) -> stage-2 upset + mispricing flags."""
    winner = predicted_winner(game)
    upset = detect_upset(
        home_team=game.home_team, away_team=game.away_team,
        predicted_winner_team=winner,
        home_rank=game.home_rank, away_rank=game.away_rank,
        min_rank_gap=upset_rank_gap,
    )
    mispricing = detect_mispricing(
        model_home_win_prob=game.home_win_prob,
        reference_panel=reference_panel,
        threshold=mispricing_threshold,
    )
    return {
        "ncaa_game_id": game.ncaa_game_id,
        "home_team": game.home_team,
        "away_team": game.away_team,
        "predicted_winner": winner,
        "predicted_margin": game.predicted_margin,
        "home_win_prob": game.home_win_prob,
        "upset": upset,
        "mispricing": mispricing,
    }


# --- reference-panel read (DB-backed; mirrors, does not import, matchup_intel) --


def fetch_reference_panel(conn, ncaa_game_id: int) -> Optional[dict]:
    """Best-effort market reference panel for one game: the current Vegas
    line off ``predictions`` (moneylines aren't stored there today, only
    ``betting_over_under`` / implicit spread via ml/m1 features — so
    ``vegas.spread``/``vegas.home_moneyline`` are typically absent until that's
    wired) plus the latest Polymarket snapshot from ``raw_signals``
    (``source_type = 'polymarket'``), if the matchup_intel ingest has run for
    this game. Returns None only if the game itself isn't found; a game with
    no market data still returns a panel with null market fields (handled by
    ``detect_mispricing``, not an error).
    """
    row = conn.execute(
        "SELECT betting_over_under FROM predictions WHERE ncaa_game_id = %s",
        (ncaa_game_id,),
    ).fetchone()
    if row is None:
        return None
    betting_over_under = row[0]

    poly_row = conn.execute(
        """
        SELECT payload FROM raw_signals
        WHERE source_type = 'polymarket' AND ncaa_game_id = %s
        ORDER BY as_of_timestamp DESC LIMIT 1
        """,
        (ncaa_game_id,),
    ).fetchone()
    polymarket = None
    if poly_row is not None:
        payload = poly_row[0] or {}
        polymarket = {
            "home_win_prob": payload.get("home_win_prob"),
            "away_win_prob": payload.get("away_win_prob"),
        }

    return {
        "vegas": {"over_under": betting_over_under, "spread": None, "home_moneyline": None},
        "polymarket": polymarket,
    }


def main() -> None:
    """CLI skeleton: score one game end-to-end, given a manually-supplied
    stage-1 prediction (there is no trained ensemble artifact yet — see
    ml/ensemble/stack.py / base_learners.py — so this does NOT run inference;
    it demonstrates stage 2 wiring against a live reference panel).

    Usage: python -m ml.ensemble.upset_mispricing <ncaa_game_id> \
        <home_team> <away_team> <predicted_margin> <home_win_prob> \
        [home_rank] [away_rank]
    """
    import sys

    from .config import load_config

    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)

    ncaa_game_id = int(sys.argv[1])
    home_team, away_team = sys.argv[2], sys.argv[3]
    margin, win_prob = float(sys.argv[4]), float(sys.argv[5])
    home_rank = int(sys.argv[6]) if len(sys.argv) > 6 and sys.argv[6] != "-" else None
    away_rank = int(sys.argv[7]) if len(sys.argv) > 7 and sys.argv[7] != "-" else None

    game = GamePrediction(
        ncaa_game_id=ncaa_game_id, home_team=home_team, away_team=away_team,
        predicted_margin=margin, home_win_prob=win_prob,
        home_rank=home_rank, away_rank=away_rank,
    )

    cfg = load_config()
    reference_panel = None
    if cfg.database_url:
        from .feature_store import connect

        with connect(cfg.database_url) as conn:
            reference_panel = fetch_reference_panel(conn, ncaa_game_id)
    else:
        print("[INFO] DATABASE_URL not set — scoring with no reference panel (no market signal).")

    result = score_game(
        game, reference_panel=reference_panel,
        upset_rank_gap=cfg.upset_rank_gap,
        mispricing_threshold=cfg.mispricing_threshold,
    )
    print(result)


if __name__ == "__main__":
    main()
