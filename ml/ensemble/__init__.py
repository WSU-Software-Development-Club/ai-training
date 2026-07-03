"""Stacked-ensemble CFB prediction + upset/mispricing detection.

SCOPE: this package is a SKELETON. It reads the point-in-time feature store
(``feature_definitions`` / ``feature_values`` in db/schema.sql) and defines the
full training/inference contract (base learners -> OOF stacking -> meta-learner
-> two-stage upset/mispricing scoring), but there is no real feature data in
the store yet (feature ingestion is a separate, not-yet-built pipeline). See
each module's docstring for exactly what is wired vs. stubbed.

Layout:
  - config.py            env/yaml-driven settings (K folds, thresholds, paths)
  - feature_store.py      point-in-time reader (as-of SQL) + catalog-first writer
  - base_learners.py      XGBoost/LightGBM regressors+classifiers, shared
                          fit/predict interface, leakage-free K-fold OOF predictions
  - stack.py              meta-learner that stacks OOF base predictions
  - upset_mispricing.py   stage-1 ensemble prediction -> stage-2 upset/mispricing flags
  - llm_features.py       Ollama/gemma3 FEATURE extraction (never predicts outcomes)
  - tests/                pure unit tests, no live DB / Ollama required

This module intentionally does NOT touch ``ml/matchup_intel/`` or the Flask
backend. It writes to Postgres directly (feature_values, and eventually its own
model outputs) — it never calls the backend API.
"""
