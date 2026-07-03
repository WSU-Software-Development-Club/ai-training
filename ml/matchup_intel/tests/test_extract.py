"""Layer-1 extraction: valid LLM output builds a Factor; bad/unreachable drops."""

from __future__ import annotations

import json
from datetime import timezone
from uuid import uuid4

from ml.matchup_intel import extract
from ml.matchup_intel.config import Config
from ml.matchup_intel.schemas import Factor

from .conftest import KICKOFF

CFG = Config(
    database_url=None, cfbd_api_key=None,
    ollama_url="http://ollama:11434", ollama_model="gemma3",
    sample_size_threshold=30, request_timeout=5,
    polymarket_enabled=True,
)

PAYLOAD = {
    "text": "Starter QB questionable; blue-chip backup looked sharp last week.",
    "supporting": {"backup_qb": {"recruit_stars": 4}},
    "sources": [{"url": "https://ex.com/a", "source_type": "injury_report"}],
    "category": "QB",
}


def _run(monkeypatch, response):
    monkeypatch.setattr(extract, "call_ollama", lambda cfg, prompt: response)
    return extract.extract_factor(
        CFG,
        raw_id=str(uuid4()),
        ncaa_game_id=990001,
        team_id=str(uuid4()),
        category="QB",
        payload=PAYLOAD,
        as_of_timestamp=KICKOFF,
        season=2024, week=7,
    )


def test_valid_llm_response_builds_factor(monkeypatch):
    resp = json.dumps({
        "category": "QB", "direction": "headwind",
        "magnitude": 0.35, "confidence": 0.6,
        "explanation": "Starter banged up but the blue-chip backup reduces the hit.",
    })
    factor = _run(monkeypatch, resp)
    assert isinstance(factor, Factor)
    assert factor.scoring_method == "llm"
    assert factor.direction == "headwind"
    assert factor.historical_rate is None and factor.sample_size == 0
    assert len(factor.derived_from_raw_ids) == 1
    assert factor.sources[0].source_type == "injury_report"
    assert factor.as_of_timestamp.tzinfo is not None


def test_invalid_llm_response_is_dropped(monkeypatch):
    # Hallucinated extra field -> validation rejects -> None (not a garbage Factor).
    resp = json.dumps({
        "category": "QB", "direction": "headwind", "magnitude": 0.5,
        "confidence": 0.6, "explanation": "x", "predicted_winner": "Home",
    })
    assert _run(monkeypatch, resp) is None


def test_unreachable_ollama_is_dropped(monkeypatch):
    # call_ollama returns None on transport failure -> no factor, no crash.
    assert _run(monkeypatch, None) is None


def test_non_json_response_is_dropped(monkeypatch):
    assert _run(monkeypatch, "the model rambled instead of returning json") is None
