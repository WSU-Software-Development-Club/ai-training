"""Matchup Intelligence Engine — does a fan's homework, not the prediction.

See db/schema.sql (teams, raw_signals, factors, factor_decks) and the
per-stage modules: ingest -> extract -> assemble/logic -> ground -> serve,
wired by flows.py (Prefect).
"""
