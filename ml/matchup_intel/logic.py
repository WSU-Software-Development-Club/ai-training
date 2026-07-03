"""Pure assembly, point-in-time, and sample-size-guard logic.

Everything here is side-effect-free (no DB, no network) so the three hard
requirements — point-in-time correctness, the sample-size guard, and ranking —
are unit-testable in isolation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence, TypeVar

from .schemas import Factor, RawSignalRef

T = TypeVar("T", bound=RawSignalRef)


def filter_point_in_time(signals: Iterable[T], kickoff: datetime) -> list[T]:
    """Keep only signals knowable at ``kickoff``.

    This is the #1 way a matchup system silently cheats, so the rule is strict
    and applied structurally: a signal is visible for a game only if BOTH
      - it was observed (``as_of_timestamp``) at or before kickoff, AND
      - its source published (``published_at``) at or before kickoff.
    A missing ``published_at`` falls back to ``as_of_timestamp`` (we can't claim
    it predates kickoff without evidence, so we use our observation time).
    News published after kickoff is invisible at that game's evaluation time.
    """
    visible: list[T] = []
    for s in signals:
        if s.as_of_timestamp > kickoff:
            continue
        published = s.published_at if s.published_at is not None else s.as_of_timestamp
        if published > kickoff:
            continue
        visible.append(s)
    return visible


def dedupe_factors(factors: Sequence[Factor]) -> list[Factor]:
    """v1 dedupe rule: one factor per ``(team_id, category)``.

    The LLM is expected to merge related raw signals into a single factor before
    scoring; this is the defensive backstop — if two survive for the same team +
    category, keep the higher ``magnitude x confidence``.
    """
    best: dict[tuple, Factor] = {}
    for f in factors:
        key = (f.team_id, f.category)
        incumbent = best.get(key)
        if incumbent is None or f.score > incumbent.score:
            best[key] = f
    return list(best.values())


def rank_factors(factors: Sequence[Factor]) -> list[Factor]:
    """Rank by ``magnitude x confidence`` descending (stable)."""
    return sorted(factors, key=lambda f: f.score, reverse=True)


def apply_sample_size_guard(factor: Factor, threshold: int) -> dict:
    """Render a factor for serving with the sample-size guard enforced.

    Below ``threshold`` the historical rate is withheld (set to ``None``) and a
    flag records why — the fan sees direction + explanation but NEVER a
    small-sample percentage dressed up as meaningful. This is the structural
    choke point: serving is built only from the output of this function, so a
    sub-threshold rate physically cannot reach the frontend.
    """
    meets = factor.sample_size >= threshold and factor.historical_rate is not None
    return {
        "team_id": str(factor.team_id),
        "category": factor.category,
        "direction": factor.direction,
        "magnitude": factor.magnitude,
        "confidence": factor.confidence,
        "score": factor.score,
        "explanation": factor.explanation,
        "scoring_method": factor.scoring_method,
        # Guard: only expose the rate when the sample clears the threshold.
        "historical_rate": factor.historical_rate if meets else None,
        "sample_size": factor.sample_size,
        "historical_rate_withheld": not meets,
        "sources": [s.model_dump(mode="json") for s in factor.sources],
        "raw_signal": factor.raw_signal,
    }


def assemble_deck(
    factors: Sequence[Factor], threshold: int
) -> list[dict]:
    """Full Layer-3/4/5 assembly for one team: dedupe -> rank -> guard-render."""
    deduped = dedupe_factors(factors)
    ranked = rank_factors(deduped)
    return [apply_sample_size_guard(f, threshold) for f in ranked]
