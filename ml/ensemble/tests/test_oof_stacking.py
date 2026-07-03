"""OOF stacking must never leak: a row's out-of-fold prediction must come
from a model that never trained on that row (directly proven), and stacking
a base model's own predictions on pure noise must not achieve suspiciously
low error (an indirect but concrete symptom of leakage).
"""

from __future__ import annotations

import numpy as np
import pytest

from ml.ensemble.base_learners import XGBRegressorLearner, oof_predictions
from ml.ensemble.stack import MeanMetaLearner, StackingEnsemble


class LeakDetectorLearner:
    """Fake base learner: fit() memorizes the set of row-ids it was trained
    on (id = last feature column); predict() returns 1.0 for a row whose id
    it has seen, 0.0 otherwise. If OOF stacking is leak-free, EVERY OOF
    prediction must be 0.0 — the model that predicted a row can never have
    seen that row during its own fit.
    """

    def __init__(self):
        self._seen_ids: set[float] = set()

    def fit(self, X, y):
        ids = np.asarray(X)[:, -1]
        self._seen_ids = set(ids.tolist())
        return self

    def predict(self, X):
        ids = np.asarray(X)[:, -1]
        return np.array([1.0 if i in self._seen_ids else 0.0 for i in ids])

    def predict_proba(self, X):
        return self.predict(X)


def _make_id_tagged_data(n: int, seed: int, binary_y: bool = False):
    rng = np.random.default_rng(seed)
    ids = np.arange(n, dtype=float)
    X = np.column_stack([rng.normal(size=n), ids])
    y = (rng.random(n) > 0.5).astype(int) if binary_y else rng.normal(size=n)
    return X, y


def test_oof_predictions_never_use_a_row_from_its_own_training_fold():
    X, y = _make_id_tagged_data(n=50, seed=0)
    result = oof_predictions(LeakDetectorLearner, X, y, k=5, task="regression")
    assert np.all(result.oof_predictions == 0.0), (
        "a nonzero OOF prediction means some row's id was seen by the model "
        "that predicted it — that model trained on data it was scored on"
    )


def test_oof_predictions_leak_free_for_classification_too():
    X, y = _make_id_tagged_data(n=40, seed=1, binary_y=True)
    result = oof_predictions(LeakDetectorLearner, X, y, k=5, task="classification")
    assert np.all(result.oof_predictions == 0.0)


def test_oof_predictions_cover_every_row_exactly_once():
    X, y = _make_id_tagged_data(n=37, seed=2)  # not evenly divisible by k
    result = oof_predictions(LeakDetectorLearner, X, y, k=5, task="regression")
    assert len(result.oof_predictions) == len(y)
    assert not np.isnan(result.oof_predictions).any()
    assert len(result.fold_models) == 5


def test_oof_predictions_requires_at_least_k_rows():
    X, y = _make_id_tagged_data(n=3, seed=3)
    with pytest.raises(ValueError):
        oof_predictions(LeakDetectorLearner, X, y, k=5, task="regression")


def test_full_model_is_fit_on_all_rows_not_just_folds():
    # The full_model (used at real inference time on brand-new games) should
    # have seen every training id — unlike any single fold model.
    X, y = _make_id_tagged_data(n=30, seed=4)
    result = oof_predictions(LeakDetectorLearner, X, y, k=5, task="regression")
    assert result.full_model.predict(X).tolist() == [1.0] * len(y)


def test_oof_does_not_trivially_memorize_pure_noise():
    """A flexible tree model with enough capacity CAN memorize pure noise
    in-sample. If OOF stacking leaked, OOF predictions on noise would also
    look suspiciously close to the noise itself. They should not: OOF error
    on unrelated-to-X noise should be roughly the noise's own variance, not
    near zero.
    """
    n = 60
    rng = np.random.default_rng(5)
    X = rng.normal(size=(n, 5))
    y = rng.normal(size=n)  # y is pure noise, independent of X

    def factory():
        return XGBRegressorLearner(params={"n_estimators": 200, "max_depth": 8})

    result = oof_predictions(factory, X, y, k=5, task="regression")
    oof_mse = float(np.mean((result.oof_predictions - y) ** 2))
    noise_var = float(np.var(y))
    assert oof_mse > 0.5 * noise_var, (
        f"OOF MSE ({oof_mse:.3f}) is suspiciously low relative to the noise's "
        f"own variance ({noise_var:.3f}) — looks like leakage"
    )


# --- stack.StackingEnsemble: the meta-learner only ever sees OOF columns ---


def test_stacking_ensemble_meta_features_are_leak_free():
    X, y = _make_id_tagged_data(n=40, seed=6)
    ensemble = StackingEnsemble(
        base_factories={"a": LeakDetectorLearner, "b": LeakDetectorLearner},
        meta_factory=MeanMetaLearner,
        k=5, task="regression",
    )
    ensemble.fit(X, y)
    # Every column of the OOF meta-feature matrix the meta-learner trained on
    # must be all-zero (leak-free), for both base learners.
    assert ensemble._last_oof_meta_X is not None
    assert np.all(ensemble._last_oof_meta_X == 0.0)


def test_stacking_ensemble_predicts_expected_shape():
    n = 40
    rng = np.random.default_rng(7)
    X = rng.normal(size=(n, 3))
    y = X[:, 0] * 2.0 + rng.normal(scale=0.1, size=n)

    def xgb_factory():
        return XGBRegressorLearner(params={"n_estimators": 50, "max_depth": 3})

    ensemble = StackingEnsemble(
        base_factories={"xgb_a": xgb_factory, "xgb_b": xgb_factory},
        meta_factory=MeanMetaLearner,
        k=4, task="regression",
    )
    ensemble.fit(X, y)

    X_new = rng.normal(size=(5, 3))
    preds = ensemble.predict(X_new)
    assert preds.shape == (5,)
    assert np.isfinite(preds).all()


def test_stacking_ensemble_requires_at_least_one_base_learner():
    with pytest.raises(ValueError):
        StackingEnsemble(base_factories={}).fit(np.zeros((10, 2)), np.zeros(10))
