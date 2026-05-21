import logging
import numpy as np
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from sklearn.metrics import (
    f1_score, accuracy_score, classification_report, confusion_matrix
)

import config
from anomaly_detector import AnomalyDetector
from cause_classifier import CauseClassifier

log = logging.getLogger(__name__)


def fetch_recent(influx_module, minutes: int = 30) -> dict:
    raw = influx_module.query_recent(minutes=minutes)
    n_temps = len(raw.get('temperatures', []))
    n_flows = len(raw.get('flows', []))
    log.info(
        "Model health: fetched %d temperature points, %d flow points from last %d min",
        n_temps, n_flows, minutes
    )
    return raw


def build_feature_vectors(raw_data: dict) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    temps = raw_data.get('temperatures', [])
    flows = raw_data.get('flows', [])
    delta_T = raw_data.get('delta_T', [])

    if not temps:
        return None, None

    temp_by_key = defaultdict(list)
    for t in temps:
        key = (t['group'], t['mold'])
        temp_by_key[key].append(t['value'])

    flow_by_group = defaultdict(list)
    for f in flows:
        flow_by_group[f['group']].append(f['value'])

    dT_by_key = defaultdict(list)
    for d in delta_T:
        key = (d['group'], d['mold'])
        dT_by_key[key].append(d['value'])

    slopes = []
    variances = []
    autocorrs = []
    affected = 0
    n_molds = len(temp_by_key)

    for key, hist in temp_by_key.items():
        if len(hist) < 10:
            continue
        arr = np.array(hist[-config.FEATURE_WINDOW_SECONDS:], dtype=float)
        x = np.arange(len(arr))
        slope = np.polyfit(x, arr, 1)[0] if len(arr) > 1 else 0.0
        slopes.append(slope)
        variances.append(float(np.var(arr)))

        if len(arr) > 2:
            with np.errstate(invalid='ignore', divide='ignore'):
                ac = float(np.corrcoef(arr[:-1], arr[1:])[0, 1])
            autocorrs.append(ac if not np.isnan(ac) else 0.0)

        if arr[-1] < config.T_MOLD_WARNING:
            affected += 1

    if not slopes:
        return None, None

    sudden_drop = 0.0
    for key, hist in temp_by_key.items():
        if len(hist) >= 120 and hist[-1] - hist[-120] < -1.0:
            sudden_drop = 1.0
            break

    flow_means = [float(np.mean(v[-config.FEATURE_WINDOW_SECONDS:])) for v in flow_by_group.values() if v] or [config.FLOW_DEFAULT_LPM]
    flow_vars = [float(np.var(v[-config.FEATURE_WINDOW_SECONDS:])) for v in flow_by_group.values() if v] or [0.0]
    flow_mean = float(np.mean(flow_means))
    flow_var = float(np.mean(flow_vars))

    dT_mean = float(np.mean([np.mean(v) for v in dT_by_key.values()])) if dT_by_key else 0.0

    features_if = np.array([[
        float(np.mean(slopes)),
        float(np.mean(variances)),
        affected / max(n_molds, 1),
        sudden_drop,
        flow_mean,
        flow_var,
        dT_mean,
        float(np.mean(autocorrs)) if autocorrs else 0.0,
    ]])

    flow_drop = flow_mean < 0.5 * config.FLOW_DEFAULT_LPM
    dT_vals = [np.mean(v) for v in dT_by_key.values()] if dT_by_key else [0.0]
    delta_T_calcaire_slope = float(np.mean(dT_vals) / 7.0)

    all_temps_for_r2 = []
    for key, hist in temp_by_key.items():
        if len(hist) >= 10:
            all_temps_for_r2.extend(list(hist)[-300:])
    if all_temps_for_r2:
        x_arr = np.arange(len(all_temps_for_r2))
        coeffs = np.polyfit(x_arr, all_temps_for_r2, 1)
        y_pred = np.polyval(coeffs, x_arr)
        ss_res = np.sum((np.array(all_temps_for_r2) - y_pred) ** 2)
        ss_tot = np.sum((np.array(all_temps_for_r2) - np.mean(all_temps_for_r2)) ** 2)
        drift_R_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.9
    else:
        drift_R_squared = 0.9

    features_rf = np.array([[
        features_if[0][0],
        features_if[0][1],
        features_if[0][2],
        features_if[0][3],
        features_if[0][4],
        float(flow_drop),
        features_if[0][5],
        delta_T_calcaire_slope,
        drift_R_squared,
        features_if[0][7],
    ]])

    return features_if, features_rf


def auto_label_anomaly(raw_data: dict) -> np.ndarray:
    temps = raw_data.get('temperatures', [])
    flows = raw_data.get('flows', [])
    if not temps:
        return np.array([])

    temp_by_key = defaultdict(list)
    for t in temps:
        key = (t['group'], t['mold'])
        temp_by_key[key].append(t['value'])

    flow_vals = [f['value'] for f in flows] if flows else [config.FLOW_DEFAULT_LPM]
    flow_mean = float(np.mean(flow_vals)) if flow_vals else config.FLOW_DEFAULT_LPM

    affected_count = 0
    sudden_drop = 0.0
    for key, hist in temp_by_key.items():
        if not hist:
            continue
        if hist[-1] < config.T_MOLD_CRITICAL:
            affected_count += 1
        if len(hist) >= 120 and hist[-1] - hist[-120] < -1.0:
            sudden_drop = 1.0

    n_molds = len(temp_by_key)
    affected_ratio = affected_count / max(n_molds, 1)
    flow_drop = flow_mean < 0.5 * config.FLOW_DEFAULT_LPM

    is_anomaly = 1 if (affected_ratio > 0.3 or sudden_drop or flow_drop) else 0
    return np.array([is_anomaly])


def auto_label_cause(raw_data: dict) -> Optional[str]:
    temps = raw_data.get('temperatures', [])
    flows = raw_data.get('flows', [])
    delta_T = raw_data.get('delta_T', [])

    if not temps:
        return None

    temp_by_key = defaultdict(list)
    for t in temps:
        key = (t['group'], t['mold'])
        temp_by_key[key].append(t['value'])

    flow_vals = [f['value'] for f in flows] if flows else [config.FLOW_DEFAULT_LPM]
    flow_mean = float(np.mean(flow_vals)) if flow_vals else config.FLOW_DEFAULT_LPM

    dT_vals = [np.mean([v['value'] for v in delta_T if v['group'] == g]) for g in set(v['group'] for v in delta_T)] if delta_T else [0.0]

    affected_count = 0
    sudden_drop = 0.0
    high_variance = 0
    for key, hist in temp_by_key.items():
        if not hist:
            continue
        if hist[-1] < config.T_MOLD_WARNING:
            affected_count += 1
        if len(hist) >= 120 and hist[-1] - hist[-120] < -1.0:
            sudden_drop = 1.0
        if len(hist) >= 30 and float(np.var(hist[-30:])) > 0.1:
            high_variance += 1

    n_molds = len(temp_by_key)
    affected_ratio = affected_count / max(n_molds, 1)
    flow_drop = flow_mean < 0.5 * config.FLOW_DEFAULT_LPM
    delta_T_slope = float(np.mean(dT_vals) / 7.0) if dT_vals else 0.0

    variance_ratio = high_variance / max(n_molds, 1)

    return CauseClassifier.auto_label(
        affected_ratio=affected_ratio,
        sudden_drop=bool(sudden_drop),
        flow_drop=flow_drop,
        flow_rate=flow_mean,
        variance=variance_ratio,
        R_squared=0.5,
        delta_T_calcaire_slope=delta_T_slope,
    )


def evaluate_isolation_forest(
    iso_forest: AnomalyDetector,
    features: np.ndarray,
    pseudo_labels: np.ndarray,
) -> Dict:
    if not iso_forest.trained or features is None or len(pseudo_labels) == 0:
        return {'anomaly_rate': 0.0, 'error': 'model not trained or no data'}

    result = iso_forest.predict(features)
    detected = 1 if result['anomaly_detected'] else 0
    true_label = int(pseudo_labels[0])

    tp = 1 if (detected == 1 and true_label == 1) else 0
    fp = 1 if (detected == 1 and true_label == 0) else 0
    fn = 1 if (detected == 0 and true_label == 1) else 0
    tn = 1 if (detected == 0 and true_label == 0) else 0

    anomaly_rate = float(result.get('anomaly_score', 0))
    score = result.get('anomaly_score')

    return {
        'anomaly_detected': bool(detected),
        'true_label': true_label,
        'anomaly_score': score,
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
        'anomaly_rate': float(detected),
    }


def evaluate_random_forest(
    rf: CauseClassifier,
    features: np.ndarray,
    true_cause: str,
) -> Dict:
    if not rf.trained or features is None or true_cause is None:
        return {'f1_weighted': 0.0, 'error': 'model not trained or no data'}

    result = rf.predict(features)
    pred_cause = result['cause']
    confidence = result['confidence']

    correct = 1 if pred_cause == true_cause else 0

    return {
        'predicted_cause': pred_cause,
        'true_cause': true_cause,
        'confidence': confidence,
        'correct': bool(correct),
        'f1_weighted': float(correct),
    }


def should_retrain(
    metrics_history: Dict[str, List],
    if_anomaly_rate_max: float = 0.15,
    rf_f1_weighted_min: float = 0.75,
    persistence: int = 3,
) -> Tuple[bool, str]:
    if_rates = metrics_history.get('if_anomaly_rate', [])
    rf_f1s = metrics_history.get('rf_f1_weighted', [])

    reasons = []

    if len(if_rates) >= persistence:
        recent_if = if_rates[-persistence:]
        if all(r > if_anomaly_rate_max for r in recent_if):
            reasons.append(
                f"IF anomaly rate > {if_anomaly_rate_max} for {persistence} evaluations"
            )

    if len(rf_f1s) >= persistence:
        recent_rf = rf_f1s[-persistence:]
        if all(f < rf_f1_weighted_min for f in recent_rf):
            reasons.append(
                f"RF F1-weighted < {rf_f1_weighted_min} for {persistence} evaluations"
            )

    if reasons:
        return True, "; ".join(reasons)
    return False, ""


def run_evaluation(
    iso_forest: AnomalyDetector,
    rf: CauseClassifier,
    influx_module,
    minutes: int = 30,
) -> Tuple[Dict, Dict]:
    raw = fetch_recent(influx_module, minutes=minutes)

    features_if, features_rf = build_feature_vectors(raw)

    if features_if is None:
        log.warning("Model health: not enough data to build features")
        return {'error': 'insufficient data'}, {'error': 'insufficient data'}

    if_metrics = evaluate_isolation_forest(
        iso_forest, features_if, auto_label_anomaly(raw)
    )

    true_cause = auto_label_cause(raw)
    rf_metrics = evaluate_random_forest(rf, features_rf, true_cause)

    log.info(
        "Model health — IF: anomaly=%s score=%s | RF: pred=%s true=%s conf=%.2f",
        if_metrics.get('anomaly_detected'),
        if_metrics.get('anomaly_score'),
        rf_metrics.get('predicted_cause', 'N/A'),
        rf_metrics.get('true_cause', 'N/A'),
        rf_metrics.get('confidence', 0),
    )

    return if_metrics, rf_metrics
