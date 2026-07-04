# ML — Score Predictions

The score-prediction pipeline is **two independent XGBoost regressors** — one for the
home score, one for the away score (`reg:squarederror`, not a classifier, not
multi-output). Training is fully offline; a weekly job runs inference and writes rows
directly to the Postgres `predictions` table, which the API reads back.

- Source: [`ml/m1/`](../ml/m1/) (models) and [`ml/training_data/`](../ml/training_data/) (corpus)
- The ML pipeline **never calls the backend API** — it writes to Postgres directly.
- Distinct from the [Matchup Intelligence Engine](matchup-intelligence.md): this model uses both teams' features but has **no weather inputs**, and its output is shown in the matchup UI as a "reference panel," not as factor-deck content.

## Directory

**`ml/m1/`**
| File | Role |
| --- | --- |
| `train_model.py` | Offline training: load corpus, temporal split, optional Optuna search, train home/away regressors, save artifacts. |
| `predict_upcoming.py` | Weekly inference entry point: auto-detect season/week, rebuild features from CFBD, load models, predict, upsert to Postgres. |
| `pr_all.py` | Dev/backfill convenience: loops weeks 1–15 shelling out to `predict_upcoming.py 2025 <week>` (hardcoded year; **not** the scheduled job). |
| `models/` | Committed trained artifacts (do not hand-edit). |
| `results/` | Evaluation plots. |

**`ml/training_data/`**
| File | Role |
| --- | --- |
| `collect_data.py` | Historical corpus builder (CFBD, seasons 2003–2024) → `training_data.csv`. Also the shared home for feature functions that `predict_upcoming.py` imports so training and inference feature logic stay in sync. |
| `training_data.csv` | The flat training file consumed by `train_model.py`. |

**Model artifacts** (per model, `{home,away}_score_*`): `_model.json` (XGBoost native),
`_features.json` (**the ordered feature-name contract**), `_metrics.json`
(`{train,validation,test}: {mae, rmse, r2}`), `_feature_importance.csv`, plus
`optimized_params.json`.

## Training (`train_model.py`)

- **Data:** `ml/training_data/training_data.csv`.
- **Temporal split (no leakage):** train 2003–2021, validation 2022–2023, test 2024 (held out).
- **Targets:** `home_score`, `away_score`.
- **Features:** prior-season team ratings (SP+, SRS, ELO, FPI), advanced offense/defense stats (PPA, success rate, explosiveness, line yards), recruiting composite, 5-game exponentially-decayed **rolling** form (only games strictly before the game date), betting lines (`betting_spread`, `betting_over_under`, moneylines), game context (`neutral_site`, `conference_game`, `week`), and `matchup_*` interaction features (rating diffs, O-vs-D crossovers, style matchups). Missing numerics → column median.
- **Tuning:** Optuna (`TPESampler`, seed 42), 50 trials/model, objective = validation MAE; `n_estimators=500` with `early_stopping_rounds=50`. Toggled by `OPTIMIZE_HYPERPARAMS` in-file; best params also written to `models/optimized_params.json`.

Run:
```bash
cd ml/m1 && python train_model.py
```
> Paths/seasons/`RANDOM_STATE=42` are hardcoded module constants (no CLI args).
> **Retraining overwrites the committed `ml/m1/models/*` artifacts** — confirm before running.

## Prediction (`predict_upcoming.py`)

**Auto-detection:** with no args, `detect_season_phase()` queries CFBD `/calendar`
(month < 8 → prior year) and returns phase/year/week. Offseason → exits without writing.

**CLI overrides:** `python predict_upcoming.py [year] [week|postseason]`.

**Per game:**
1. Fetch upcoming CFBD games + NCAA scoreboard games for the target week.
2. Rebuild the exact training feature schema: current-season completed games for rolling features (excluding the prediction week+later), current-season betting lines, **prior-season** ratings/advanced-stats/recruiting (leakage rule). Align/coerce to each model's `*_features.json`; unmatched features → `0.0`.
3. `home_model.predict` / `away_model.predict` → rounded, floored at 0.
4. Derive `predicted_winner`, `predicted_margin`, `predicted_total`. If a betting line exists, `calculate_over_under_probability` models error as Normal(mean=total, sd=combined test-set MAE) → `over_probability`/`under_probability`.
5. Match CFBD game → NCAA game by date + both team names (large normalization table). **No NCAA match → the game is skipped, no row written** (main silent-loss point on low-match weeks).
6. If CFBD and NCAA disagree on home/away, teams+scores are swapped to match NCAA's convention.

**Env:** `CFBD_API_KEY`, `DATABASE_URL`. **Write:** `INSERT ... ON CONFLICT (ncaa_game_id) DO UPDATE` into `predictions`. On any Postgres error, falls back to writing `ml/m1/predictions_<timestamp>.json` locally (uploaded as a CI artifact) rather than losing the run.

## The `predictions` table contract

The writer populates (see [Database](database.md) for full types):

```
game_id, ncaa_game_id (UNIQUE, upsert key), season, week, game_date,
home_team, away_team, predicted_home_score, predicted_away_score,
predicted_winner, predicted_margin, predicted_total,
betting_over_under, over_probability, under_probability, prediction_made_at
```

`backend/utils/db.py` reads with `SELECT *` (no hardcoded column list), so a
writer-side **column addition** surfaces automatically — but a **rename/type change**
must be mirrored in `db/schema.sql` and the reader.

> **Known gap:** `predictions.neutral_site` exists in the schema but is **not** in the
> writer's column list, so it always reads back as its default `FALSE`, even for real
> neutral-site games.

## The weekly job

`.github/workflows/weekly_predictions.yml` — cron `0 9 * * 2` (Tue 09:00 UTC) + manual
`workflow_dispatch` (optional `year`/`week`). Runs on a **GitHub-hosted `ubuntu-latest`
runner** (not troyster): installs `ml/requirements.txt`, joins the tailnet via
`tailscale/github-action@v2` (`TS_AUTHKEY`, `tag:ci` — required because troyster
Postgres is Tailscale/LAN-only), then runs `predict_upcoming.py`. Uploads any
`predictions_*.json` fallback as an artifact. See [Deployment → CI/CD](deployment.md#cicd).
