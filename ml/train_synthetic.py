import sys, os, json, logging, random, math
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

import config
from anomaly_detector import AnomalyDetector
from cause_classifier import CauseClassifier
from grey_box import GreyBoxModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('train_synthetic')

N_DAYS = 60
SAMPLE_MINUTES = list(range(0, 1440, 5))  # every 5 min

GROUP_TEMP_OFFSET = {1: +0.3, 2: 0.0, 3: -0.3, 4: -0.5}
MOLD_POS_OFFSET = {1: -0.1, 2: +0.3}
ENCRASSEMENT_DRIFT = {1: -0.015, 2: -0.025, 3: -0.030, 4: -0.020}
DAILY_CYCLE_AMP = 0.4
DAILY_CYCLE_PHASE = 0.21
GROUP_FLOW_BASELINE = {1: 16.0, 2: 16.5, 3: 17.0, 4: 16.2}

def daily_cycle(minute):
    return DAILY_CYCLE_AMP * math.sin(2 * math.pi * (minute / 1440.0 - DAILY_CYCLE_PHASE))

def gen_temps(day, gid, mid):
    group_off = GROUP_TEMP_OFFSET.get(gid, 0.0)
    mold_off = MOLD_POS_OFFSET.get(mid, 0.0)
    drift = 0.0
    if day > 20:
        max_drift = ENCRASSEMENT_DRIFT.get(gid, -0.02) * (N_DAYS - 20)
        drift = max_drift * (1 - math.exp(-0.05 * (day - 20)))

    records = []
    prev = None
    for minute in SAMPLE_MINUTES:
        cycle = daily_cycle(minute)
        target = config.T_HEATER + group_off + mold_off + cycle + drift
        if prev is None:
            prev = target + random.gauss(0, 0.08)
        else:
            prev = 0.97 * prev + 0.03 * target + random.gauss(0, 0.08)
        records.append({'minute': minute, 'temp': round(max(25, prev), 1)})
    return records

def gen_flow(day, gid):
    base = GROUP_FLOW_BASELINE.get(gid, config.FLOW_DEFAULT_LPM)
    val = base + random.gauss(0, 0.5)
    if gid == 3 and day > 20:
        val *= 0.6
    return round(max(0, val), 2)

def generate_all_data():
    log.info("Generating %d days of synthetic data in memory...", N_DAYS)
    grey = GreyBoxModel()

    temp_data = defaultdict(list)
    dT_data = defaultdict(list)
    flow_data = defaultdict(list)
    calibration_done = set()

    for day in range(N_DAYS):
        day_start = datetime.now() - timedelta(days=N_DAYS - day)

        for (gid, mid), _ in config.SENSOR_MAP.items():
            temps = gen_temps(day, gid, mid)
            g_flow = gen_flow(day, gid)
            for rec in temps:
                ts = day_start + timedelta(minutes=rec['minute']) + timedelta(microseconds=mid)
                t = rec['temp']

                if (gid, mid) not in calibration_done:
                    grey.set_calibration(gid, mid, t)
                    calibration_done.add((gid, mid))

                gb = grey.compute(gid, mid, t, g_flow)
                temp_data[(gid, mid)].append((ts, t))
                dT_data[(gid, mid)].append((ts, gb['delta_T_calcaire']))

        for gid in config.FLOW_SENSOR_PINS:
            for minute in SAMPLE_MINUTES:
                ts = day_start + timedelta(minutes=minute)
                flow_data[gid].append((ts, gen_flow(day, gid)))

    for key in temp_data:
        temp_data[key].sort(key=lambda x: x[0])
    for key in dT_data:
        dT_data[key].sort(key=lambda x: x[0])
    for gid in flow_data:
        flow_data[gid].sort(key=lambda x: x[0])

    log.info("Generated: %d temp series, %d flow series",
             len(temp_data), len(flow_data))
    return dict(temp_data), dict(dT_data), dict(flow_data)

def build_windows(temp_data, dT_data, flow_data, window_size=30, step=30):
    all_mold_keys = sorted(temp_data.keys())
    all_group_ids = sorted(flow_data.keys())

    if not all_mold_keys or not all_group_ids:
        log.error("No data")
        return None

    latest_start = max(max(t[0] for t in temp_data[key][:1]) for key in all_mold_keys)
    earliest_end = min(min(t[0] for t in temp_data[key][-1:]) for key in all_mold_keys)
    log.info("Time range: %s → %s", latest_start, earliest_end)

    if latest_start >= earliest_end:
        log.error("No overlap")
        return None

    def to_lookup(series):
        lookup = defaultdict(dict)
        for key, pairs in series.items():
            for ts, val in pairs:
                lookup[key][ts] = val
        return lookup

    temp_lookup = to_lookup(temp_data)
    flow_lookup = to_lookup(flow_data)
    dT_lookup = to_lookup(dT_data)

    all_timestamps = sorted({ts for key in all_mold_keys for ts, _ in temp_data[key]
                            if latest_start <= ts <= earliest_end})
    log.info("Timestamps in range: %d", len(all_timestamps))

    if len(all_timestamps) < window_size:
        log.error("Not enough points (%d) for window (%d)", len(all_timestamps), window_size)
        return None

    ts_array = np.array(all_timestamps)
    iso = AnomalyDetector()
    if_features = []
    rf_features = []
    labels = []

    for i in range(window_size, len(all_timestamps), step):
        ws = i - window_size
        window_ts = ts_array[ws:i]

        temp_history = {}
        for key in all_mold_keys:
            vals = [temp_lookup[key].get(ts) for ts in window_ts if temp_lookup[key].get(ts) is not None]
            if vals:
                temp_history[key] = vals[:30]

        flow_history = {}
        for gid in all_group_ids:
            vals = [flow_lookup[gid].get(ts) for ts in window_ts if flow_lookup[gid].get(ts) is not None]
            if vals:
                flow_history[gid] = vals[:30]

        if not temp_history:
            continue
        if not flow_history:
            for gid in all_group_ids:
                flow_history[gid] = [config.FLOW_DEFAULT_LPM]

        current_dT = {}
        for key in all_mold_keys:
            dT_vals = dT_lookup.get(key, {})
            for ts in reversed(window_ts):
                if ts in dT_vals:
                    current_dT[key] = dT_vals[ts]
                    break

        features_8d = iso.extract_features(temp_history, flow_history, current_dT)
        if features_8d is None:
            continue

        f = features_8d[0]
        flow_rate = f[4]
        flow_drop = float(flow_rate < 0.5 * config.FLOW_DEFAULT_LPM)

        all_temps = [v for vals in temp_history.values() for v in vals]
        if len(all_temps) >= 10:
            x_arr = np.arange(len(all_temps))
            coeffs = np.polyfit(x_arr, all_temps, 1)
            y_pred = np.polyval(coeffs, x_arr)
            ss_res = np.sum((np.array(all_temps) - y_pred) ** 2)
            ss_tot = np.sum((np.array(all_temps) - np.mean(all_temps)) ** 2)
            drift_R2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.9
        else:
            drift_R2 = 0.9

        dT_vals = list(current_dT.values())
        dT_slope = float(np.mean(dT_vals) / 7.0) if dT_vals else 0.0

        rf_feat = np.array([[
            f[0], f[1], f[2], f[3], f[4],
            flow_drop, f[5], dT_slope, drift_R2, f[7],
        ]])

        label = CauseClassifier.auto_label(
            affected_ratio=float(f[2]), sudden_drop=bool(f[3]),
            flow_drop=bool(flow_drop), flow_rate=float(f[4]),
            variance=float(f[1]), R_squared=drift_R2,
            delta_T_calcaire_slope=dT_slope,
            temp_heater=config.T_HEATER, nominal_flow=config.FLOW_DEFAULT_LPM,
        )

        if_features.append(features_8d)
        rf_features.append(rf_feat)
        labels.append(label)

    log.info("Windows extracted: %d", len(if_features))
    return if_features, rf_features, labels

def save_report(results):
    path = os.path.join(os.path.dirname(__file__), '..', 'models', 'training_report.json')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    log.info("Report saved → %s", path)

def main():
    log.info("=" * 60)
    log.info("SYNTHETIC TRAINING (no InfluxDB)")
    log.info("  Days: %d", N_DAYS)
    log.info("=" * 60)

    os.makedirs(os.path.join(os.path.dirname(__file__), '..', 'backend', 'models'), exist_ok=True)

    temp_data, dT_data, flow_data = generate_all_data()

    result = build_windows(temp_data, dT_data, flow_data)
    if result is None:
        log.error("Window building failed")
        sys.exit(1)
    if_features, rf_features, labels = result

    if len(if_features) < 100:
        log.error("Too few windows (%d)", len(if_features))
        sys.exit(1)

    log.info("Training Isolation Forest...")
    normal_mask = [l == 'NORMAL' for l in labels]
    normal_features = [f for f, m in zip(if_features, normal_mask) if m]
    X_if = np.vstack(normal_features)
    iso = AnomalyDetector()
    iso.trained = False
    iso.train(X_if)

    log.info("Training Random Forest...")
    X_rf = np.vstack(rf_features)
    rf = CauseClassifier()
    rf.trained = False
    rf.train(X_rf, labels)

    from collections import Counter
    dist = Counter(labels)
    for cls, cnt in sorted(dist.items(), key=lambda x: -x[1]):
        log.info("  %-30s %6d (%.1f%%)", cls, cnt, cnt / len(labels) * 100)

    results = {
        'windows_total': len(if_features),
        'days_generated': N_DAYS,
        'class_distribution': dict(dist),
    }

    try:
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import classification_report, confusion_matrix, f1_score

        X_train, X_test, y_train, y_test = train_test_split(
            X_rf, labels, test_size=0.2, random_state=42, stratify=labels)

        rf2 = CauseClassifier()
        rf2.trained = False
        rf2.train(X_train, y_train)

        y_pred = rf2.model.predict(X_test)
        report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        cm = confusion_matrix(y_test, y_pred).tolist()
        f1_weighted = f1_score(y_test, y_pred, average='weighted', zero_division=0)

        log.info("\n" + classification_report(y_test, y_pred, zero_division=0))
        results['eval'] = {
            'f1_weighted': f1_weighted,
            'classification_report': report,
            'confusion_matrix': cm,
        }
        log.info("Weighted F1: %.4f", f1_weighted)
    except Exception as e:
        log.warning("Eval error: %s", e)

    save_report(results)

    try:
        from plots_evaluation import generate_all_plots
        pseudo_labels = np.array([1 if l != 'NORMAL' else 0 for l in labels])
        generate_all_plots(
            iso_model=iso, rf_model=rf,
            features_if=np.vstack(if_features),
            features_rf=X_rf, labels_rf=labels,
            pseudo_labels_if=pseudo_labels,
        )
        log.info("Plots generated in models/plots/")
    except Exception as e:
        log.warning("Plot error: %s", e)

    log.info("Done — models saved to backend/models/")

if __name__ == '__main__':
    main()
