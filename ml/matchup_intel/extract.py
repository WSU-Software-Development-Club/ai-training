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
from dataclasses import dataclass
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
    "- confidence: 0..1, how sure you are given the evidence.\n"
    "- explanation: one or two plain-language sentences a fan can read, carrying "
    "the nuance. No hedging boilerplate.\n"
    "- Output ONLY the JSON object, nothing else.\n\n"
    "MAGNITUDE is 0..1 and must reflect NET impact after mitigating context. Use "
    "this rubric and let the supporting data move you WITHIN a band:\n"
    "  0.00-0.20  negligible / routine\n"
    "  0.20-0.40  modest — real but well-mitigated (e.g. starter hurt but an "
    "elite, proven backup)\n"
    "  0.40-0.60  notable — clear edge/hit with partial mitigation\n"
    "  0.60-0.80  major — significant, little mitigation (e.g. starter OUT, "
    "untested/walk-on backup)\n"
    "  0.80-1.00  decisive — game-defining\n"
    "The QUALITY of a replacement is the key dial: a highly-touted, sharp backup "
    "pulls magnitude DOWN; an untested/walk-on backup pushes it UP."
)

# Few-shot calibration so backup quality actually separates the magnitude, not
# just the prose. Kept deliberately generic (no real teams) to avoid biasing.
_FEWSHOT = """CALIBRATION EXAMPLES (study how magnitude moves with mitigation):

Example A — RAW: "Starting QB questionable with a shoulder issue."
SUPPORTING: {"backup_qb": {"recruit_stars": 4, "recent_snaps": "210 yds, 2 TD in relief", "notes": "former blue-chip, looked sharp"}}
OUTPUT: {"category": "QB", "direction": "headwind", "magnitude": 0.35, "confidence": 0.6, "explanation": "Losing the starter hurts, but a blue-chip backup who has already played well limits the drop-off, so the net impact is modest."}

Example B — RAW: "Starting QB ruled OUT; backup is a converted walk-on making his first career start."
SUPPORTING: {"backup_qb": {"recruit_stars": 0, "recent_snaps": "none", "notes": "untested"}}
OUTPUT: {"category": "QB", "direction": "headwind", "magnitude": 0.72, "confidence": 0.75, "explanation": "The starter is out and the replacement is an untested walk-on making his first start, so the offense takes a major hit with little to cushion it."}

Example C — RAW: "Starter fully healthy; no changes at QB."
SUPPORTING: {}
OUTPUT: {"category": "QB", "direction": "neutral", "magnitude": 0.10, "confidence": 0.7, "explanation": "No meaningful change at quarterback this week."}
"""


def build_prompt(category: str, raw_text: str, supporting: dict | None) -> str:
    """Pure: assemble the single-factor prompt (no I/O)."""
    supporting_json = json.dumps(supporting or {}, indent=2, default=str)
    return (
        f"{_SYSTEM}\n\n"
        f"{_FEWSHOT}\n"
        f"NOW DO THE SAME FOR THIS ONE.\n"
        f"FACTOR CATEGORY: {category}\n\n"
        f"RAW SIGNAL:\n{raw_text}\n\n"
        f"SUPPORTING DATA (use this to judge NET impact and pick the magnitude band):\n"
        f"{supporting_json}\n\n"
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


@dataclass
class ExtractResult:
    """The Factor plus the full LLM trace, so every call is auditable — including
    ones that were DROPPED (factor is None) for producing invalid output."""

    factor: Optional[Factor]
    prompt: str
    response: Optional[str]     # raw model text (None on transport failure)
    valid: bool                # did the output validate into a factor?


def extract_factor_traced(
    config: Config,
    *,
    raw_id: str,
    ncaa_game_id: int,
    team_id: str,
    category: str,
    payload: dict,
    as_of_timestamp,
    season: int | None = None,
    week: int | None = None,
    game_id: int | None = None,
) -> ExtractResult:
    """Full Layer-1 step for one raw signal: prompt -> Ollama -> validate ->
    assemble a Factor (scoring_method='llm'). Returns the Factor (or None if
    dropped) together with the exact prompt + raw response for the audit trail."""
    raw_text = payload.get("text") or payload.get("body") or ""
    supporting = payload.get("supporting")
    prompt = build_prompt(category, raw_text, supporting)

    response = call_ollama(config, prompt)
    llm = parse_response(response) if response is not None else None
    if llm is None:
        return ExtractResult(factor=None, prompt=prompt, response=response, valid=False)

    factor = Factor(
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
    return ExtractResult(factor=factor, prompt=prompt, response=response, valid=True)


def extract_factor(config: Config, **kwargs) -> Optional[Factor]:
    """Back-compat wrapper: just the Factor (or None). Used where the LLM trace
    isn't needed (and by the unit tests)."""
    return extract_factor_traced(config, **kwargs).factor
