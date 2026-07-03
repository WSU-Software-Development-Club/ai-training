"""Pydantic models for the ensemble's LLM feature-extraction branch.

This is the validation boundary for ``llm_features.py``: every Ollama/gemma3
response is parsed through ``LLMFeatureOutput`` with ``extra="forbid"`` and
strict bounds. Anything that doesn't conform is dropped (``parse_llm_feature``
returns ``None``) rather than passed downstream — mirrors
``ml/matchup_intel/schemas.py``'s ``LLMFactorOutput``/``parse_llm_factor``,
reimplemented here (not imported) to keep this package decoupled.

CRITICAL: the LLM emits a FEATURE (a number the ensemble later reads from the
feature store), never a game outcome. ``extra="forbid"`` means a hallucinated
``predicted_winner``/``predicted_score`` field rejects the whole output.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

# Open set intentionally (kept as a tuple, not an enum) so new LLM-derived
# features can be added without a code change — same pattern as
# matchup_intel.schemas.KNOWN_CATEGORIES. Both are bounded [-1, 1]: negative
# favors the away team, positive favors the home team, 0 = no edge.
KNOWN_LLM_FEATURES = (
    "coaching_edge_score",   # net coaching-matchup edge (game-planning, situational, in-game adjustments)
    "momentum_score",        # net qualitative momentum edge from recent form/narrative context
)


class LLMFeatureOutput(BaseModel):
    """STRICT schema the LLM must return for ONE feature extraction call.

    The LLM is a feature extractor only — it never sees or emits anything
    about the game outcome (score, winner, margin). ``extra="forbid"`` means a
    hallucinated extra field rejects the whole output.
    """

    model_config = ConfigDict(extra="forbid")

    feature_name: str = Field(min_length=1)
    # Bounded [-1, 1]: negative = favors away team, positive = favors home
    # team, magnitude = size of the edge. Bounds are enforced here so a
    # malformed/extreme LLM output can never reach feature_values.
    value: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)


class FeatureValueDraft(BaseModel):
    """A validated LLM output, addressed to a specific game/team pair and
    timestamped — ready for ``feature_store.write_feature_value``. Separate
    from ``LLMFeatureOutput`` because the LLM itself never sees or sets
    ``ncaa_game_id``/``as_of_timestamp``; those are supplied by the caller
    (the pipeline knows which game/kickoff it's extracting for)."""

    model_config = ConfigDict(extra="forbid")

    feature_name: str = Field(min_length=1)
    value: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=1)
    ncaa_game_id: int
    as_of_timestamp: object  # datetime; kept loose here, validated at the DB write boundary


def parse_llm_feature(data: object) -> Optional[LLMFeatureOutput]:
    """Validate a raw LLM output. Returns the model, or ``None`` if invalid.

    Never raises — invalid model output is *expected* (the model can
    hallucinate a field, emit an out-of-range value, or return malformed
    JSON) and must be dropped silently rather than crash the pipeline or leak
    garbage into the feature store.
    """
    try:
        return LLMFeatureOutput.model_validate(data)
    except (ValidationError, TypeError):
        return None
