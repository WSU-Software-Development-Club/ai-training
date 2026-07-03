"""Pydantic models for the Matchup Intelligence Engine.

This module is the *validation boundary*. Every LLM output is parsed through
``LLMFactorOutput`` with ``extra="forbid"`` and strict bounds; anything that
doesn't conform is dropped (``parse_llm_factor`` returns ``None``) rather than
passed downstream. Downstream code only ever sees validated ``Factor`` objects.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

Direction = Literal["tailwind", "headwind", "neutral"]
ScoringMethod = Literal["historical", "model", "llm", "hybrid"]

# Open set intentionally: new categories are added as templates grow. Kept as a
# tuple (not an enum) so config/data can extend it without a code change.
KNOWN_CATEGORIES = (
    "QB", "OL", "DL", "rest", "travel", "coaching",
    "momentum", "weather", "special_teams",
)


class Source(BaseModel):
    """Provenance for a factor — so a fan can verify every claim."""

    model_config = ConfigDict(extra="forbid")

    url: Optional[str] = None
    source_type: str
    snippet: Optional[str] = None
    published_at: Optional[datetime] = None


class LLMFactorOutput(BaseModel):
    """STRICT schema the LLM must return for ONE factor.

    The LLM is a feature extractor/contextualizer only — it never sees or emits
    anything about the game outcome. ``extra="forbid"`` means a hallucinated
    extra field (e.g. a "predicted_winner") rejects the whole output.
    """

    model_config = ConfigDict(extra="forbid")

    category: str = Field(min_length=1)
    direction: Direction
    # Magnitude/confidence are hard-bounded [0, 1]; anything outside is invalid.
    magnitude: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    # The explanation carries the nuance ("starter out, but blue-chip backup has
    # looked sharp — net headwind reduced"). Must be non-trivial.
    explanation: str = Field(min_length=1)


class Factor(BaseModel):
    """A fully-assembled factor, ready to persist to the ``factors`` table."""

    model_config = ConfigDict(extra="forbid")

    ncaa_game_id: int
    game_id: Optional[int] = None
    season: Optional[int] = None
    week: Optional[int] = None
    team_id: UUID
    category: str
    raw_signal: Optional[str] = None
    direction: Direction
    magnitude: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(min_length=1)
    scoring_method: ScoringMethod
    historical_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    sample_size: int = Field(default=0, ge=0)
    sources: list[Source] = Field(default_factory=list)
    derived_from_raw_ids: list[UUID] = Field(default_factory=list)
    grounding: Optional[dict] = None
    as_of_timestamp: datetime

    @property
    def score(self) -> float:
        """Ranking key: magnitude x confidence."""
        return self.magnitude * self.confidence


class RawSignalRef(BaseModel):
    """Minimal view of a ``raw_signals`` row used by the point-in-time filter."""

    model_config = ConfigDict(extra="forbid")

    raw_id: UUID
    source_type: str
    ncaa_game_id: Optional[int] = None
    team_id: Optional[UUID] = None
    published_at: Optional[datetime] = None
    as_of_timestamp: datetime


def parse_llm_factor(data: object) -> Optional[LLMFactorOutput]:
    """Validate a raw LLM output. Returns the model, or ``None`` if invalid.

    Never raises — invalid model output is *expected* and must be dropped
    silently rather than crash the pipeline or leak garbage downstream.
    """
    try:
        return LLMFactorOutput.model_validate(data)
    except (ValidationError, TypeError):
        return None
