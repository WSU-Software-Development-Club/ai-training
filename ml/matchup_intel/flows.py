"""Prefect DAG wiring the QB vertical slice end to end.

    ingest (seed) -> extract+contextualize (LLM) -> ground -> serve

Idempotent and re-runnable: ingest dedupes on content_hash, factor decks upsert
on (game, team, as_of). Each stage fails independently (a game that errors does
not corrupt the others).

Prefect is preferred/optional: if it isn't installed the @task/@flow decorators
degrade to plain functions, so the pipeline still runs via `python -m
ml.matchup_intel.flows`.
"""

from __future__ import annotations

from datetime import datetime

try:  # Prefect preferred; degrade gracefully so the module always imports/runs.
    from prefect import flow, task
    from prefect.logging import get_run_logger
    _HAVE_PREFECT = True
except ImportError:  # pragma: no cover
    _HAVE_PREFECT = False

    def task(fn=None, **_kw):
        def wrap(f):
            return f
        return wrap(fn) if fn else wrap

    def flow(fn=None, **_kw):
        def wrap(f):
            return f
        return wrap(fn) if fn else wrap

    def get_run_logger():
        import logging
        return logging.getLogger("matchup_intel")

from uuid import UUID

from . import db, serve
from .config import Config, load_config
from .extract import extract_factor_traced
from .ground import ground_factor
from .ingest.polymarket_ingest import ingest_seed_odds
from .ingest.seed import ingest_seed, load_seed_games
from .ingest.seed_weather import ingest_weather_seed
from .schemas import Factor, Source
from .score.weather import score_weather


def _safe_sources(payload: dict) -> list[Source]:
    out = []
    for s in payload.get("sources", []) or []:
        try:
            out.append(Source.model_validate(s))
        except Exception:
            pass
    return out


def _weather_factor(row: dict, game: dict) -> Factor:
    """Build a weather Factor from a raw signal via the Layer-2 scorer (no LLM).
    The bucket is carried on `grounding` so the weather grounder can query history."""
    payload = row["payload"]
    ws = score_weather(payload.get("conditions", {}))
    return Factor(
        ncaa_game_id=game["ncaa_game_id"],
        game_id=game.get("cfbd_game_id"),
        season=game.get("season"),
        week=game.get("week"),
        team_id=row["team_id"] if isinstance(row["team_id"], UUID) else UUID(str(row["team_id"])),
        category="weather",
        raw_signal=payload.get("text"),
        direction=ws.direction,
        magnitude=ws.magnitude,
        confidence=ws.confidence,
        explanation=ws.explanation,
        scoring_method="model",              # grounding bumps to 'hybrid'
        sources=_safe_sources(payload),
        derived_from_raw_ids=[row["raw_id"] if isinstance(row["raw_id"], UUID) else UUID(str(row["raw_id"]))],
        grounding={"condition_bucket": ws.bucket},
        as_of_timestamp=row["as_of_timestamp"],
    )


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@task(retries=2, retry_delay_seconds=10)
def ingest_stage(cfg: Config) -> dict:
    with db.connect(cfg.database_url) as conn:
        summary = ingest_seed(conn)
        summary.update(ingest_weather_seed(conn))
        # Best-effort, gated by config: Polymarket coverage is sparse and the
        # source is optional, so a disabled/unreachable Polymarket must never
        # fail the ingest stage overall.
        if cfg.polymarket_enabled:
            summary.update(ingest_seed_odds(conn, timeout=cfg.request_timeout))
        return summary


@task(retries=2, retry_delay_seconds=10)
def extract_and_ground_stage(cfg: Config, game: dict) -> int:
    """LLM-extract + contextualize + ground every raw signal for one game."""
    log = get_run_logger()
    created = 0
    with db.connect(cfg.database_url) as conn:
        # Idempotent re-run: clear this game's prior factors + call records first.
        db.reset_game_factors(conn, game["ncaa_game_id"])
        rows = db.fetch_all_raw_signals_for_game(conn, game["ncaa_game_id"])
        for row in rows:
            if row.get("team_id") is None:
                continue  # can't attribute a factor to a team

            # Quantitative factors (weather, ...) use a Layer-2 scorer, NOT the
            # LLM, for magnitude — then get real historical grounding.
            if row["source_type"] == "weather":
                factor = _weather_factor(row, game)
                factor = ground_factor(factor, conn)
                db.insert_factor(conn, factor)
                created += 1
                continue

            result = extract_factor_traced(
                cfg,
                raw_id=str(row["raw_id"]),
                ncaa_game_id=game["ncaa_game_id"],
                team_id=str(row["team_id"]),
                category=row["payload"].get("category", "QB"),
                payload=row["payload"],
                as_of_timestamp=row["as_of_timestamp"],
                season=game.get("season"),
                week=game.get("week"),
                game_id=game.get("cfbd_game_id"),
            )
            factor_id = None
            if result.factor is not None:
                factor = ground_factor(result.factor, conn)
                factor_id = db.insert_factor(conn, factor)
                created += 1
            else:
                log.warning("LLM output dropped for raw_id=%s (invalid/unreachable)", row["raw_id"])
            # Persist the call for audit — even when the output was dropped.
            db.insert_llm_call(
                conn,
                raw_id=str(row["raw_id"]),
                factor_id=factor_id,
                model=cfg.ollama_model,
                prompt=result.prompt,
                response=result.response,
                valid=result.valid,
            )
    return created


@task(retries=2, retry_delay_seconds=10)
def serve_stage(cfg: Config, game: dict) -> dict:
    with db.connect(cfg.database_url) as conn:
        decks = serve.build_and_store_decks(
            conn,
            ncaa_game_id=game["ncaa_game_id"],
            kickoff=_parse_ts(game["kickoff"]),
            threshold=cfg.sample_size_threshold,
        )
    return {"ncaa_game_id": game["ncaa_game_id"], "teams": len(decks)}


@flow(name="matchup-intel-qb-slice")
def run_pipeline() -> list[dict]:
    cfg = load_config()
    if not cfg.database_url:
        raise RuntimeError("DATABASE_URL is not set (see ml/matchup_intel/env.example)")

    ingest_stage(cfg)

    results = []
    for game in load_seed_games():
        extract_and_ground_stage(cfg, game)
        results.append(serve_stage(cfg, game))
    return results


if __name__ == "__main__":
    print(run_pipeline())
