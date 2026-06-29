# ml/train_models.py
# Trains Isolation Forest and Random Forest on real data from InfluxDB.
# Overwrites the synthetic models in backend/models/ with production models.
#
# Usage:
#   python ml/train_models.py                       # last 21 days
#   python ml/train_models.py --days 7              # last week
#   python ml/train_models.py --days 21 --step 60   # every 60s
#   python ml/train_models.py --eval                # train/test split + metrics
#
# Ridge regression is NOT here — it retrains daily in main.py automatically.

import sys
import os
import json
import logging
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

import config
import influxdb_manager as influx
from anomaly_detector import AnomalyDetector
from cause_classifier import CauseClassifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('train_models')


def parse_args():
    parser = argparse.ArgumentParser(description='Train ML models on real InfluxDB data')
    parser.add_argument('--days',  type=int, default=21, help='Days of history to load (default: 21)')
    parser.add_argument('--step',  type=int, default=30, help='Window step in seconds (default: 30)')
    parser.add_argument('--window', type=int, default=30, help='Window size in seconds (default: 30)')
    parser.add_argument('--eval', action='store_true', help='Split train/test and report metrics')
    parser.add_argument('--plots', action='store_true', help='Generate evaluation plots (t-SNE, ROC, histogram, etc.)')
    return parser.parse_args()


def load_temperatures(days: int):
    """Query temperature data from InfluxDB (only temperature field, no heater sensor).
    Returns: dict {(group_id, mold_id): [(timestamp, temperature), ...]}
    """
    if influx._query_api is None:
        influx.init_influxdb()
    if influx._query_api is None:
        log.error("Cannot connect to InfluxDB")
        return {}
    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "temperature")
      |> filter(fn: (r) => r._field == "temperature")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "group_id", "mold_id", "temperature"])
    '''
    tables = influx._query_api.query(flux, org=config.INFLUX_ORG)
    temp_data = defaultdict(list)
    for table in tables:
        for record in table.records:
            key = (int(record['group_id']), int(record['mold_id']))
            temp_data[key].append((record.get_time(), float(record['temperature'])))
    for key in temp_data:
        temp_data[key].sort(key=lambda x: x[0])
    log.info("Loaded temperatures: %d molds, ~%d total points",
             len(temp_data), sum(len(v) for v in temp_data.values()))
    return dict(temp_data)


def load_delta_T_calcaires(days: int):
    """Query delta_T_calcaire field from InfluxDB.
    Returns dict: {(group_id, mold_id): [(timestamp, delta_T_calcaire), ...]}
    """
    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "temperature")
      |> filter(fn: (r) => r._field == "delta_T_calcaire")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "group_id", "mold_id", "delta_T_calcaire"])
    '''
    tables = influx._query_api.query(flux, org=config.INFLUX_ORG)
    dT_data = defaultdict(list)
    for table in tables:
        for record in table.records:
            key = (int(record['group_id']), int(record['mold_id']))
            dT_data[key].append((record.get_time(), float(record['delta_T_calcaire'])))
    for key in dT_data:
        dT_data[key].sort(key=lambda x: x[0])
    return dict(dT_data)


def load_flows(days: int):
    """Query flow data from InfluxDB.
    Returns dict: {group_id: [(timestamp, flow_rate), ...]}
    """
    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{days}d)
      |> filter(fn: (r) => r._measurement == "flow")
      |> filter(fn: (r) => r._field == "flow_rate")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "group_id", "flow_rate"])
    '''
    tables = influx._query_api.query(flux, org=config.INFLUX_ORG)
    flow_data = defaultdict(list)
    for table in tables:
        for record in table.records:
            gid = int(record['group_id'])
            flow_data[gid].append((record.get_time(), float(record['flow_rate'])))
    for gid in flow_data:
        flow_data[gid].sort(key=lambda x: x[0])
    return dict(flow_data)


def build_windows(temp_data, dT_data, flow_data, window_size, step):
    """Slide a window across the aligned data, yielding one feature vector per step.
    Steps are in seconds. Each window covers `window_size` seconds.
    """
    all_mold_keys = sorted(temp_data.keys())
    all_group_ids = sorted(flow_data.keys())

    if not all_mold_keys or not all_group_ids:
        log.error("No data found")
        return

    # Find common time range across all sensors
    latest_start = max(
        max(t[0] for t in temp_data[key][:1]) if temp_data[key] else datetime.min
        for key in all_mold_keys
    )
    earliest_end = min(
        min(t[0] for t in temp_data[key][-1:]) if temp_data[key] else datetime.max
        for key in all_mold_keys
    )

    log.info("Common time range: %s → %s", latest_start, earliest_end)
    if latest_start >= earliest_end:
        log.error("No overlapping time range across all molds")
        return

    # Build lookup dicts: timestamp → value for fast access
    def to_lookup(series):
        lookup = defaultdict(dict)
        for key, pairs in series.items():
            for ts, val in pairs:
                lookup[key][ts] = val
        return lookup

    temp_lookup = to_lookup(temp_data)
    flow_lookup = to_lookup(flow_data)
    dT_lookup = to_lookup(dT_data)

    # Get sorted list of all unique timestamps within the common range
    all_timestamps = set()
    for key in all_mold_keys:
        for ts, _ in temp_data[key]:
            if latest_start <= ts <= earliest_end:
                all_timestamps.add(ts)
    all_timestamps = sorted(all_timestamps)

    log.info("Total timestamps in common range: %d", len(all_timestamps))
    if len(all_timestamps) < window_size:
        log.error("Not enough data points (%d) for window size (%d)", len(all_timestamps), window_size)
        return

    # Convert timestamps to numpy array for fast indexing
    ts_array = np.array(all_timestamps)

    # Pre-build a mask: for each timestamp, which keys have data?
    iso = AnomalyDetector()
    rf_features_list = []
    if_features_list = []
    labels_list = []
    flow_rate_samples = []
    flow_drop_samples = []
    normal_temps_list = []

    n_molds = len(all_mold_keys)

    for i in range(window_size, len(all_timestamps), step):
        window_start = i - window_size
        window_ts = ts_array[window_start:i]

        # Reconstruct temp_history dict (latest 30 values per mold)
        temp_history = {}
        for key in all_mold_keys:
            vals = []
            for ts in window_ts:
                t = temp_lookup[key].get(ts)
                if t is not None:
                    vals.append(t)
                if len(vals) >= 30:
                    break
            if vals:
                temp_history[key] = vals

        # Reconstruct flow_history dict
        flow_history = {}
        for gid in all_group_ids:
            vals = []
            for ts in window_ts:
                f = flow_lookup[gid].get(ts)
                if f is not None:
                    vals.append(f)
                if len(vals) >= 30:
                    break
            if vals:
                flow_history[gid] = vals

        if not temp_history:
            continue
        if not flow_history:
            for gid in all_group_ids:
                flow_history[gid] = [config.FLOW_DEFAULT_LPM]

        # Get current delta_T_calcaires (last value in window)
        current_dT = {}
        for key in all_mold_keys:
            vals = dT_lookup.get(key, {})
            for ts in reversed(window_ts):
                if ts in vals:
                    current_dT[key] = vals[ts]
                    break

        # Extract 8D features
        features_8d = iso.extract_features(temp_history, flow_history, current_dT)
        if features_8d is None:
            continue

        # Compute missing RF features
        f = features_8d[0]
        flow_rate = f[4]

        # flow_drop_flag
        flow_drop = float(flow_rate < 0.5 * config.FLOW_DEFAULT_LPM)

        # DEBUG: sample flow_rate periodically
        if len(flow_rate_samples) < 50:
            flow_rate_samples.append(flow_rate)
            flow_drop_samples.append(flow_drop)

        # drift_R_squared: per-mold R² then averaged (concatenating molds with
        # different baselines artificially depresses R², killing CALCAIRE_TUYAUX)
        r2_list = []
        for key in all_mold_keys:
            vals = temp_history.get(key, [])
            if len(vals) >= 10:
                arr = np.array(vals)
                x_arr = np.arange(len(arr))
                coeffs = np.polyfit(x_arr, arr, 1)
                y_pred = np.polyval(coeffs, x_arr)
                ss_res = np.sum((arr - y_pred) ** 2)
                ss_tot = np.sum((arr - np.mean(arr)) ** 2)
                r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.9
                r2_list.append(r2)
        drift_R_squared = float(np.mean(r2_list)) if r2_list else 0.9

        # delta_T_calcaire_slope = mean / 7 (approximation)
        dT_vals = list(current_dT.values())
        delta_T_calcaire_slope = float(np.mean(dT_vals) / 7.0) if dT_vals else 0.0

        # Build 10D vector
        rf_feat = np.array([[
            f[0],                     # slope_T_mold
            f[1],                     # variance_T_mold
            f[2],                     # affected_molds_ratio
            f[3],                     # sudden_drop_flag
            f[4],                     # flow_rate
            flow_drop,                # flow_drop_flag
            f[5],                     # flow_variance
            delta_T_calcaire_slope,    # delta_T_calcaire_slope
            drift_R_squared,           # drift_R_squared
            f[7],                     # autocorr_lag1
        ]])

        # Auto-label (no heater sensor in real system — detect via flow + temp patterns)
        label = CauseClassifier.auto_label(
            affected_ratio=float(f[2]),
            sudden_drop=bool(f[3]),
            flow_drop=bool(flow_drop),
            flow_rate=float(f[4]),
            variance=float(f[1]),
            R_squared=drift_R_squared,
            delta_T_calcaire_slope=delta_T_calcaire_slope,
            nominal_flow=config.FLOW_DEFAULT_LPM,
        )

        # Check if all temperatures across all molds are within normal range [42, 48]°C
        all_temps_in_window = []
        for key_vals in temp_history.values():
            all_temps_in_window.extend(key_vals)
        is_normal = all(42.0 <= t <= 48.0 for t in all_temps_in_window) if all_temps_in_window else False

        if_features_list.append(features_8d)
        rf_features_list.append(rf_feat)
        labels_list.append(label)
        normal_temps_list.append(is_normal)

        if (i - window_size) % 10000 == 0 and i > window_size:
            log.info("  Processed %d windows...", len(if_features_list))

    log.info("Total windows extracted: %d", len(if_features_list))
    if flow_rate_samples:
        log.info("DEBUG flow_rate sample (first %d): min=%.2f max=%.2f flow_drop_true=%d/%d",
                 len(flow_rate_samples), min(flow_rate_samples), max(flow_rate_samples),
                 sum(flow_drop_samples), len(flow_drop_samples))

    n_normal = sum(normal_temps_list)
    log.info("Windows with all temps in [42, 48]°C: %d / %d (%.1f%%)",
             n_normal, len(normal_temps_list), 100.0 * n_normal / len(normal_temps_list) if normal_temps_list else 0)
    return if_features_list, rf_features_list, labels_list, normal_temps_list


def train_isolation_forest(if_features, normal_mask=None):
    """Train Isolation Forest on 8D feature vectors — only on normal windows (all temps in [42,48]°C).
    This ensures the IF learns what 'normal' looks like and flags anything deviating as anomalous.
    """
    if normal_mask is not None:
        X_normal = np.vstack([if_features[i] for i in range(len(if_features)) if normal_mask[i]])
        excluded = len(if_features) - len(X_normal)
        log.info("Isolation Forest: using %d normal windows (excluded %d non-normal)",
                 len(X_normal), excluded)
    else:
        X_normal = np.vstack(if_features)
        log.info("Isolation Forest: no mask provided, using all %d windows", len(X_normal))
    iso = AnomalyDetector()
    iso.trained = False
    iso.train(X_normal)
    log.info("Isolation Forest trained and saved → models/isolation_forest.pkl")


def train_random_forest(rf_features, labels):
    """Train Random Forest on 10D feature vectors with auto-labels.
    All 7 AMDEC classes are trained (N1 + N2). N1 physical rules run FIRST
    at inference, then RF catches cases that fall below N1 thresholds.
    Only CAUSE_INDETERMINEE is excluded: it is not a physical class but a
    confidence threshold fallback — including it would pollute RF boundaries.
    """
    EXCLUDE = {'CAUSE_INDETERMINEE'}
    keep_mask = [l not in EXCLUDE for l in labels]
    X_train = np.vstack([rf_features[i] for i in range(len(labels)) if keep_mask[i]])
    labels_train = [labels[i] for i in range(len(labels)) if keep_mask[i]]

    removed = len(labels) - len(labels_train)
    if removed:
        log.info("Excluded %d CAUSE_INDETERMINEE samples", removed)

    log.info("Training Random Forest on %d samples (%d classes)...",
             len(X_train), len(set(labels_train)))
    rf = CauseClassifier()
    rf.trained = False
    rf.train(X_train, labels_train)
    log.info("Random Forest trained and saved → models/random_forest.pkl")

    # Class distribution
    from collections import Counter
    dist = Counter(labels_train)
    log.info("RF class distribution (excluding CAUSE_INDETERMINEE):")
    for cls, count in sorted(dist.items(), key=lambda x: -x[1]):
        log.info("  %-30s %6d (%.1f%%)", cls, count, count / len(labels) * 100)


def evaluate_models(rf_features, labels):
    """Split train/test and report metrics for Random Forest (all 7 AMDEC classes).
    Only CAUSE_INDETERMINEE excluded: it is not a physical class but a confidence
    threshold fallback — evaluating on it would pollute metrics."""
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, confusion_matrix, f1_score

    log.info("Evaluating Random Forest (80/20 split)...")

    EXCLUDE = {'CAUSE_INDETERMINEE'}
    keep_mask = [l not in EXCLUDE for l in labels]
    X_all = np.vstack([rf_features[i] for i in range(len(labels)) if keep_mask[i]])
    y_all = np.array([labels[i] for i in range(len(labels)) if keep_mask[i]])

    removed = len(labels) - len(y_all)
    if removed:
        log.info("Excluded %d CAUSE_INDETERMINEE samples from evaluation", removed)

    # Temporal split (no shuffle — time series!)
    split = int(len(X_all) * 0.8)
    X_train, X_test = X_all[:split], X_all[split:]
    y_train, y_test = y_all[:split], y_all[split:]

    rf = CauseClassifier()
    rf.trained = False
    rf.train(X_train, list(y_train))

    y_pred = []
    for x in X_test:
        result = rf.predict(x.reshape(1, -1))
        y_pred.append(result['cause'])

    class_labels = sorted(set(y_test))
    f1_macro = f1_score(y_test, y_pred, labels=class_labels, average='macro', zero_division=0)

    report = classification_report(y_test, y_pred, labels=class_labels, zero_division=0)
    print("\nClassification Report (Random Forest — all AMDEC classes):")
    print(report)
    print(f"F1 macro: {f1_macro:.4f}")

    # Feature importances
    print("\nFeature importances:")
    for name, imp in sorted(rf.feature_importances().items(), key=lambda x: -x[1]):
        print(f"  {name:30s} {imp:.4f}")

    return {
        'f1_macro': round(f1_macro, 4),
        'classification_report': report,
        'feature_importances': rf.feature_importances(),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'split_ratio': '80/20 temporal',
        'n1_excluded': removed,
    }


def save_report(results, path=None):
    if path is None:
        path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'models', 'training_report.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    """Save training report as JSON."""
    serializable = {}
    for k, v in results.items():
        if isinstance(v, (np.floating,)):
            serializable[k] = float(v)
        elif isinstance(v, (np.integer,)):
            serializable[k] = int(v)
        elif isinstance(v, dict):
            serializable[k] = {sk: round(float(sv), 4) if isinstance(sv, (np.floating,)) else sv
                               for sk, sv in v.items()}
        else:
            serializable[k] = v
    serializable['date'] = datetime.now().isoformat()
    with open(path, 'w') as f:
        json.dump(serializable, f, indent=2)
    log.info("Report saved to %s", path)


def main():
    args = parse_args()
    log.info("=" * 60)
    log.info("TRAINING ML MODELS")
    log.info("  Days:   %d", args.days)
    log.info("  Window: %ds", args.window)
    log.info("  Step:   %ds  %s", args.step,
             "(overlapping)" if args.step < args.window else "(non-overlapping)")
    log.info("  Eval:   %s", args.eval)
    log.info("=" * 60)

    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'backend', 'models'), exist_ok=True)

    # 1. Load data
    log.info("Loading data from InfluxDB...")
    temp_data = load_temperatures(args.days)
    dT_data = load_delta_T_calcaires(args.days)
    flow_data = load_flows(args.days)

    if not temp_data or not flow_data:
        log.error("No data available — check InfluxDB connection and bucket '%s'", config.INFLUX_BUCKET)
        sys.exit(1)

    # 2. Build windows
    log.info("Building sliding windows (size=%ds, step=%ds)...", args.window, args.step)

    # DEBUG: flow data stats
    total_flow_pts = sum(len(v) for v in flow_data.values())
    all_flow_vals = [v for pts in flow_data.values() for _, v in pts]
    log.info("DEBUG flow_data: %d groups, %d total points, min=%.2f max=%.2f mean=%.2f",
             len(flow_data), total_flow_pts,
             min(all_flow_vals) if all_flow_vals else 0,
             max(all_flow_vals) if all_flow_vals else 0,
             float(np.mean(all_flow_vals)) if all_flow_vals else 0)

    result = build_windows(temp_data, dT_data, flow_data, args.window, args.step)
    if result is None:
        sys.exit(1)
    if_features, rf_features, labels, normal_temps_list = result

    if len(if_features) < 100:
        log.error("Too few windows (%d) — need at least 100", len(if_features))
        sys.exit(1)

    # 3. Train Isolation Forest (normal samples only — all temps in [42, 48]°C)
    train_isolation_forest(if_features, normal_temps_list)

    # 4. Train Random Forest
    train_random_forest(rf_features, labels)

    # 5. Evaluate (optional)
    results = {
        'windows_total': len(if_features),
        'days_loaded': args.days,
        'window_size_s': args.window,
        'step_s': args.step,
        'train_isolation_forest': True,
        'train_random_forest': True,
    }
    if args.eval:
        eval_results = evaluate_models(rf_features, labels)
        results.update(eval_results)

    save_report(results)

    # 6. Generate plots (optional)
    if args.plots:
        try:
            from plots_evaluation import generate_all_plots
            from anomaly_detector import AnomalyDetector
            from cause_classifier import CauseClassifier

            X_if = np.vstack(if_features)
            X_rf = np.vstack(rf_features)

            iso = AnomalyDetector()
            rfc = CauseClassifier()

            generate_all_plots(
                iso_model=iso,
                rf_model=rfc,
                features_if=X_if,
                features_rf=X_rf,
                labels_rf=labels,
                pseudo_labels_if=np.array([1 if l != 'NORMAL' else 0 for l in labels]),
            )
            log.info("Plots generated in models/plots/")
        except Exception as plot_exc:
            log.warning("Could not generate plots: %s", plot_exc)

    log.info("Done — models saved to backend/models/")
    log.info("Restart the backend to load the new models.")


if __name__ == '__main__':
    main()
