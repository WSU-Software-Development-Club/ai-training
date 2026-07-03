"""The LLM-output validation boundary rejects malformed output (drops, no crash)."""

from __future__ import annotations

from ml.matchup_intel.schemas import LLMFactorOutput, parse_llm_factor


def _valid() -> dict:
    return {
        "category": "QB",
        "direction": "headwind",
        "magnitude": 0.4,
        "confidence": 0.6,
        "explanation": "Starter out, but the backup is a highly-rated recruit.",
    }


def test_valid_output_parses():
    result = parse_llm_factor(_valid())
    assert isinstance(result, LLMFactorOutput)
    assert result.direction == "headwind"
    assert result.magnitude == 0.4


def test_missing_required_field_is_dropped():
    bad = _valid()
    del bad["explanation"]
    assert parse_llm_factor(bad) is None


def test_magnitude_out_of_range_is_dropped():
    bad = _valid()
    bad["magnitude"] = 1.7  # outside [0, 1]
    assert parse_llm_factor(bad) is None

    bad["magnitude"] = -0.2
    assert parse_llm_factor(bad) is None


def test_invalid_direction_is_dropped():
    bad = _valid()
    bad["direction"] = "very good"  # not tailwind/headwind/neutral
    assert parse_llm_factor(bad) is None


def test_hallucinated_extra_field_is_dropped():
    # The LLM must never emit a game-outcome field; extra="forbid" rejects it.
    bad = _valid()
    bad["predicted_winner"] = "Home"
    assert parse_llm_factor(bad) is None


def test_empty_explanation_is_dropped():
    bad = _valid()
    bad["explanation"] = ""
    assert parse_llm_factor(bad) is None


def test_non_dict_input_does_not_raise():
    assert parse_llm_factor(None) is None
    assert parse_llm_factor("not json") is None
    assert parse_llm_factor(42) is None
