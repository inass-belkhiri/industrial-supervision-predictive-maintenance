import logging
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

import config

log = logging.getLogger(__name__)

PLOTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'plots')

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except ImportError:
    log.warning("matplotlib not available — plots will not be generated")
    plt = None


def _ensure_plots_dir():
    os.makedirs(PLOTS_DIR, exist_ok=True)
    return PLOTS_DIR


def plot_rf_tsne(rf_model, features: np.ndarray, labels: list, suffix: str = ''):
    if plt is None:
        return
    try:
        from sklearn.manifold import TSNE
    except ImportError:
        log.warning("sklearn.manifold not available — skipping t-SNE plot")
        return

    if features.shape[0] < 5 or len(set(labels)) < 2:
        log.info("Not enough data for t-SNE plot")
        return

    _ensure_plots_dir()

    tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, features.shape[0] - 1))
    X_2d = tsne.fit_transform(features)

    unique_labels = sorted(set(labels))
    cmap = plt.cm.tab10
    fig, ax = plt.subplots(figsize=(10, 8))

    for i, label in enumerate(unique_labels):
        mask = np.array(labels) == label
        ax.scatter(X_2d[mask, 0], X_2d[mask, 1],
                   c=[cmap(i % 10)], label=label, alpha=0.7, edgecolors='k', linewidth=0.5, s=60)

    ax.set_title('t-SNE Clusters — Random Forest (causes)', fontsize=14, fontweight='bold')
    ax.set_xlabel('t-SNE dim 1')
    ax.set_ylabel('t-SNE dim 2')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)

    path = os.path.join(PLOTS_DIR, f'rf_tsne_clusters{suffix}.png')
    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    log.info("t-SNE plot saved → %s", path)


def plot_if_roc(iso_model, features: np.ndarray, pseudo_labels: np.ndarray, suffix: str = ''):
    if plt is None:
        return
    from sklearn.metrics import roc_curve, auc

    if not iso_model.trained or features.shape[0] < 2:
        log.info("Not enough data for ROC curve")
        return

    _ensure_plots_dir()

    X_scaled = iso_model.scaler.transform(features)
    scores = iso_model.model.score_samples(X_scaled)
    # score_samples: higher = more normal. Negate so higher = more anomalous.
    scores_neg = -scores

    fpr, tpr, _ = roc_curve(pseudo_labels, scores_neg)
    roc_auc = auc(fpr, tpr)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
    ax.plot([0, 1], [0, 1], color='navy', lw=1, linestyle='--', label='Random classifier')
    ax.fill_between(fpr, tpr, alpha=0.1, color='darkorange')

    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=12)
    ax.set_ylabel('True Positive Rate (Sensitivity)', fontsize=12)
    ax.set_title('ROC Curve — Isolation Forest', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    ax.grid(True, alpha=0.3)

    path = os.path.join(PLOTS_DIR, f'if_roc_curve{suffix}.png')
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    log.info("ROC curve saved → %s (AUC=%.3f)", path, roc_auc)

    return roc_auc


def plot_ridge_regression(predictor, suffix: str = ''):
    if plt is None:
        return
    if predictor.X_data is None or predictor.y_data is None or predictor.model is None:
        log.info("Ridge predictor not trained — skipping regression plot")
        return

    _ensure_plots_dir()

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.scatter(predictor.X_data, predictor.y_data, color='steelblue', s=40,
               label='Daily delta_T_calcaire (real)', zorder=5)

    X_smooth = np.linspace(int(predictor.X_data.min()), int(predictor.X_data.max()) + 60, 200).reshape(-1, 1)
    X_smooth_poly = predictor.poly.transform(X_smooth)
    y_smooth = predictor.model.predict(X_smooth_poly)

    ax.plot(X_smooth, y_smooth, color='crimson', lw=2, label='Ridge polynomial fit (deg 2)', zorder=4)

    ax.axhline(y=predictor.delta_T_max, color='green', linestyle='--', lw=1.5,
               label=f'Critical threshold ({predictor.delta_T_max:.2f}°C)')

    ax.axvline(x=int(predictor.X_data[-1]), color='gray', linestyle=':', alpha=0.5,
               label=f'Today (day {int(predictor.X_data[-1])})')

    ax.set_xlabel('Day offset', fontsize=12)
    ax.set_ylabel('delta_T_calcaire (°C)', fontsize=12)
    ax.set_title(f'Ridge Regression — Mold ({predictor.group_id},{predictor.mold_id})',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    path = os.path.join(PLOTS_DIR, f'ridge_regression_{predictor.group_id}_{predictor.mold_id}{suffix}.png')
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    log.info("Ridge regression plot saved → %s", path)


def plot_all_ridge(maintenance_list: list, suffix: str = ''):
    if plt is None:
        return
    for entry in maintenance_list:
        if 'predictor' in entry:
            plot_ridge_regression(entry['predictor'], suffix=suffix)


def plot_if_histogram(iso_model, features: np.ndarray, suffix: str = ''):
    if plt is None:
        return
    if not iso_model.trained or features.shape[0] < 5:
        log.info("Not enough data for histogram")
        return

    _ensure_plots_dir()

    X_scaled = iso_model.scaler.transform(features)
    scores = iso_model.model.score_samples(X_scaled)

    fig, ax = plt.subplots(figsize=(10, 6))

    n, bins, patches = ax.hist(scores, bins=40, color='steelblue', edgecolor='white',
                               alpha=0.75, density=True, label='Anomaly scores')

    threshold = np.percentile(scores, 5)
    ax.axvline(x=threshold, color='red', linestyle='--', lw=2,
               label=f'Contamination threshold (p5 = {threshold:.3f})')

    ax.axvline(x=0, color='gray', linestyle=':', alpha=0.5, label='Decision boundary')

    ax.set_xlabel('Anomaly score (higher = more normal)', fontsize=12)
    ax.set_ylabel('Density', fontsize=12)
    ax.set_title('Isolation Forest — Anomaly Score Distribution', fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

    path = os.path.join(PLOTS_DIR, f'if_score_histogram{suffix}.png')
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    log.info("IF histogram saved → %s", path)


def plot_learning_curve(sufficiency_results: dict, suffix: str = ''):
    if plt is None:
        return
    if not sufficiency_results:
        log.info("No sufficiency results to plot")
        return

    _ensure_plots_dir()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    rf_scores = sufficiency_results.get('rf_f1_scores', {})
    ridge_scores = sufficiency_results.get('ridge_r2_scores', {})

    if rf_scores:
        ax = axes[0]
        ks = sorted(rf_scores.keys())
        vals = [rf_scores[k] for k in ks]
        ax.plot(ks, vals, 'o-', color='darkorange', lw=2, markersize=8)
        ax.axhline(y=0.85, color='green', linestyle='--', alpha=0.7, label='Objective (F1=0.85)')
        ax.fill_between(ks, vals, alpha=0.1, color='darkorange')
        ax.set_xlabel('Days of training data')
        ax.set_ylabel('F1-macro')
        ax.set_title('Learning Curve — Random Forest', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

    if ridge_scores:
        ax = axes[1]
        ks = sorted(ridge_scores.keys())
        vals = [ridge_scores[k] for k in ks]
        ax.plot(ks, vals, 'o-', color='steelblue', lw=2, markersize=8)
        ax.axhline(y=0.80, color='green', linestyle='--', alpha=0.7, label='Objective (R²=0.80)')
        ax.fill_between(ks, vals, alpha=0.1, color='steelblue')
        ax.set_xlabel('Days of training data')
        ax.set_ylabel('R²')
        ax.set_title('Learning Curve — Ridge Regression', fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

    path = os.path.join(PLOTS_DIR, f'learning_curve{suffix}.png')
    plt.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    log.info("Learning curve saved → %s", path)


def generate_all_plots(iso_model=None, rf_model=None,
                       features_if=None, features_rf=None,
                       labels_rf=None, pseudo_labels_if=None,
                       maintenance_list=None, sufficiency_results=None,
                       suffix: str = ''):
    if plt is None:
        log.warning("Cannot generate plots — matplotlib not installed")
        return

    _ensure_plots_dir()

    if iso_model and features_if is not None:
        plot_if_histogram(iso_model, features_if, suffix=suffix)
        if pseudo_labels_if is not None:
            plot_if_roc(iso_model, features_if, pseudo_labels_if, suffix=suffix)

    if rf_model and features_rf is not None and labels_rf is not None:
        plot_rf_tsne(rf_model, features_rf, labels_rf, suffix=suffix)

    if maintenance_list:
        plot_all_ridge(maintenance_list, suffix=suffix)

    if sufficiency_results:
        plot_learning_curve(sufficiency_results, suffix=suffix)

    log.info("All plots generated in %s", PLOTS_DIR)
