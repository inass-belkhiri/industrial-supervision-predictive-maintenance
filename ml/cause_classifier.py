# ml/cause_classifier.py
# Random Forest classifier for identifying the root cause of thermal anomalies.
# Classes: NORMAL | POMPE_DEFAILLANTE | BULLES_AIR | NIVEAU_BAS | CALCAIRE
#
# Architecture: hybrid — deterministic physical rules first, then RF for ambiguous cases.

import logging
import pickle
import os
import numpy as np
from typing import Optional, Dict, Tuple, List

from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

import config

log = logging.getLogger(__name__)

MODEL_PATH   = 'models/random_forest.pkl'
ENCODER_PATH = 'models/label_encoder.pkl'

CLASSES = [
    'CALCAIRE_TUYAUX',
    'HEATER_POMPE_HS',
    'HEATER_RESISTANCE_HS',
    'NIVEAU_BAS_VANNE_PANNE',
    'BULLES_AIR',
    'FUITE_CIRCUIT',
    'ISOLATION_DEGRADEE'
]


class CauseClassifier:
    """
    Two-level diagnostic:
        Level 1 — deterministic physical rules (100% certain cases)
        Level 2 — Random Forest for ambiguous cases
    """

    FEATURE_NAMES = [
        'slope_T_mold',
        'variance_T_mold',
        'affected_molds_ratio',
        'sudden_drop_flag',
        'flow_rate',
        'flow_drop_flag',
        'flow_variance',
        'delta_T_calcaire_slope',   # slope of delta_T_calcaire over 7 days
        'drift_R_squared',          # R^2 of linear fit on T_mold
        'autocorr_lag1',
    ]

    def __init__(self):
        self.model:   Optional[RandomForestClassifier] = None
        self.encoder: Optional[LabelEncoder]           = None
        self.trained: bool                             = False
        os.makedirs('models', exist_ok=True)
        self._load()

    # ── Level 1 — Physical rules ──────────────────────────────────────────────

    @staticmethod
    def physical_rules(
        affected_ratio:   float,
        sudden_drop:      bool,
        flow_rate:        float,
        flow_drop:        bool,
        temp_heater:      float = 45.0,
        nominal_flow:     float = 16.5,
    ) -> Optional[Dict]:
        """
        Apply deterministic physical rules.
        Returns a result dict if the case is certain, or None for ambiguous cases.
        """
        # Heater resistance failure: T_heater significantly below setpoint
        if temp_heater < 44.0 and affected_ratio > 0.8:
            return {
                'cause':      'HEATER_RESISTANCE_HS',
                'confidence': 1.0,
                'method':     'physical_rule',
            }

        # Pump failure: sudden global drop + flow collapse
        if affected_ratio > 0.8 and sudden_drop and flow_drop:
            return {
                'cause':      'HEATER_POMPE_HS',
                'confidence': 1.0,
                'method':     'physical_rule',
            }

        # Low water level / valve issue: many molds affected, flow very low but not zero
        if affected_ratio > 0.7 and flow_rate < 0.3 * nominal_flow and not sudden_drop:
            return {
                'cause':      'NIVEAU_BAS_VANNE_PANNE',
                'confidence': 1.0,
                'method':     'physical_rule',
            }

        return None   # ambiguous — use ML

    # ── Level 2 — Random Forest ───────────────────────────────────────────────

    def predict(self, features: np.ndarray) -> Dict:
        """
        Classify the cause from the 10-feature vector.
        Returns { cause, confidence, proba_dict, method }.
        """
        if not self.trained or self.model is None:
            return {'cause': 'NORMAL', 'confidence': 1.0, 'method': 'default', 'proba_dict': {}}

        proba  = self.model.predict_proba(features)[0]
        idx    = int(np.argmax(proba))
        cause  = self.encoder.inverse_transform([idx])[0]

        proba_dict = {cls: float(round(p, 3)) for cls, p in zip(self.encoder.classes_, proba)}

        return {
            'cause':      cause,
            'confidence': float(round(float(proba[idx]), 3)),
            'proba_dict': proba_dict,
            'method':     'random_forest',
        }

    # ── Training ─────────────────────────────────────────────────────────────

    def train(self, X: np.ndarray, y: List[str]):
        """
        Train the Random Forest on labeled examples.
        y is a list of string class labels.
        class_weight='balanced' compensates for class imbalance.
        """
        self.encoder = LabelEncoder()
        y_encoded    = self.encoder.fit_transform(y)

        self.model = RandomForestClassifier(
            n_estimators  = 100,
            class_weight  = 'balanced',
            max_depth     = 10,
            random_state  = 42,
            n_jobs        = -1,
        )
        self.model.fit(X, y_encoded)
        self.trained = True
        self._save()
        log.info(
            "Random Forest trained on %d samples, classes: %s",
            len(X), list(self.encoder.classes_)
        )

    def feature_importances(self) -> Dict[str, float]:
        """Returns feature importance scores for interpretability."""
        if self.model is None:
            return {}
        return dict(zip(self.FEATURE_NAMES, self.model.feature_importances_))

    # ── Auto-labeling for bootstrap ──────────────────────────────────────────

    @staticmethod
    def auto_label(
        affected_ratio:        float,
        sudden_drop:           bool,
        flow_drop:             bool,
        flow_rate:             float,
        variance:              float,
        R_squared:             float,
        delta_T_calcaire_slope: float,
        temp_heater:           float = 45.0,
        variance_threshold:    float = 0.1,
        nominal_flow:          float = 16.5,
    ) -> str:
        """
        Rule-based auto-labeling to generate training data from unlabeled history.
        """
        if temp_heater < 44.0 and affected_ratio > 0.8:
            return 'HEATER_RESISTANCE_HS'
        if affected_ratio > 0.8 and sudden_drop and flow_drop:
            return 'HEATER_POMPE_HS'
        if affected_ratio > 0.7 and flow_rate < 0.3 * nominal_flow:
            return 'NIVEAU_BAS_VANNE_PANNE'
        if variance > variance_threshold and R_squared < 0.3 and affected_ratio < 0.4:
            return 'BULLES_AIR'
        if delta_T_calcaire_slope > 0.03 and R_squared > 0.85:
            return 'CALCAIRE_TUYAUX'
        if affected_ratio < 0.3 and R_squared > 0.7:
            return 'ISOLATION_DEGRADEE'
        # Si aucune condition : on pourrait retourner la classe la plus probable
        # ou lever une exception, selon le contexte d'utilisation
        return 'FUITE_CIRCUIT'  # Classe par défaut pour cas ambigus

    # ── Persistence ──────────────────────────────────────────────────────────

    def _save(self):
        try:
            with open(MODEL_PATH,   'wb') as f: pickle.dump(self.model,   f)
            with open(ENCODER_PATH, 'wb') as f: pickle.dump(self.encoder, f)
            log.info("Random Forest saved")
        except Exception as exc:
            log.error("Could not save Random Forest: %s", exc)

    def _load(self):
        try:
            if os.path.exists(MODEL_PATH) and os.path.exists(ENCODER_PATH):
                with open(MODEL_PATH,   'rb') as f: self.model   = pickle.load(f)
                with open(ENCODER_PATH, 'rb') as f: self.encoder = pickle.load(f)
                self.trained = True
                log.info("Random Forest loaded from disk")
        except Exception as exc:
            log.warning("Could not load Random Forest: %s", exc)
