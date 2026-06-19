import sys
import os
import numpy as np

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

from ridge_predictor import RidgePredictor


class TestRidgePredictor:
    def test_fit_insufficient_data(self):
        predictor = RidgePredictor(group_id=1, mold_id=1, delta_T_max=5.0)
        predictor._save = lambda: None
        predictor._load = lambda: None

        predictor.fit([
            {'day_offset': 0, 'value': 1.0},
            {'day_offset': 1, 'value': 1.2},
        ])

        assert predictor.model is None
        assert predictor.predict_maintenance() is None

    def test_find_crossing(self):
        predictor = RidgePredictor(group_id=1, mold_id=1, delta_T_max=3.0)

        y_pred = np.array([0.5, 1.0, 2.0, 3.0, 4.0, 5.0])
        idx = predictor._find_crossing(y_pred)
        assert idx == 3

        y_pred2 = np.array([0.5, 1.0, 1.5, 2.0])
        idx2 = predictor._find_crossing(y_pred2)
        assert idx2 is None

    def test_bootstrap_consistency(self):
        predictor = RidgePredictor(group_id=1, mold_id=1, delta_T_max=5.0)
        predictor._save = lambda: None
        predictor._load = lambda: None

        records = [
            {'day_offset': i, 'value': 0.5 + i * 0.3}
            for i in range(14)
        ]
        predictor.fit(records)

        result = predictor.predict_maintenance()

        if result is not None:
            assert result['borne_basse'] <= result['jours_maintenance'] <= result['borne_haute']
            assert result['n_bootstrap'] > 0
