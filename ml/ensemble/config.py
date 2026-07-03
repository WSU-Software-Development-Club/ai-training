"""Configuration for the stacked ensemble — config over hardcoding.

Precedence: environment variables > config.yaml (this dir) > built-in defaults.
Secrets (``DATABASE_URL``) come ONLY from the environment / a local ``.env``,
never from the committed yaml — mirrors ``ml/matchup_intel/config.py`` and the
top-level ``ml/`` convention (python-dotenv + os.getenv). Never print secret
values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional — yaml only needed if a config.yaml is present
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

_HERE = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    database_url: str | None

    # --- self-hosted LLM (feature-extraction branch only, never predicts) ---
    ollama_url: str
    ollama_model: str
    request_timeout: int

    # --- OOF stacking ---
    k_folds: int                 # K for the leakage-free OOF split
    random_state: int

    # --- two-stage upset / mispricing detection ---
    # |model_win_prob - market_implied_prob| >= this flags a mispricing.
    mispricing_threshold: float
    # Minimum rank gap (lower rank number = better) between predicted winner
    # and predicted loser for the predicted result to be flagged an "upset".
    upset_rank_gap: int

    # --- artifacts ---
    model_dir: Path


_DEFAULTS = {
    "ollama_url": "http://ollama:11434",
    "ollama_model": "gemma3",
    "request_timeout": 180,
    "k_folds": 5,
    "random_state": 42,
    "mispricing_threshold": 0.15,
    "upset_rank_gap": 10,
}


def _load_yaml() -> dict:
    path = _HERE / "config.yaml"
    if yaml is None or not path.exists():
        return {}
    with open(path) as fh:
        return yaml.safe_load(fh) or {}


def load_config() -> Config:
    if load_dotenv is not None:
        load_dotenv(dotenv_path=_HERE / ".env")

    file_cfg = _load_yaml()

    def pick(key, cast=str):
        env_key = key.upper()
        if os.getenv(env_key) is not None:
            return cast(os.getenv(env_key))
        if key in file_cfg and file_cfg[key] is not None:
            return cast(file_cfg[key])
        return _DEFAULTS.get(key)

    model_dir_str = pick("model_dir") or str(_HERE / "models")

    return Config(
        # Secret: env only.
        database_url=os.getenv("DATABASE_URL"),
        ollama_url=pick("ollama_url"),
        ollama_model=pick("ollama_model"),
        request_timeout=pick("request_timeout", int),
        k_folds=pick("k_folds", int),
        random_state=pick("random_state", int),
        mispricing_threshold=pick("mispricing_threshold", float),
        upset_rank_gap=pick("upset_rank_gap", int),
        model_dir=Path(model_dir_str),
    )
