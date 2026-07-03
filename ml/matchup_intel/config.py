"""Configuration for the matchup pipeline — config over hardcoding.

Precedence: environment variables > config.yaml > built-in defaults. Secrets
(DATABASE_URL, CFBD_API_KEY) come ONLY from the environment / a local .env,
never from the committed yaml. Mirrors the ml/ convention (python-dotenv +
os.getenv).
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
    cfbd_api_key: str | None
    ollama_url: str
    ollama_model: str
    # The sample-size guard threshold — a factor's historical_rate is only served
    # when sample_size >= this. Tune per how much evidence you require.
    sample_size_threshold: int
    request_timeout: int
    # Kill-switch for the Polymarket reference-panel input (Gamma/CLOB are
    # public, no-key endpoints — this exists for ops to disable lookups
    # entirely, e.g. if troyster egress to polymarket.com is blocked or
    # rate-limited, without a code change).
    polymarket_enabled: bool


_DEFAULTS = {
    "ollama_url": "http://ollama:11434",
    "ollama_model": "gemma3",
    "sample_size_threshold": 30,
    # Generous enough to tolerate a cold gemma3 load on the first inference
    # (the model is lazy-loaded into memory on first call).
    "request_timeout": 180,
    "polymarket_enabled": True,
}


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


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

    return Config(
        # Secrets: env only.
        database_url=os.getenv("DATABASE_URL"),
        cfbd_api_key=os.getenv("CFBD_API_KEY"),
        ollama_url=pick("ollama_url"),
        ollama_model=pick("ollama_model"),
        sample_size_threshold=pick("sample_size_threshold", int),
        request_timeout=pick("request_timeout", int),
        polymarket_enabled=pick("polymarket_enabled", _to_bool),
    )
