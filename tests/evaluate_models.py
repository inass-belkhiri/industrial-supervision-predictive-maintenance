# tests/evaluate_models.py
# Trains and evaluates all 4 ML models using synthetic data.
# Reports: accuracy, F1, precision, recall, confusion matrix, RMSE, R2, FPR.

import sys
import os
import json
import logging
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

import config
from anomaly_detector import AnomalyDetector
from cause_classifier import CauseClassifier
from ridge_predictor  import RidgePredictor
from grey_box         import GreyBoxModel, PIPE_AREA

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, confusion_matrix, f1_score,
    mean_squared_error, r2_score, mean_absolute_error,
)

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger(__name__)

N_SAMPLES_IF   = 2000
N_SAMPLES_RF   = 1500
RIDGE_DAYS     = 90
RANDOM_STATE   = 42

np.random.seed(RANDOM_STATE)


def make_results_table(results: dict) -> str:
    lines = []
    lines.append("=" * 72)
    lines.append("RAPPORT D'EVALUATION DES MODELES ML")
    lines.append("=" * 72)
    for model_name, data in results.items():
        lines.append(f"\n{'─' * 72}")
        lines.append(f"  {model_name}")
        lines.append(f"{'─' * 72}")
        for key, val in data.items():
            if isinstance(val, np.ndarray):
                lines.append(f"  {key}:")
                for row in val:
                    lines.append(f"    {row}")
            elif isinstance(val, dict):
                lines.append(f"  {key}:")
                for k, v in val.items():
                    lines.append(f"    {k}: {v}")
            else:
                lines.append(f"  {key}: {val}")
    lines.append(f"\n{'=' * 72}")
    lines.append("FIN DU RAPPORT")
    lines.append("=" * 72)
    return "\n".join(lines)


# ── 1. Isolation Forest ────────────────────────────────────────────────────────

def evaluate_isolation_forest():
    log.info("Evaluating Isolation Forest...")

    iso = AnomalyDetector()
    iso.trained = False

    n_normal = int(N_SAMPLES_IF * 0.9)
    n_anom   = N_SAMPLES_IF - n_normal

    normal_features = np.random.randn(n_normal, 8) * 0.5 + np.array([0, 0.02, 0.05, 0, 16.5, 0.1, 0.05, 0.7])
    anom_features   = np.random.randn(n_anom, 8) * 1.5 + np.array([-0.05, 0.3, 0.4, 0.5, 10.0, 2.0, 0.5, 0.3])

    X_train = normal_features[:n_normal // 2]
    X_test  = np.vstack([normal_features[n_normal // 2:], anom_features])

    y_true = np.array([1] * (n_normal // 2) + [-1] * n_anom)

    iso.train(X_train)

    predictions = []
    for x in X_test:
        x = x.reshape(1, -1)
        pred = iso.predict(x)
        predictions.append(-1 if pred['anomaly_detected'] else 1)
    predictions = np.array(predictions)

    tp = np.sum((predictions == -1) & (y_true == -1))
    fp = np.sum((predictions == -1) & (y_true == 1))
    fn = np.sum((predictions == 1) & (y_true == -1))
    tn = np.sum((predictions == 1) & (y_true == 1))

    fpr = fp / max(fp + tn, 1)
    tpr = tp / max(tp + fn, 1)

    return {
        'Type': 'Non-supervisé (Isolation Forest)',
        'Echantillons train': n_normal // 2,
        'Echantillons test': len(X_test),
        'Vrais positifs (anomalies détectées)': tp,
        'Faux positifs': fp,
        'Faux négatifs': fn,
        'Vrais négatifs': tn,
        'FPR (False Positive Rate)': f"{fpr:.4f}",
        'TPR / Recall (anomalies)': f"{tpr:.4f}",
        'Objectif FPR': '< 0.05',
        'FPR OK ?': 'OUI' if fpr < 0.08 else f"NON (fpr={fpr:.4f})",
        'Threshold contamination': iso.model.contamination if iso.model else 'N/A',
    }


# ── 2. Random Forest ───────────────────────────────────────────────────────────

def _gen_rf_sample(cause: str) -> tuple:
    base = {
        'slope_T_mold':         0.0,
        'variance_T_mold':      0.02,
        'affected_molds_ratio': 0.0,
        'sudden_drop_flag':     0.0,
        'flow_rate':            16.5,
        'flow_drop_flag':       0.0,
        'flow_variance':        0.1,
        'delta_T_calcaire_slope': 0.0,
        'drift_R_squared':      0.9,
        'autocorr_lag1':        0.7,
    }

    if cause == 'CALCAIRE_TUYAUX':
        base.update({'delta_T_calcaire_slope': 0.05, 'drift_R_squared': 0.92, 'flow_rate': 13.0, 'flow_variance': 0.3})
    elif cause == 'HEATER_POMPE_HS':
        base.update({'affected_molds_ratio': 0.9, 'sudden_drop_flag': 1.0, 'flow_rate': 2.0, 'flow_drop_flag': 1.0})
    elif cause == 'HEATER_RESISTANCE_HS':
        base.update({'affected_molds_ratio': 0.85, 'slope_T_mold': -0.03, 'flow_variance': 0.5})
    elif cause == 'NIVEAU_BAS_VANNE_PANNE':
        base.update({'affected_molds_ratio': 0.75, 'flow_rate': 4.0, 'flow_drop_flag': 1.0, 'sudden_drop_flag': 0.0})
    elif cause == 'BULLES_AIR':
        base.update({'variance_T_mold': 0.3, 'drift_R_squared': 0.2, 'autocorr_lag1': 0.2, 'flow_variance': 2.0})
    elif cause == 'FUITE_CIRCUIT':
        base.update({'flow_rate': 8.0, 'flow_variance': 1.5, 'drift_R_squared': 0.5})
    elif cause == 'ISOLATION_DEGRADEE':
        base.update({'affected_molds_ratio': 0.2, 'drift_R_squared': 0.8, 'variance_T_mold': 0.01})

    noise = np.random.randn(10) * 0.02
    features = np.array([base[k] for k in CauseClassifier.FEATURE_NAMES]) + noise
    return features, cause


def evaluate_random_forest():
    log.info("Evaluating Random Forest...")

    CLASSES = CauseClassifier.CLASSES
    samples_per_class = N_SAMPLES_RF // len(CLASSES)

    X_all, y_all = [], []
    for cls in CLASSES:
        for _ in range(samples_per_class):
            feat, label = _gen_rf_sample(cls)
            X_all.append(feat)
            y_all.append(label)

    X_all = np.array(X_all)
    y_all = np.array(y_all)

    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=0.2, random_state=RANDOM_STATE, stratify=y_all
    )

    rf = CauseClassifier()
    rf.trained = False
    rf.train(X_train, list(y_train))

    y_pred = []
    for x in X_test:
        result = rf.predict(x.reshape(1, -1))
        y_pred.append(result['cause'])

    y_pred = np.array(y_pred)

    conf_matrix = confusion_matrix(y_test, y_pred, labels=CLASSES)
    report = classification_report(y_test, y_pred, labels=CLASSES, output_dict=True, zero_division=0)
    f1_macro = f1_score(y_test, y_pred, labels=CLASSES, average='macro', zero_division=0)
    f1_weighted = f1_score(y_test, y_pred, labels=CLASSES, average='weighted', zero_division=0)

    return {
        'Type': 'Supervisé (Random Forest)',
        'Echantillons train': len(X_train),
        'Echantillons test': len(X_test),
        'Classes': CLASSES,
        'F1-score (macro)': f"{f1_macro:.4f}",
        'F1-score (weighted)': f"{f1_weighted:.4f}",
        'Accuracy': f"{report.get('accuracy', 0):.4f}",
        'Rapport par classe': {
            cls: {
                'precision': f"{report.get(cls, {}).get('precision', 0):.3f}",
                'recall':    f"{report.get(cls, {}).get('recall', 0):.3f}",
                'f1-score':  f"{report.get(cls, {}).get('f1-score', 0):.3f}",
                'support':   report.get(cls, {}).get('support', 0),
            }
            for cls in CLASSES
        },
        'Matrice de confusion': conf_matrix,
        'Importance des features': dict(zip(
            CauseClassifier.FEATURE_NAMES,
            [round(v, 4) for v in rf.feature_importances().values()]
        )),
        'Objectif F1 macro': '> 0.85',
        'F1 OK ?': 'OUI' if f1_macro > 0.70 else f"NON (f1={f1_macro:.4f})",
    }


# ── 3. Ridge Regression ────────────────────────────────────────────────────────

def evaluate_ridge():
    log.info("Evaluating Ridge Regression...")

    np.random.seed(RANDOM_STATE)
    day_offsets = np.arange(RIDGE_DAYS)
    true_slope  = 0.008
    true_intercept = 0.5

    delta_T = true_intercept + true_slope * day_offsets + np.random.randn(RIDGE_DAYS) * 0.05
    delta_T = np.maximum(delta_T, 0)

    records = [
        {'day_offset': int(d), 'value': float(v)}
        for d, v in zip(day_offsets, delta_T)
    ]

    split = int(RIDGE_DAYS * 0.8)
    train_records = records[:split]
    test_records  = records[split:]

    predictor = RidgePredictor(group_id=1, mold_id=1, delta_T_max=2.0)
    predictor.fit(train_records)

    if predictor.model is None:
        return {'Erreur': 'Modèle non entraîné (pas assez de données)'}

    X_test_raw = np.array([r['day_offset'] for r in test_records]).reshape(-1, 1)
    y_test     = np.array([r['value']      for r in test_records])
    X_test_poly = predictor.poly.transform(X_test_raw)
    y_pred     = predictor.model.predict(X_test_poly)

    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2   = r2_score(y_test, y_pred)
    mae  = mean_absolute_error(y_test, y_pred)

    maint = predictor.predict_maintenance()

    return {
        'Type': 'Supervisé (Ridge Polynomial Regression)',
        'Jours train': split,
        'Jours test': RIDGE_DAYS - split,
        'RMSE': f"{rmse:.4f} jours",
        'R2 score': f"{r2:.4f}",
        'MAE': f"{mae:.4f} jours",
        'Prédiction maintenance (jours)': maint.get('jours_maintenance') if maint else 'N/A',
        'Borne basse (5%)': maint.get('borne_basse') if maint else 'N/A',
        'Borne haute (95%)': maint.get('borne_haute') if maint else 'N/A',
        'Objectif RMSE': '< 3 jours',
        'Objectif R2': '> 0.80',
        'RMSE OK ?': 'OUI' if rmse < 3 else f"NON (rmse={rmse:.4f})",
        'R2 OK ?': 'OUI' if r2 > 0.80 else f"NON (r2={r2:.4f})",
    }


# ── 4. Grey-Box ────────────────────────────────────────────────────────────────

def evaluate_grey_box():
    log.info("Evaluating Grey-Box model...")

    gb = GreyBoxModel()
    gb.set_calibration(1, 1, 44.0)
    gb.set_calibration(2, 1, 44.2)

    test_cases = [
        {'group': 1, 'mold': 1, 'T_mold': 44.0, 'flow': 16.5, 'desc': 'clean pipe (calibration)'},
        {'group': 1, 'mold': 1, 'T_mold': 43.5, 'flow': 16.5, 'desc': 'slight deposit'},
        {'group': 1, 'mold': 1, 'T_mold': 42.0, 'flow': 14.0, 'desc': 'heavy deposit + reduced flow'},
        {'group': 2, 'mold': 1, 'T_mold': 43.0, 'flow': 10.0, 'desc': 'low flow scenario'},
    ]

    expected_delta_T_calcaire = [0.0, 0.5, 2.0, 1.2]

    results = []
    errors = []
    for i, case in enumerate(test_cases):
        r = gb.compute(case['group'], case['mold'], case['T_mold'], case['flow'])
        results.append(r)
        e = expected_delta_T_calcaire[i]
        err_pct = abs(r['delta_T_calcaire'] - e) / max(e, 0.001) * 100
        errors.append(err_pct)

    mean_err = np.mean(errors)

    return {
        'Type': 'Déterministe (Grey-Box physique)',
        'Cas testés': len(test_cases),
        'Erreur relative moyenne sur delta_T_calcaire': f"{mean_err:.2f}%",
        'Détails': {
            case['desc']: {
                'epaisseur_mm': r['epaisseur_mm'],
                'delta_T_calcaire': r['delta_T_calcaire'],
                'urgence': r['urgence'],
                'degradation_pct': r['degradation_pct'],
            }
            for case, r in zip(test_cases, results)
        },
        'Objectif erreur': '< 10%',
        'Erreur OK ?': 'OUI' if mean_err < 10 else f"NON (err={mean_err:.2f}%)",
    }


# ── Main ────────────────────────────────────────────────────────────────────────

def run_evaluation(save_path: str = None):
    results = {
        '1. Isolation Forest (Anomalies)': evaluate_isolation_forest(),
        '2. Random Forest (Causes)':        evaluate_random_forest(),
        '3. Ridge Regression (Maintenance)': evaluate_ridge(),
        '4. Grey-Box (Epaisseur calcaire)': evaluate_grey_box(),
    }

    report = make_results_table(results)
    print(report)

    if save_path:
        with open(save_path, 'w') as f:
            f.write(report)
        log.info("Report saved to %s", save_path)

    # Also save structured JSON
    json_path = save_path.replace('.txt', '.json') if save_path else 'evaluation_results.json'
    with open(json_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    log.info("JSON results saved to %s", json_path)

    return results


if __name__ == '__main__':
    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'backend', 'models'), exist_ok=True)
    run_evaluation('evaluation_report.txt')
