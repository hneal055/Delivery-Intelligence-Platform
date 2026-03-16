"""
Unit tests for the ETAPredictor ML model.
_load_model is patched during construction to avoid loading stale on-disk
models and _save_model is patched to avoid unnecessary disk I/O.
"""
import pytest
from unittest.mock import patch, MagicMock

from src.analytics.ml_models.eta_predictor import ETAPredictor


def _fresh_predictor():
    """Return an ETAPredictor that never touches disk."""
    with patch.object(ETAPredictor, "_load_model"):
        p = ETAPredictor()
    p.is_trained = False
    return p


class TestETAPredictorSyntheticData:
    def test_generate_returns_correct_sample_count(self):
        p = _fresh_predictor()
        X, y = p._generate_synthetic_data(n_samples=200)
        assert len(X) == 200
        assert len(y) == 200

    def test_generate_feature_columns_present(self):
        p = _fresh_predictor()
        X, y = p._generate_synthetic_data(n_samples=50)
        assert "distance_km" in X.columns
        assert "traffic_load" in X.columns

    def test_generate_distance_range(self):
        p = _fresh_predictor()
        X, y = p._generate_synthetic_data(n_samples=500)
        assert X["distance_km"].min() >= 0.5
        assert X["distance_km"].max() <= 20.0

    def test_generate_traffic_range(self):
        p = _fresh_predictor()
        X, y = p._generate_synthetic_data(n_samples=500)
        assert X["traffic_load"].min() >= 0.0
        assert X["traffic_load"].max() <= 1.0

    def test_generate_all_delays_above_minimum(self):
        p = _fresh_predictor()
        _, y = p._generate_synthetic_data(n_samples=300)
        assert all(y >= 5.0)


class TestETAPredictorTrain:
    def test_train_sets_is_trained(self):
        p = _fresh_predictor()
        with patch.object(p, "_save_model"):
            p.train()
        assert p.is_trained is True

    def test_train_model_is_fitted(self):
        p = _fresh_predictor()
        with patch.object(p, "_save_model"):
            p.train()
        assert hasattr(p.model, "n_estimators")

    def test_train_calls_save(self):
        p = _fresh_predictor()
        with patch.object(p, "_save_model") as mock_save:
            p.train()
        mock_save.assert_called_once()

    def test_retrain_sets_is_trained_again(self):
        p = _fresh_predictor()
        with patch.object(p, "_save_model"):
            p.train()
            p.train()
        assert p.is_trained is True


class TestETAPredictorPredict:
    def setup_method(self):
        self.p = _fresh_predictor()
        with patch.object(self.p, "_save_model"):
            self.p.train()

    def test_predict_returns_positive(self):
        result = self.p.predict(5.0, 0.5, 2)
        assert result >= 1.0

    def test_predict_clamps_to_minimum_one(self):
        result = self.p.predict(0.01, 0.0, 1)
        assert result >= 1.0

    def test_longer_distance_yields_higher_eta(self):
        short_eta = self.p.predict(1.0, 0.3, 1)
        long_eta = self.p.predict(15.0, 0.3, 1)
        assert long_eta > short_eta

    def test_high_traffic_yields_higher_eta(self):
        low_traffic = self.p.predict(5.0, 0.1, 1)
        high_traffic = self.p.predict(5.0, 0.9, 1)
        assert high_traffic > low_traffic

    def test_predict_auto_trains_if_untrained(self):
        p = _fresh_predictor()
        with patch.object(p, "_save_model"):
            result = p.predict(5.0, 0.5, 2)
        assert result >= 1.0
        assert p.is_trained is True

    def test_predict_with_zero_packages(self):
        result = self.p.predict(3.0, 0.5, 0)
        assert result >= 1.0
