"""The LLM feature-output validation boundary rejects malformed output
(drops, never crashes) — including any attempt to sneak in a game-outcome
field, which would violate "the LLM never predicts the outcome".
"""

from __future__ import annotations

from ml.ensemble.llm_features import build_prompt, parse_response
from ml.ensemble.schemas import LLMFeatureOutput, parse_llm_feature


def _valid() -> dict:
    return {
        "feature_name": "coaching_edge_score",
        "value": 0.4,
        "confidence": 0.6,
        "rationale": "Home staff has a strong track record in short-week turnarounds.",
    }


def test_valid_output_parses():
    result = parse_llm_feature(_valid())
    assert isinstance(result, LLMFeatureOutput)
    assert result.feature_name == "coaching_edge_score"
    assert result.value == 0.4


def test_missing_required_field_is_dropped():
    bad = _valid()
    del bad["rationale"]
    assert parse_llm_feature(bad) is None


def test_value_out_of_range_is_dropped():
    bad = _valid()
    bad["value"] = 1.7  # outside [-1, 1]
    assert parse_llm_feature(bad) is None

    bad["value"] = -1.2
    assert parse_llm_feature(bad) is None


def test_confidence_out_of_range_is_dropped():
    bad = _valid()
    bad["confidence"] = 1.5
    assert parse_llm_feature(bad) is None

    bad["confidence"] = -0.1
    assert parse_llm_feature(bad) is None


def test_hallucinated_outcome_field_is_dropped():
    # The LLM must never emit a game-outcome field; extra="forbid" rejects it.
    bad = _valid()
    bad["predicted_winner"] = "Home"
    assert parse_llm_feature(bad) is None

    bad2 = _valid()
    bad2["predicted_score"] = 27
    assert parse_llm_feature(bad2) is None


def test_empty_rationale_is_dropped():
    bad = _valid()
    bad["rationale"] = ""
    assert parse_llm_feature(bad) is None


def test_empty_feature_name_is_dropped():
    bad = _valid()
    bad["feature_name"] = ""
    assert parse_llm_feature(bad) is None


def test_non_dict_input_does_not_raise():
    assert parse_llm_feature(None) is None
    assert parse_llm_feature("not json") is None
    assert parse_llm_feature(42) is None
    assert parse_llm_feature([1, 2, 3]) is None


# --- llm_features.py glue: prompt building + response parsing --------------


def test_build_prompt_includes_feature_name_and_context():
    prompt = build_prompt("momentum_score", {"recent_form": "won 4 straight"})
    assert "momentum_score" in prompt
    assert "won 4 straight" in prompt
    # The system preamble must explicitly instruct the model NOT to predict
    # the outcome — the LLM is a feature extractor, never a predictor.
    assert "do not predict the game outcome" in prompt.lower()


def test_parse_response_valid_json():
    import json

    text = json.dumps(_valid())
    result = parse_response(text)
    assert isinstance(result, LLMFeatureOutput)


def test_parse_response_invalid_json_does_not_raise():
    assert parse_response("not json at all") is None
    assert parse_response("") is None


def test_parse_response_valid_json_but_invalid_schema():
    import json

    bad = _valid()
    bad["value"] = 5.0
    assert parse_response(json.dumps(bad)) is None
