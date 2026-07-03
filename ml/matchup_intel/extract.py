"""Layer 1 — LLM extraction & contextualization (self-hosted Ollama / gemma3).

The LLM is a FEATURE EXTRACTOR and CONTEXTUALIZER, never a predictor. Each call
is scoped to ONE factor with a strict JSON-schema output (Ollama structured
outputs), and every response is validated against ``LLMFactorOutput`` — invalid
output is dropped, never passed downstream.

The hard/valuable part is contextualization: given the raw signal PLUS supporting
data (e.g. the backup QB's recruiting profile and recent snaps), the model must
assign direction/magnitude/confidence/explanation reflecting NET impact — "starter
out" is a headwind, but a blue-chip backup who's looked sharp reduces the magnitude.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import requests

from .config import Config
from .schemas import Factor, LLMFactorOutput, Source, parse_llm_factor

_SYSTEM = (
    "You are a college-football matchup ANALYST that extracts a single structured "
    "factor from a raw signal. You do NOT predict the game outcome, score, or "
    "winner. You only characterize how this one factor tilts the matchup for the "
    "given team, and by how much.\n\n"
    "Rules:\n"
    "- direction: 'tailwind' (helps the team), 'headwind' (hurts), or 'neutral'.\n"
    "- magnitude: 0..1, how much this factor matters for THIS game.\n"
    "- confidence: 0..1, how sure you are given the evidence.\n"
    "- Weigh NET impact using the supporting data. A hurt starter is a headwind, "
    "but a highly-touted backup who has played well REDUCES the magnitude, and the "
    "explanation must say so.\n"
    "- explanation: one or two plain-language sentences a fan can read, carrying "
    "the nuance. No hedging boilerplate.\n"
    "- Output ONLY the JSON object, nothing else."
)


def build_prompt(category: str, raw_text: str, supporting: dict | None) -> str:
    """Pure: assemble the single-factor prompt (no I/O)."""
    supporting_json = json.dumps(supporting or {}, indent=2, default=str)
    return (
        f"{_SYSTEM}\n\n"
        f"FACTOR CATEGORY: {category}\n\n"
        f"RAW SIGNAL:\n{raw_text}\n\n"
        f"SUPPORTING DATA (use this to judge NET impact):\n{supporting_json}\n\n"
        f'Return JSON with keys: category, direction, magnitude, confidence, explanation.'
    )


def parse_response(text: str) -> Optional[LLMFactorOutput]:
    """Pure: parse+validate an Ollama response body. Returns None if unusable."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return parse_llm_factor(data)


def call_ollama(config: Config, prompt: str) -> Optional[str]:
    """Impure: call Ollama's /api/generate with a strict JSON schema. Returns the
    raw response text, or None on any transport error (handled gracefully)."""
    schema = LLMFactorOutput.model_json_schema()
    try:
        resp = requests.post(
            f"{config.ollama_url}/api/generate",
            json={
                "model": config.ollama_model,
                "prompt": prompt,
                "stream": False,
                "format": schema,   # Ollama structured outputs -> schema-constrained JSON
                "options": {"temperature": 0.2},
            },
            timeout=config.request_timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response")
    except (requests.RequestException, ValueError):
        return None


def _sources_from_payload(payload: dict) -> list[Source]:
    """Build provenance from a raw_signals payload. Never invents sources."""
    out: list[Source] = []
    for s in payload.get("sources", []) or []:
        parsed = _safe_source(s)
        if parsed is not None:
            out.append(parsed)
    return out


def _safe_source(s: dict) -> Optional[Source]:
    try:
        return Source.model_validate(s)
    except Exception:
        return None


def extract_factor(
    config: Config,
    *,
    raw_id: str,
    ncaa_game_id: int,
    team_id: str,
    category: str,
    payload: dict,
    as_of_timestamp: datetime,
    season: int | None = None,
    week: int | None = None,
    game_id: int | None = None,
) -> Optional[Factor]:
    """Full Layer-1 step for one raw signal: prompt -> Ollama -> validate ->
    assemble a Factor (scoring_method='llm'). Returns None if the LLM output is
    unusable (dropped)."""
    raw_text = payload.get("text") or payload.get("body") or ""
    supporting = payload.get("supporting")
    prompt = build_prompt(category, raw_text, supporting)

    response = call_ollama(config, prompt)
    if response is None:
        return None
    llm = parse_response(response)
    if llm is None:
        return None

    return Factor(
        ncaa_game_id=ncaa_game_id,
        game_id=game_id,
        season=season,
        week=week,
        team_id=UUID(team_id),
        category=llm.category,
        raw_signal=raw_text[:2000] or None,
        direction=llm.direction,
        magnitude=llm.magnitude,
        confidence=llm.confidence,
        explanation=llm.explanation,
        scoring_method="llm",
        historical_rate=None,     # grounding stage fills this (guard-gated)
        sample_size=0,
        sources=_sources_from_payload(payload),
        derived_from_raw_ids=[UUID(raw_id)],
        as_of_timestamp=as_of_timestamp,
    )
