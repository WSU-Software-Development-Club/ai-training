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

from . import db, serve
from .config import Config, load_config
from .extract import extract_factor
from .ground import ground_factor
from .ingest.seed import ingest_seed, load_seed_games


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@task(retries=2, retry_delay_seconds=10)
def ingest_stage(cfg: Config) -> dict:
    with db.connect(cfg.database_url) as conn:
        return ingest_seed(conn)


@task(retries=2, retry_delay_seconds=10)
def extract_and_ground_stage(cfg: Config, game: dict) -> int:
    """LLM-extract + contextualize + ground every raw signal for one game."""
    log = get_run_logger()
    created = 0
    with db.connect(cfg.database_url) as conn:
        rows = db.fetch_all_raw_signals_for_game(conn, game["ncaa_game_id"])
        for row in rows:
            if row.get("team_id") is None:
                continue  # can't attribute a factor to a team
            factor = extract_factor(
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
            if factor is None:
                log.warning("LLM output dropped for raw_id=%s (invalid/unreachable)", row["raw_id"])
                continue
            factor = ground_factor(factor, conn)
            db.insert_factor(conn, factor)
            created += 1
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
