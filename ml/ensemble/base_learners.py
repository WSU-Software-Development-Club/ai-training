"""Base learners (XGBoost + LightGBM) behind a shared fit/predict interface,
plus leakage-free out-of-fold (OOF) prediction generation for stacking.

WHY OOF MATTERS: a meta-learner trained on base-learner predictions must never
see a prediction a base model made on data it was also trained on — that would
let the meta-learner learn to trust overfit in-sample confidence rather than
genuine generalization. ``oof_predictions`` enforces this structurally: for
each of K folds, a base model is fit ONLY on the other K-1 folds and predicts
ONLY the held-out fold, so every row's OOF prediction comes from a model that
never saw that row's features or label during its own fit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Optional, Protocol, Sequence

import numpy as np
from sklearn.model_selection import KFold, StratifiedKFold

Task = Literal["regression", "classification"]


class Learner(Protocol):
    """The shared interface every base learner (and the meta-learner) exposes."""

    def fit(self, X: Any, y: Any) -> "Learner": ...

    def predict(self, X: Any) -> np.ndarray: ...


class ProbaLearner(Learner, Protocol):
    """Classifiers additionally expose calibrated-ish probabilities; stacking
    uses ``predict_proba`` (not the hard label) as the meta-feature."""

    def predict_proba(self, X: Any) -> np.ndarray: ...


LearnerFactory = Callable[[], Learner]


# --- concrete wrappers -------------------------------------------------------
# Thin adapters so the OOF/stacking code only ever depends on the Learner
# protocol above, never on xgboost/lightgbm APIs directly.


@dataclass
class XGBRegressorLearner:
    """Wraps xgboost.XGBRegressor. One margin/score-differential base learner."""

    params: dict = field(default_factory=dict)
    _model: Any = field(default=None, init=False, repr=False)

    def fit(self, X: Any, y: Any) -> "XGBRegressorLearner":
        import xgboost as xgb

        self._model = xgb.XGBRegressor(**self.params)
        self._model.fit(X, y)
        return self

    def predict(self, X: Any) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("XGBRegressorLearner.predict called before fit")
        return np.asarray(self._model.predict(X))


@dataclass
class XGBClassifierLearner:
    """Wraps xgboost.XGBClassifier. Win-probability / upset-probability learner."""

    params: dict = field(default_factory=dict)
    _model: Any = field(default=None, init=False, repr=False)

    def fit(self, X: Any, y: Any) -> "XGBClassifierLearner":
        import xgboost as xgb

        self._model = xgb.XGBClassifier(**self.params)
        self._model.fit(X, y)
        return self

    def predict(self, X: Any) -> np.ndarray:
        return np.asarray(self._model.predict(X))

    def predict_proba(self, X: Any) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("XGBClassifierLearner.predict_proba called before fit")
        return np.asarray(self._model.predict_proba(X))[:, 1]


@dataclass
class LGBMRegressorLearner:
    """Wraps lightgbm.LGBMRegressor. Requires the optional `lightgbm` dependency
    (see ml/ensemble/requirements.txt); the import is lazy so importing this
    module — or using only the XGBoost learners — never requires lightgbm."""

    params: dict = field(default_factory=dict)
    _model: Any = field(default=None, init=False, repr=False)

    def fit(self, X: Any, y: Any) -> "LGBMRegressorLearner":
        import lightgbm as lgb

        self._model = lgb.LGBMRegressor(**self.params)
        self._model.fit(X, y)
        return self

    def predict(self, X: Any) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("LGBMRegressorLearner.predict called before fit")
        return np.asarray(self._model.predict(X))


@dataclass
class LGBMClassifierLearner:
    """Wraps lightgbm.LGBMClassifier."""

    params: dict = field(default_factory=dict)
    _model: Any = field(default=None, init=False, repr=False)

    def fit(self, X: Any, y: Any) -> "LGBMClassifierLearner":
        import lightgbm as lgb

        self._model = lgb.LGBMClassifier(**self.params)
        self._model.fit(X, y)
        return self

    def predict(self, X: Any) -> np.ndarray:
        return np.asarray(self._model.predict(X))

    def predict_proba(self, X: Any) -> np.ndarray:
        if self._model is None:
            raise RuntimeError("LGBMClassifierLearner.predict_proba called before fit")
        return np.asarray(self._model.predict_proba(X))[:, 1]


# Registry used by train/inference scripts to build the default ensemble
# ("catalog-first" for models, same spirit as the feature catalog).
DEFAULT_REGRESSOR_FACTORIES: dict[str, LearnerFactory] = {
    "xgb": lambda: XGBRegressorLearner(params={"n_estimators": 300, "max_depth": 4}),
    "lgbm": lambda: LGBMRegressorLearner(params={"n_estimators": 300, "max_depth": 4, "verbosity": -1}),
}

DEFAULT_CLASSIFIER_FACTORIES: dict[str, LearnerFactory] = {
    "xgb": lambda: XGBClassifierLearner(params={"n_estimators": 300, "max_depth": 4}),
    "lgbm": lambda: LGBMClassifierLearner(params={"n_estimators": 300, "max_depth": 4, "verbosity": -1}),
}


# --- leakage-free OOF predictions -------------------------------------------


@dataclass
class OOFResult:
    """The OOF predictions (safe to use as stacking meta-features) plus the
    per-fold models (diagnostic only — NOT used at inference time) and a
    model fit on the FULL training set (used at inference time on new games,
    which is not leaky: at inference time the "held-out" data is a genuinely
    new game the model has never seen, unlike a training-set fold)."""

    oof_predictions: np.ndarray
    fold_models: list[Learner]
    full_model: Learner


def oof_predictions(
    factory: LearnerFactory,
    X: Any,
    y: Sequence,
    *,
    k: int = 5,
    task: Task = "regression",
    random_state: int = 42,
) -> OOFResult:
    """K-fold out-of-fold predictions for one base learner — the leakage-free
    meta-feature generator that ``stack.py`` consumes.

    For each fold: fit a FRESH model instance (from ``factory``) on the other
    K-1 folds, predict the held-out fold. Every row is predicted exactly once,
    by a model that never trained on it. A final model is also fit on the
    *entire* training set for use at inference time on genuinely new rows.
    """
    y_arr = np.asarray(y)
    n = len(y_arr)
    if n < k:
        raise ValueError(f"oof_predictions: n={n} rows is smaller than k={k} folds")

    if task == "classification":
        splitter = StratifiedKFold(n_splits=k, shuffle=True, random_state=random_state)
        split_args = (X, y_arr)
    else:
        splitter = KFold(n_splits=k, shuffle=True, random_state=random_state)
        split_args = (X,)

    oof = np.full(n, np.nan, dtype=float)
    fold_models: list[Learner] = []

    for train_idx, held_out_idx in splitter.split(*split_args):
        model = factory()
        X_train = _select_rows(X, train_idx)
        X_held = _select_rows(X, held_out_idx)
        model.fit(X_train, y_arr[train_idx])

        if task == "classification":
            preds = model.predict_proba(X_held)  # type: ignore[attr-defined]
        else:
            preds = model.predict(X_held)

        oof[held_out_idx] = preds
        fold_models.append(model)

    if np.isnan(oof).any():
        # Should be unreachable with KFold/StratifiedKFold (every row lands in
        # exactly one held-out fold), but fail loudly rather than silently
        # feed a leaked/garbage value into the meta-learner.
        missing = int(np.isnan(oof).sum())
        raise RuntimeError(f"oof_predictions: {missing} rows never got an OOF prediction")

    full_model = factory()
    full_model.fit(X, y_arr)

    return OOFResult(oof_predictions=oof, fold_models=fold_models, full_model=full_model)


def _select_rows(X: Any, idx: np.ndarray):
    """Index rows for either a pandas DataFrame or a numpy array."""
    if hasattr(X, "iloc"):
        return X.iloc[idx]
    return np.asarray(X)[idx]
