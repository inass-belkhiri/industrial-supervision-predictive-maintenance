# ml/ridge_predictor.py
# Ridge polynomial regression for predicting the date of calcaire maintenance.
# Uses bootstrap (1000 simulations) to compute confidence intervals.
# Retrained daily at 2 AM from InfluxDB historical data.

import logging
import pickle
import os
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple

from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures

import config

log = logging.getLogger(__name__)

MODEL_DIR = 'models/ridge'


class RidgePredictor:
    """
    Per-mold Ridge polynomial predictor.
    One model instance per (group_id, mold_id) pair.
    """

    def __init__(self, group_id: int, mold_id: int, delta_T_max: float):
        self.group_id   = group_id
        self.mold_id    = mold_id
        self.delta_T_max = max(delta_T_max, 0.1)
        self.poly        = PolynomialFeatures(degree=2, include_bias=True)
        self.model:  Optional[Ridge] = None
        self.X_data: Optional[np.ndarray] = None
        self.y_data: Optional[np.ndarray] = None
        self.n_days: int = 0
        os.makedirs(MODEL_DIR, exist_ok=True)
        self._load()

    # ── Training ─────────────────────────────────────────────────────────────

    def fit(self, daily_records: List[Dict]):
        """
        Train the Ridge model from a list of daily records.
        Each record: { 'day_offset': int, 'value': float (delta_T_calcaire) }
        Requires at least RIDGE_MIN_DAYS records.
        """
        if len(daily_records) < config.RIDGE_MIN_DAYS:
            log.info(
                "Ridge mold (%d,%d): not enough data (%d < %d days)",
                self.group_id, self.mold_id, len(daily_records), config.RIDGE_MIN_DAYS
            )
            return

        X_raw = np.array([r['day_offset'] for r in daily_records]).reshape(-1, 1)
        y     = np.array([r['value']      for r in daily_records])

        X_poly    = self.poly.fit_transform(X_raw)
        self.model = Ridge(alpha=1.0)
        self.model.fit(X_poly, y)

        self.X_data = X_raw
        self.y_data = y
        self.n_days = len(daily_records)
        self._save()
        log.info("Ridge mold (%d,%d) trained on %d days", self.group_id, self.mold_id, self.n_days)

    # ── Prediction ───────────────────────────────────────────────────────────

    def predict_maintenance(self) -> Optional[Dict]:
        """
        Predict how many days until delta_T_calcaire reaches delta_T_max (critical threshold).
        Returns None if the model is not ready.

        Returns a dict:
            jours_maintenance  : int   — median prediction
            borne_basse        : int   — 5th percentile (worst credible case)
            borne_haute        : int   — 95th percentile (best credible case)
            predicted_date     : str   — ISO date of recommended maintenance
            n_bootstrap        : int   — number of bootstrap iterations used
        """
        if self.model is None or self.X_data is None:
            return None

        N     = len(self.X_data)
        start = int(self.X_data[-1]) + 1
        # Predict up to 365 days into the future
        X_future = np.arange(start, start + 366).reshape(-1, 1)
        X_f_poly = self.poly.transform(X_future)

        # Central prediction
        y_pred = self.model.predict(X_f_poly)
        idx    = self._find_crossing(y_pred)
        if idx is None:
            return None
        central = int(idx)

        # Bootstrap confidence interval
        crossing_days = []
        for _ in range(config.BOOTSTRAP_N):
            indices  = np.random.choice(N, size=N, replace=True)
            X_boot   = self.poly.transform(self.X_data[indices])
            y_boot   = self.y_data[indices]
            m        = Ridge(alpha=1.0)
            m.fit(X_boot, y_boot)
            y_b      = m.predict(X_f_poly)
            i_b      = self._find_crossing(y_b)
            if i_b is not None:
                crossing_days.append(int(i_b))

        if not crossing_days:
            return None

        borne_basse = int(np.percentile(crossing_days, 5))
        borne_haute = int(np.percentile(crossing_days, 95))
        median      = int(np.percentile(crossing_days, 50))

        predicted_date = (datetime.today() + timedelta(days=borne_basse)).strftime('%d/%m/%Y')

        return {
            'jours_maintenance': median,
            'borne_basse':       borne_basse,
            'borne_haute':       borne_haute,
            'predicted_date':    predicted_date,
            'n_bootstrap':       len(crossing_days),
        }

    def _find_crossing(self, y_pred: np.ndarray) -> Optional[int]:
        """Return the index (= days from now) when y_pred first exceeds delta_T_max."""
        crossings = np.where(y_pred >= self.delta_T_max)[0]
        return int(crossings[0]) if len(crossings) > 0 else None

    # ── Persistence ──────────────────────────────────────────────────────────

    def _save(self):
        path = os.path.join(MODEL_DIR, f'ridge_{self.group_id}_{self.mold_id}.pkl')
        try:
            with open(path, 'wb') as f:
                pickle.dump({'model': self.model, 'X': self.X_data, 'y': self.y_data,
                             'n': self.n_days, 'poly': self.poly}, f)
        except Exception as exc:
            log.error("Could not save Ridge mold (%d,%d): %s", self.group_id, self.mold_id, exc)

    def _load(self):
        path = os.path.join(MODEL_DIR, f'ridge_{self.group_id}_{self.mold_id}.pkl')
        try:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    d = pickle.load(f)
                self.model  = d['model']
                self.X_data = d['X']
                self.y_data = d['y']
                self.n_days = d['n']
                self.poly   = d['poly']
                log.info("Ridge mold (%d,%d) loaded from disk", self.group_id, self.mold_id)
        except Exception as exc:
            log.warning("Could not load Ridge mold (%d,%d): %s", self.group_id, self.mold_id, exc)
