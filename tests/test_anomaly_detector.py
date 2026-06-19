import sys
import os
import numpy as np

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

from anomaly_detector import AnomalyDetector


def _make_temp_history(n_molds=2, n_points=30, base_temp=43.5):
    history = {}
    for i in range(n_molds):
        key = (i + 1, 1)
        history[key] = [base_temp + np.random.uniform(-0.3, 0.3) for _ in range(n_points)]
    return history


class TestAnomalyDetector:
    def test_extract_features_sufficient(self):
        detector = AnomalyDetector()
        temp_history = _make_temp_history(n_molds=2, n_points=30)
        flow_history = {1: [16.5 + np.random.uniform(-0.5, 0.5) for _ in range(30)]}
        delta_T_calcaires = {(1, 1): 0.5, (2, 1): 0.3}

        features = detector.extract_features(temp_history, flow_history, delta_T_calcaires)

        assert features is not None
        assert features.shape == (1, 8)
        assert features.dtype == np.float64

    def test_insufficient_data_and_untrained_model(self):
        detector = AnomalyDetector()

        temp_history = {(1, 1): [43.5] * 3}
        flow_history = {}
        delta_T_calcaires = {}

        features = detector.extract_features(temp_history, flow_history, delta_T_calcaires)
        assert features is None

        result = detector.predict(np.zeros((1, 8)))
        assert result['anomaly_detected'] is False
        assert result['anomaly_score'] is None
