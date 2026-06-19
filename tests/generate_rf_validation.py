"""
Jeu de validation manuel pour le Random Forest.
Construit des vecteurs features 10D avec des causes connues
indépendamment des règles d'auto-labeling.

Usage :
    python tests/generate_rf_validation.py          # génère le dataset
    python tests/generate_rf_validation.py --eval    # évalue le RF dessus
"""

import sys
import os
import json
import random
import argparse
from typing import List, Dict, Tuple

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

import numpy as np

from cause_classifier import CauseClassifier, CLASSES

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'rf_validation_dataset.json')

random.seed(42)
np.random.seed(42)


def _jitter(base, amplitude):
    return base + random.uniform(-amplitude, amplitude)


# ── Signatures physiques par cause ────────────────────────────────────────────
# Chaque signature produit 4-5 variantes avec du bruit.
# L'ordre des 10 features RF :
#   slope_T_mold, variance_T_mold, affected_molds_ratio, sudden_drop_flag,
#   flow_rate, flow_drop_flag, flow_variance, delta_T_calcaire_slope,
#   drift_R_squared, autocorr_lag1

SIGNATURES = {
    'HEATER_RESISTANCE_HS': {
        'base': [-0.04, 0.05, 0.85, 0.0, 16.5, 0.0, 0.02, 0.01, 0.88, 0.85],
        'amplitude': [0.02, 0.03, 0.10, 0.0, 0.5, 0.0, 0.01, 0.01, 0.05, 0.05],
        'n': 4,
    },
    'HEATER_POMPE_HS': {
        'base': [-0.08, 0.15, 0.95, 1.0, 3.5, 1.0, 0.03, 0.005, 0.60, 0.55],
        'amplitude': [0.03, 0.05, 0.05, 0.0, 1.5, 0.0, 0.02, 0.005, 0.10, 0.10],
        'n': 4,
    },
    'NIVEAU_BAS_VANNE_PANNE': {
        'base': [-0.02, 0.08, 0.70, 0.0, 4.0, 1.0, 0.02, 0.005, 0.55, 0.60],
        'amplitude': [0.01, 0.03, 0.08, 0.0, 1.0, 0.0, 0.01, 0.005, 0.10, 0.10],
        'n': 4,
    },
    'CALCAIRE_TUYAUX': {
        'base': [-0.005, 0.02, 0.30, 0.0, 14.0, 0.0, 0.01, 0.05, 0.90, 0.90],
        'amplitude': [0.005, 0.01, 0.10, 0.0, 1.0, 0.0, 0.01, 0.02, 0.05, 0.05],
        'n': 4,
    },
    'BULLES_AIR': {
        'base': [0.0, 0.35, 0.20, 0.0, 15.0, 0.0, 0.30, 0.01, 0.20, 0.15],
        'amplitude': [0.005, 0.10, 0.10, 0.0, 1.0, 0.0, 0.10, 0.01, 0.10, 0.10],
        'n': 4,
    },
    'FUITE_CIRCUIT': {
        'base': [-0.01, 0.04, 0.30, 0.0, 11.0, 1.0, 0.08, 0.02, 0.65, 0.60],
        'amplitude': [0.01, 0.02, 0.10, 0.0, 1.5, 0.0, 0.04, 0.01, 0.10, 0.10],
        'n': 4,
    },
    'ISOLATION_DEGRADEE': {
        'base': [-0.008, 0.02, 0.20, 0.0, 16.5, 0.0, 0.01, 0.005, 0.80, 0.80],
        'amplitude': [0.005, 0.01, 0.10, 0.0, 0.5, 0.0, 0.01, 0.005, 0.10, 0.10],
        'n': 4,
    },
}

# ── Cas ambigus (zones grises où les règles ne décident pas) ──────────────────
# Ces cas ne devraient PAS être attrapés par les règles physiques
# et testent la vraie valeur ajoutée du RF.

AMBIGUOUS_CASES = [
    # affected_ratio modéré, flow légèrement bas, variance modérée
    {'features': [-0.01, 0.12, 0.45, 0.0, 10.0, 0.0, 0.08, 0.02, 0.50, 0.45],
     'cause': 'NIVEAU_BAS_VANNE_PANNE'},
    # pente négative faible, affected_ratio bas, R² élevé → isolation vs calcaire
    {'features': [-0.008, 0.03, 0.25, 0.0, 16.0, 0.0, 0.02, 0.03, 0.78, 0.75],
     'cause': 'ISOLATION_DEGRADEE'},
    # affected_ratio modéré, flow nominal, variance élevée → bulles vs normal
    {'features': [0.0, 0.25, 0.35, 0.0, 15.5, 0.0, 0.20, 0.01, 0.30, 0.25],
     'cause': 'BULLES_AIR'},
    # Très lent decline, affected_ratio modéré, R² élevé → calcaire
    {'features': [-0.003, 0.02, 0.35, 0.0, 13.5, 0.0, 0.02, 0.04, 0.87, 0.85],
     'cause': 'CALCAIRE_TUYAUX'},
    # affected_ratio élevé mais pas de sudden_drop, flow bas → niveau_bas vs pompe
    {'features': [-0.02, 0.06, 0.75, 0.0, 5.0, 1.0, 0.03, 0.01, 0.50, 0.55],
     'cause': 'NIVEAU_BAS_VANNE_PANNE'},
    # sudden drop + flow presque nominal → heater failure vs pump
    {'features': [-0.06, 0.12, 0.85, 1.0, 12.0, 0.0, 0.10, 0.01, 0.60, 0.50],
     'cause': 'HEATER_RESISTANCE_HS'},
    # flow drop + affected_ratio modéré mais pas sudden → fuite
    {'features': [-0.015, 0.05, 0.40, 0.0, 9.0, 1.0, 0.12, 0.015, 0.55, 0.50],
     'cause': 'FUITE_CIRCUIT'},
]


def generate_dataset() -> List[Dict]:
    dataset = []

    for cause, sig in SIGNATURES.items():
        for _ in range(sig['n']):
            features = [
                _jitter(sig['base'][i], sig['amplitude'][i])
                for i in range(10)
            ]
            features[3] = round(features[3])  # sudden_drop_flag binaire
            features[5] = round(features[5])  # flow_drop_flag binaire
            features = [round(f, 4) for f in features]
            dataset.append({'features': features, 'cause': cause})

    for case in AMBIGUOUS_CASES:
        dataset.append(case)

    return dataset


def evaluate_rf(dataset: List[Dict]) -> Dict:
    rf = CauseClassifier()
    if not rf.trained:
        return {'error': 'RF non entraîné. Entraîne d\'abord les modèles.'}

    y_true = []
    y_pred = []

    for item in dataset:
        X = np.array([item['features']])
        result = rf.predict(X)
        y_true.append(item['cause'])
        y_pred.append(result['cause'])

    correct = sum(1 for a, b in zip(y_true, y_pred) if a == b)
    total = len(dataset)

    from sklearn.metrics import classification_report, confusion_matrix
    report = classification_report(y_true, y_pred, labels=CLASSES, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=CLASSES)

    return {
        'accuracy': correct / total,
        'correct': correct,
        'total': total,
        'classification_report': report,
        'confusion_matrix': cm.tolist(),
        'classes': CLASSES,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--eval', action='store_true', help='Évalue le RF sur le dataset')
    args = parser.parse_args()

    dataset = generate_dataset()
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(dataset, f, indent=2)
    print(f"Dataset généré : {len(dataset)} cas → {OUTPUT_PATH}")
    for cause in CLASSES:
        count = sum(1 for d in dataset if d['cause'] == cause)
        print(f"  {cause:<30s} {count} cas")

    if args.eval:
        print("\n" + "=" * 60)
        print("Évaluation du Random Forest")
        print("=" * 60)
        result = evaluate_rf(dataset)
        if 'error' in result:
            print(f"  ERREUR : {result['error']}")
        else:
            print(f"  Accuracy : {result['accuracy']:.1%} ({result['correct']}/{result['total']})")
            print(f"\n  Rapport de classification :\n{result['classification_report']}")

    return dataset


if __name__ == '__main__':
    main()
