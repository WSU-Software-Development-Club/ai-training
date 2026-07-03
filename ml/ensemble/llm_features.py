"""LLM feature-extraction branch (self-hosted Ollama/gemma3).

Reuses the client style from ``ml/matchup_intel/extract.py`` (strict prompt,
Ollama structured-output schema, Pydantic-validated response, drop invalid) —
reimplemented here rather than imported, to keep this package decoupled from
ml/matchup_intel (which is being edited concurrently).

HARD RULE: the LLM emits FEATURES (e.g. a coaching-edge or momentum score)
written to ``feature_values`` with an ``as_of_timestamp``. It NEVER predicts
the game outcome — ``LLMFeatureOutput`` (schemas.py) has no score/winner/margin
field, and ``extra="forbid"`` rejects any response that tries to add one.
These are inputs to the ensemble's base learners, not outputs of the pipeline.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import requests

from .config import Config
from .schemas import KNOWN_LLM_FEATURES, LLMFeatureOutput, parse_llm_feature

_SYSTEM = (
    "You are a college-football ANALYST that extracts ONE structured, "
    "numeric feature from context you're given. You do NOT predict the game "
    "outcome, score, margin, or winner — you are extracting a single input "
    "signal for a downstream model, not producing a prediction yourself.\n\n"
    "Rules:\n"
    "- value: a number from -1.0 to 1.0. Positive means the signal favors the "
    "HOME team; negative favors the AWAY team; magnitude is the size of the "
    "edge. 0.0 means no meaningful edge either way.\n"
    "- confidence: 0.0 to 1.0, how sure you are given the evidence provided.\n"
    "- rationale: one or two plain-language sentences explaining the value, "
    "grounded ONLY in the context given (never invent facts not present).\n"
    "- Output ONLY the JSON object, nothing else.\n"
)


def build_prompt(feature_name: str, context: dict) -> str:
    """Pure: assemble the single-feature extraction prompt (no I/O)."""
    context_json = json.dumps(context or {}, indent=2, default=str)
    known = ", ".join(KNOWN_LLM_FEATURES)
    return (
        f"{_SYSTEM}\n"
        f"KNOWN FEATURE NAMES (for reference, extend cautiously): {known}\n\n"
        f"FEATURE TO EXTRACT: {feature_name}\n\n"
        f"CONTEXT:\n{context_json}\n\n"
        f'Return JSON with keys: feature_name, value, confidence, rationale. '
        f'feature_name must be exactly "{feature_name}".'
    )


def parse_response(text: str) -> Optional[LLMFeatureOutput]:
    """Pure: parse+validate an Ollama response body. Returns None if unusable."""
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    return parse_llm_feature(data)


def call_ollama(config: Config, prompt: str) -> Optional[str]:
    """Impure: call Ollama's /api/generate with a strict JSON schema. Returns
    the raw response text, or None on any transport error (handled
    gracefully — a down/cold Ollama must never crash the pipeline)."""
    schema = LLMFeatureOutput.model_json_schema()
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


@dataclass
class ExtractResult:
    """The validated feature (or None if dropped) plus the full LLM trace, so
    every call is auditable — including dropped/invalid ones."""

    feature_name: str
    value: Optional[float]
    confidence: Optional[float]
    rationale: Optional[str]
    prompt: str
    response: Optional[str]   # raw model text (None on transport failure)
    valid: bool               # did the output validate?


def extract_feature_traced(
    config: Config,
    *,
    feature_name: str,
    context: dict,
) -> ExtractResult:
    """One LLM feature-extraction call: prompt -> Ollama -> validate. Returns
    the ExtractResult (feature=None if dropped) with the exact prompt + raw
    response for the audit trail."""
    prompt = build_prompt(feature_name, context)
    response = call_ollama(config, prompt)
    parsed = parse_response(response) if response is not None else None

    if parsed is None:
        return ExtractResult(
            feature_name=feature_name, value=None, confidence=None, rationale=None,
            prompt=prompt, response=response, valid=False,
        )
    if parsed.feature_name != feature_name:
        # The model must extract exactly the feature it was asked for — a
        # mismatched name is treated the same as invalid output (dropped).
        return ExtractResult(
            feature_name=feature_name, value=None, confidence=None, rationale=None,
            prompt=prompt, response=response, valid=False,
        )
    return ExtractResult(
        feature_name=feature_name, value=parsed.value, confidence=parsed.confidence,
        rationale=parsed.rationale, prompt=prompt, response=response, valid=True,
    )


def write_extracted_feature(
    conn,
    result: ExtractResult,
    *,
    ncaa_game_id: int,
    as_of_timestamp: datetime,
    season: Optional[int] = None,
    week: Optional[int] = None,
    model_name: str = "gemma3",
) -> bool:
    """Persist a valid ExtractResult to feature_values via
    feature_store.write_feature_value. No-op (returns False) if the
    extraction was dropped — an invalid LLM output must never reach the
    feature store, matching the drop-invalid rule enforced at parse time.
    """
    if not result.valid or result.value is None:
        return False

    from .feature_store import write_feature_value

    write_feature_value(
        conn, result.feature_name,
        ncaa_game_id=ncaa_game_id, season=season, week=week,
        value_num=result.value,
        as_of_timestamp=as_of_timestamp,
        source=f"llm:{model_name}",
        dtype="numeric", entity_level="game",
        # LLM-derived qualitative features are NOT treated as point-in-time
        # safe by default — they're commentary generated at extraction time,
        # not a fact known to have existed at ``as_of_timestamp`` the way a
        # box-score stat is. Flip explicitly per-feature once that's reviewed.
        point_in_time_safe=False,
    )
    return True


def insert_llm_call(
    conn,
    *,
    model: Optional[str],
    prompt: str,
    response: Optional[str],
    valid: bool,
) -> None:
    """Best-effort audit-trail insert into the shared ``llm_calls`` table
    (raw_id/factor_id are matchup_intel concepts and left NULL here — this
    table is generic schema, not matchup_intel-owned code). Never raises;
    losing an audit row must not break feature extraction."""
    try:
        conn.execute(
            """
            INSERT INTO llm_calls (raw_id, factor_id, model, prompt, response, valid)
            VALUES (NULL, NULL, %s, %s, %s, %s)
            """,
            (model, prompt, response, valid),
        )
    except Exception as exc:  # pragma: no cover - defensive, logged not raised
        print(f"[WARNING] insert_llm_call failed: {exc}")


def main() -> None:
    """CLI skeleton: extract one feature for one game from hand-supplied
    context JSON (no live CFBD/news ingestion is wired for this branch yet —
    that's a separate, not-yet-built ingestion pipeline, same caveat as
    feature_store.py).

    Usage: python -m ml.ensemble.llm_features <ncaa_game_id> <feature_name> <context_json_path>
    """
    import sys
    from datetime import timezone

    from .config import load_config

    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)

    ncaa_game_id = int(sys.argv[1])
    feature_name = sys.argv[2]
    with open(sys.argv[3]) as fh:
        context = json.load(fh)

    cfg = load_config()
    result = extract_feature_traced(cfg, feature_name=feature_name, context=context)
    print(f"valid={result.valid} value={result.value} confidence={result.confidence}")
    print(f"rationale={result.rationale!r}")

    if result.valid and cfg.database_url:
        from .feature_store import connect

        with connect(cfg.database_url) as conn:
            write_extracted_feature(
                conn, result, ncaa_game_id=ncaa_game_id,
                as_of_timestamp=datetime.now(timezone.utc), model_name=cfg.ollama_model,
            )
            insert_llm_call(
                conn, model=cfg.ollama_model, prompt=result.prompt,
                response=result.response, valid=result.valid,
            )
        print("[OK] Written to feature_values (+ llm_calls audit row).")
    elif not cfg.database_url:
        print("[INFO] DATABASE_URL not set — not persisting.")


if __name__ == "__main__":
    main()
