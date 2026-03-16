# ml/anomaly_detector.py
# Isolation Forest for unsupervised anomaly detection.
# Trained on normal operating data (first weeks of operation).
# Returns an anomaly score and a boolean flag.

import logging
import pickle
import os
import numpy as np
from typing import Optional, List, Dict, Tuple

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

import config

log = logging.getLogger(__name__)

MODEL_PATH  = 'models/isolation_forest.pkl'
SCALER_PATH = 'models/scaler_if.pkl'


class AnomalyDetector:
    """
    Wraps Isolation Forest with feature extraction and persistence.

    Features used (computed from a rolling 30-second window):
        - slope_T_mold          : mean linear slope of all mold temperatures
        - variance_T_mold       : mean variance across all molds
        - affected_molds_ratio  : fraction of molds below threshold
        - sudden_drop_flag      : 1 if any mold dropped > 1 degree in < 2 min
        - flow_rate             : current pump flow rate
        - flow_variance         : variance of flow over the window
        - delta_T_calcaire_mean : mean delta_T_calcaire across all molds
        - autocorr_lag1         : mean lag-1 autocorrelation of T_mold signals
    """

    FEATURE_NAMES = [
        'slope_T_mold',
        'variance_T_mold',
        'affected_molds_ratio',
        'sudden_drop_flag',
        'flow_rate',
        'flow_variance',
        'delta_T_calcaire_mean',
        'autocorr_lag1',
    ]

    def __init__(self):
        self.model:   Optional[IsolationForest] = None
        self.scaler:  Optional[StandardScaler]  = None
        self.trained: bool                      = False
        os.makedirs('models', exist_ok=True)
        self._load()

    # ── Feature extraction ────────────────────────────────────────────────────

    def extract_features(
        self,
        temp_history:       Dict[Tuple, List[float]],   # {mold_key: [t1, t2, ...]}
        flow_history:       List[float],
        delta_T_calcaires:  Dict[Tuple, float],
    ) -> Optional[np.ndarray]:
        """
        Extract the 8-feature vector from rolling histories.
        Returns None if not enough data is available.
        """
        window  = config.FEATURE_WINDOW_SECONDS
        all_temps = []

        slopes       = []
        variances    = []
        autocorrs    = []
        affected     = 0

        for key, hist in temp_history.items():
            if len(hist) < 10:
                continue
            arr = np.array(hist[-window:], dtype=float)
            all_temps.extend(arr.tolist())

            # Linear slope (degrees C / second)
            x  = np.arange(len(arr))
            slope = np.polyfit(x, arr, 1)[0] if len(arr) > 1 else 0.0
            slopes.append(slope)

            # Variance
            variances.append(float(np.var(arr)))

            # Lag-1 autocorrelation
            if len(arr) > 2:
                ac = float(np.corrcoef(arr[:-1], arr[1:])[0, 1])
                autocorrs.append(ac if not np.isnan(ac) else 0.0)

            # Affected flag
            if arr[-1] < config.T_MOLD_CRITICAL:
                affected += 1

        if not slopes:
            return None

        # Sudden drop: any mold that dropped more than 1 degree in the last 2 min
        sudden_drop = 0.0
        for key, hist in temp_history.items():
            if len(hist) >= 120:
                if hist[-1] - hist[-120] < -1.0:
                    sudden_drop = 1.0
                    break

        n_molds = max(len(temp_history), 1)

        flow_arr      = np.array(flow_history[-window:]) if flow_history else np.array([config.FLOW_DEFAULT_LPM])
        flow_mean     = float(np.mean(flow_arr))
        flow_var      = float(np.var(flow_arr))

        dT_mean = float(np.mean(list(delta_T_calcaires.values()))) if delta_T_calcaires else 0.0

        features = np.array([[
            float(np.mean(slopes)),
            float(np.mean(variances)),
            affected / n_molds,
            sudden_drop,
            flow_mean,
            flow_var,
            dT_mean,
            float(np.mean(autocorrs)) if autocorrs else 0.0,
        ]])

        return features

    # ── Training ─────────────────────────────────────────────────────────────

    def train(self, feature_matrix: np.ndarray):
        """
        Train Isolation Forest on a matrix of normal feature vectors.
        contamination=0.05 means we expect ~5% anomalies in the data.
        """
        self.scaler = StandardScaler()
        X_scaled    = self.scaler.fit_transform(feature_matrix)

        self.model = IsolationForest(
            n_estimators  = 200,
            contamination = 0.05,
            random_state  = 42,
            n_jobs        = -1,
        )
        self.model.fit(X_scaled)
        self.trained = True
        self._save()
        log.info("Isolation Forest trained on %d samples", len(feature_matrix))

    # ── Inference ────────────────────────────────────────────────────────────

    def predict(self, features: np.ndarray) -> Dict:
        """
        Returns { anomaly_detected: bool, anomaly_score: float }.
        anomaly_score: closer to 0 = more anomalous, closer to 1 = normal.
        """
        if not self.trained or self.model is None or self.scaler is None:
            return {'anomaly_detected': False, 'anomaly_score': None}

        X_scaled = self.scaler.transform(features)
        label    = self.model.predict(X_scaled)[0]      # +1 normal, -1 anomaly
        score    = self.model.score_samples(X_scaled)[0] # lower = more anomalous

        return {
            'anomaly_detected': bool(label == -1),
            'anomaly_score':    float(round(score, 4)),
        }

    # ── Persistence ──────────────────────────────────────────────────────────

    def _save(self):
        try:
            with open(MODEL_PATH,  'wb') as f: pickle.dump(self.model,  f)
            with open(SCALER_PATH, 'wb') as f: pickle.dump(self.scaler, f)
            log.info("Isolation Forest model saved")
        except Exception as exc:
            log.error("Could not save Isolation Forest: %s", exc)

    def _load(self):
        try:
            if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
                with open(MODEL_PATH,  'rb') as f: self.model  = pickle.load(f)
                with open(SCALER_PATH, 'rb') as f: self.scaler = pickle.load(f)
                self.trained = True
                log.info("Isolation Forest model loaded from disk")
        except Exception as exc:
            log.warning("Could not load Isolation Forest: %s", exc)
