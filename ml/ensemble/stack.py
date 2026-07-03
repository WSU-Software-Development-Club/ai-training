"""Meta-learner that stacks leakage-free OOF base-learner predictions.

``StackingEnsemble.fit`` never lets the meta-learner see a base model's
in-sample prediction: every training-row meta-feature comes from
``base_learners.oof_predictions`` (a model that did NOT train on that row).
At inference time (``predict``), each base learner's ``full_model`` (fit on
ALL training rows) predicts the new, genuinely-unseen row — which is not
leakage, since the row was never in the training set at all.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from .base_learners import Learner, LearnerFactory, Task, oof_predictions


def _predict_with(model: Any, X: Any, want_proba: bool) -> np.ndarray:
    """Uniform predict across our own Learner wrappers (predict_proba already
    1-D, positive-class probability) and raw sklearn-style estimators
    (predict_proba returns an (n, 2) array) — so the meta-learner can be
    either one of our wrappers or a plain sklearn LogisticRegression/Ridge."""
    if not want_proba:
        return np.asarray(model.predict(X))
    if not hasattr(model, "predict_proba"):
        raise AttributeError(f"{model!r} has no predict_proba but task='classification'")
    proba = np.asarray(model.predict_proba(X))
    if proba.ndim == 2 and proba.shape[1] == 2:
        return proba[:, 1]
    return proba.reshape(-1)


@dataclass
class MeanMetaLearner:
    """Trivial meta-learner: unweighted average of base-learner predictions.

    A reasonable default before there's enough training data to fit a real
    meta-learner (logistic/linear regression on 2-3 stacking columns needs
    at least a modest number of games) — swap in
    ``sklearn.linear_model.{Ridge,LogisticRegression}`` once there's real data.
    """

    def fit(self, X: Any, y: Any) -> "MeanMetaLearner":
        return self

    def predict(self, X: Any) -> np.ndarray:
        return np.asarray(X, dtype=float).mean(axis=1)

    def predict_proba(self, X: Any) -> np.ndarray:
        return self.predict(X)


@dataclass
class StackingEnsemble:
    """Fits N base learners via leakage-free OOF, then a meta-learner on the
    stacked OOF predictions. One instance = one target (e.g. margin, or
    home-win probability) — build two instances for the two-stage model in
    ``upset_mispricing.py`` (one regression stack for margin, one
    classification stack for win probability), or reuse one if margin alone
    is sufficient.
    """

    base_factories: dict[str, LearnerFactory]
    meta_factory: Callable[[], Any] = MeanMetaLearner
    k: int = 5
    task: Task = "regression"
    random_state: int = 42

    base_names: list[str] = field(init=False, default_factory=list)
    _base_models: dict[str, Learner] = field(init=False, default_factory=dict)
    _meta_model: Any = field(init=False, default=None)
    _last_oof_meta_X: np.ndarray | None = field(init=False, default=None, repr=False)

    def fit(self, X: Any, y: Any) -> "StackingEnsemble":
        if not self.base_factories:
            raise ValueError("StackingEnsemble requires at least one base learner")

        # Sorted for a deterministic column order between fit and predict.
        self.base_names = sorted(self.base_factories)
        oof_columns = []
        for name in self.base_names:
            result = oof_predictions(
                self.base_factories[name], X, y,
                k=self.k, task=self.task, random_state=self.random_state,
            )
            oof_columns.append(result.oof_predictions)
            self._base_models[name] = result.full_model

        meta_X = np.column_stack(oof_columns)
        self._last_oof_meta_X = meta_X

        self._meta_model = self.meta_factory()
        self._meta_model.fit(meta_X, np.asarray(y))
        return self

    def base_predictions(self, X: Any) -> dict[str, np.ndarray]:
        """Each fitted base learner's prediction on ``X`` (diagnostic + used
        internally by ``meta_features``/``predict``)."""
        if not self._base_models:
            raise RuntimeError("StackingEnsemble.base_predictions called before fit")
        want_proba = self.task == "classification"
        return {
            name: _predict_with(model, X, want_proba)
            for name, model in self._base_models.items()
        }

    def meta_features(self, X: Any) -> np.ndarray:
        preds = self.base_predictions(X)
        return np.column_stack([preds[name] for name in self.base_names])

    def predict(self, X: Any) -> np.ndarray:
        if self._meta_model is None:
            raise RuntimeError("StackingEnsemble.predict called before fit")
        meta_X = self.meta_features(X)
        want_proba = self.task == "classification"
        return _predict_with(self._meta_model, meta_X, want_proba)
