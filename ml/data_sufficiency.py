import logging
import sys
import os
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
from sklearn.metrics import f1_score, r2_score
from sklearn.linear_model import Ridge
from sklearn.preprocessing import PolynomialFeatures

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

import config
import influxdb_manager as influx
from anomaly_detector import AnomalyDetector
from cause_classifier import CauseClassifier

log = logging.getLogger(__name__)

DAYS_TO_TEST = [3, 5, 7, 10, 14, 21, 28]


def count_real_data_days() -> int:
    if influx._query_api is None:
        influx.init_influxdb()
    if influx._query_api is None:
        return 0

    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: 0)
      |> filter(fn: (r) => r._measurement == "temperature")
      |> filter(fn: (r) => r._field == "temperature")
      |> first()
    '''
    try:
        tables = influx._query_api.query(flux, org=config.INFLUX_ORG)
        for table in tables:
            for record in table.records:
                first_ts = record.get_time()
                if first_ts:
                    delta = datetime.now(first_ts.tzinfo) - first_ts
                    return max(0, delta.days)
    except Exception as exc:
        log.warning("Could not query data range: %s", exc)
    return 0


def _load_data_by_day(days_back: int = 90):
    if influx._query_api is None:
        influx.init_influxdb()
    if influx._query_api is None:
        return None

    temp_flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{days_back}d)
      |> filter(fn: (r) => r._measurement == "temperature")
      |> filter(fn: (r) => r._field == "temperature")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "group_id", "mold_id", "temperature"])
    '''
    flow_flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{days_back}d)
      |> filter(fn: (r) => r._measurement == "flow")
      |> filter(fn: (r) => r._field == "flow_rate")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> keep(columns: ["_time", "group_id", "flow_rate"])
    '''

    try:
        temp_tables = influx._query_api.query(temp_flux, org=config.INFLUX_ORG)
        flow_tables = influx._query_api.query(flow_flux, org=config.INFLUX_ORG)
    except Exception as exc:
        log.error("InfluxDB query error: %s", exc)
        return None

    temp_by_day = defaultdict(lambda: defaultdict(list))
    for table in temp_tables:
        for record in table.records:
            ts = record.get_time()
            day = ts.date()
            key = (int(record['group_id']), int(record['mold_id']))
            temp_by_day[day][key].append((ts, float(record['temperature'])))

    flow_by_day = defaultdict(lambda: defaultdict(list))
    for table in flow_tables:
        for record in table.records:
            ts = record.get_time()
            day = ts.date()
            gid = int(record['group_id'])
            flow_by_day[day][gid].append((ts, float(record['flow_rate'])))

    sorted_days = sorted(set(temp_by_day.keys()) & set(flow_by_day.keys()))
    if not sorted_days:
        return None

    t0 = sorted_days[0]
    day_offset = {d: (d - t0).days for d in sorted_days}
    log.info("Loaded %d days of data (t0=%s)", len(sorted_days), t0)

    return {
        'temp_by_day': dict(temp_by_day),
        'flow_by_day': dict(flow_by_day),
        'sorted_days': sorted_days,
        'day_offset': day_offset,
        't0': t0,
    }


def _build_rf_features_for_day(data_bundle, day, day_offset_map):
    temp_by_key = data_bundle['temp_by_day'][day]
    flow_by_key = data_bundle['flow_by_day'][day]

    if not temp_by_key or not flow_by_key:
        return None, None

    all_mold_keys = sorted(temp_by_key.keys())
    all_group_ids = sorted(flow_by_key.keys())

    temp_history = {}
    for key, pairs in temp_by_key.items():
        vals = [v for _, v in pairs[-30:]]
        if vals:
            temp_history[key] = vals

    flow_history = {}
    for gid, pairs in flow_by_key.items():
        vals = [v for _, v in pairs[-30:]]
        if vals:
            flow_history[gid] = vals

    if not temp_history or not flow_history:
        return None, None

    affected = sum(1 for key in all_mold_keys
                   if temp_history.get(key) and temp_history[key][-1] < config.T_MOLD_CRITICAL)
    n_molds = max(len(temp_history), 1)
    affected_ratio = affected / n_molds

    slopes = []
    variances = []
    autocorrs = []
    for key, hist in temp_history.items():
        arr = np.array(hist, dtype=float)
        if len(arr) < 5:
            continue
        x = np.arange(len(arr))
        slope = np.polyfit(x, arr, 1)[0]
        slopes.append(slope)
        variances.append(float(np.var(arr)))
        if len(arr) > 2:
            with np.errstate(invalid='ignore', divide='ignore'):
                ac = float(np.corrcoef(arr[:-1], arr[1:])[0, 1])
            autocorrs.append(ac if not np.isnan(ac) else 0.0)

    sudden_drop = 0.0
    for key, hist in temp_history.items():
        if len(hist) >= 10 and hist[-1] - hist[0] < -1.0:
            sudden_drop = 1.0
            break

    flow_means = [float(np.mean(v)) for v in flow_history.values() if v] or [config.FLOW_DEFAULT_LPM]
    flow_vars = [float(np.var(v)) for v in flow_history.values() if v] or [0.0]
    flow_mean = float(np.mean(flow_means))
    flow_var = float(np.mean(flow_vars))

    if not slopes:
        return None, None

    f8 = np.array([[
        float(np.mean(slopes)),
        float(np.mean(variances)),
        affected_ratio,
        sudden_drop,
        flow_mean,
        flow_var,
        0.0,
        float(np.mean(autocorrs)) if autocorrs else 0.0,
    ]])

    flow_drop = float(flow_mean < 0.5 * config.FLOW_DEFAULT_LPM)
    all_temps = []
    for key, hist in temp_history.items():
        if len(hist) >= 5:
            all_temps.extend(hist[-30:])
    if all_temps:
        x_arr = np.arange(len(all_temps))
        coeffs = np.polyfit(x_arr, all_temps, 1)
        y_pred = np.polyval(coeffs, x_arr)
        ss_res = np.sum((np.array(all_temps) - y_pred) ** 2)
        ss_tot = np.sum((np.array(all_temps) - np.mean(all_temps)) ** 2)
        drift_R2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.9
    else:
        drift_R2 = 0.9

    f10 = np.array([[
        f8[0][0], f8[0][1], f8[0][2], f8[0][3], f8[0][4],
        flow_drop, f8[0][5], 0.0, drift_R2, f8[0][7],
    ]])

    label = CauseClassifier.auto_label(
        affected_ratio=affected_ratio,
        sudden_drop=bool(sudden_drop),
        flow_drop=bool(flow_drop),
        flow_rate=flow_mean,
        variance=float(np.mean(variances)) if variances else 0.0,
        R_squared=drift_R2,
        delta_T_calcaire_slope=0.0,
    )

    return f8, f10, label


def evaluate_rf_sufficiency(data_bundle) -> tuple:
    sorted_days = data_bundle['sorted_days']
    day_offset = data_bundle['day_offset']
    n_days = len(sorted_days)

    all_features = []
    all_labels = []
    day_of_sample = []

    for day in sorted_days:
        result = _build_rf_features_for_day(data_bundle, day, day_offset)
        if result is None or result[1] is None:
            continue
        _, f10, label = result
        all_features.append(f10[0])
        all_labels.append(label)
        day_of_sample.append(day_offset[day])

    if len(all_features) < 20 or len(set(all_labels)) < 2:
        log.info("RF sufficiency: too few samples (%d) or classes (%d)", len(all_features), len(set(all_labels)))
        return n_days, {}

    X = np.array(all_features)
    y = np.array(all_labels)
    f1_scores = {}

    for k in DAYS_TO_TEST:
        if k >= n_days:
            continue
        train_mask = np.array([d < k for d in day_of_sample])
        test_mask = np.array([d >= k for d in day_of_sample])

        n_train = np.sum(train_mask)
        n_test = np.sum(test_mask)

        if n_train < 5 or n_test < 3:
            continue

        X_train, X_test = X[train_mask], X[test_mask]
        y_train, y_test = y[train_mask], y[test_mask]

        train_classes = set(y_train)
        test_classes = set(y_test)
        if len(train_classes) < 2:
            continue

        rf = CauseClassifier()
        rf.trained = False
        try:
            rf.train(X_train, list(y_train))
        except Exception as exc:
            log.debug("RF train failed at k=%d: %s", k, exc)
            continue

        y_pred = [rf.predict(x.reshape(1, -1))['cause'] for x in X_test]
        macro = f1_score(y_test, y_pred, average='macro', zero_division=0)
        f1_scores[k] = macro
        log.debug("  RF sufficiency k=%d: F1-macro=%.4f (train=%d, test=%d)", k, macro, n_train, n_test)

    if len(f1_scores) < 2:
        return n_days, f1_scores

    sorted_ks = sorted(f1_scores.keys())
    scores = [f1_scores[k] for k in sorted_ks]

    for i in range(len(sorted_ks)):
        k = sorted_ks[i]
        score = scores[i]
        if score >= 0.85:
            if i >= 2:
                slope = (scores[i] - scores[i-2]) / max(k - sorted_ks[i-2], 1)
            elif i >= 1:
                slope = (scores[i] - scores[i-1]) / max(k - sorted_ks[i-1], 1)
            else:
                slope = 0.0

            if slope < 0.01:
                log.info("RF plateau at k=%d (F1=%.4f, slope=%.4f)", k, score, slope)
                return k, f1_scores

    best = sorted_ks[-1]
    log.info("RF no plateau found, best k=%d (F1=%.4f)", best, scores[-1])
    return best, f1_scores


def evaluate_ridge_sufficiency(data_bundle) -> tuple:
    sorted_days = data_bundle['sorted_days']
    n_days = len(sorted_days)
    r2_scores = {}

    for k in DAYS_TO_TEST:
        if k >= n_days:
            continue

        r2_per_mold = []
        for (gid, mid) in config.SENSOR_MAP.keys():
            raw = influx.query_daily_mean_mold(gid, mid, days_back=90)
            if len(raw) < k + 3:
                continue

            train_recs = raw[:k]
            test_recs = raw[k:]

            if len(train_recs) < config.RIDGE_MIN_DAYS:
                continue

            X_train = np.array([r['day_offset'] for r in train_recs]).reshape(-1, 1)
            y_train = np.array([r['value'] for r in train_recs])
            X_test = np.array([r['day_offset'] for r in test_recs]).reshape(-1, 1)
            y_test = np.array([r['value'] for r in test_recs])

            poly = PolynomialFeatures(degree=2, include_bias=True)
            X_train_p = poly.fit_transform(X_train)
            X_test_p = poly.transform(X_test)

            model = Ridge(alpha=1.0)
            try:
                model.fit(X_train_p, y_train)
            except Exception:
                continue

            y_pred = model.predict(X_test_p)
            r2 = r2_score(y_test, y_pred)
            if not np.isnan(r2):
                r2_per_mold.append(r2)

        if r2_per_mold:
            r2_scores[k] = float(np.mean(r2_per_mold))
            log.debug("  Ridge sufficiency k=%d: R²=%.4f", k, r2_scores[k])

    if len(r2_scores) < 2:
        return n_days, r2_scores

    sorted_ks = sorted(r2_scores.keys())
    scores = [r2_scores[k] for k in sorted_ks]

    for i in range(len(sorted_ks)):
        k = sorted_ks[i]
        score = scores[i]
        if score >= 0.80:
            if i >= 2:
                slope = (scores[i] - scores[i-2]) / max(k - sorted_ks[i-2], 1)
            elif i >= 1:
                slope = (scores[i] - scores[i-1]) / max(k - sorted_ks[i-1], 1)
            else:
                slope = 0.0

            if slope < 0.01:
                log.info("Ridge plateau at k=%d (R²=%.4f, slope=%.4f)", k, score, slope)
                return k, r2_scores

    best = sorted_ks[-1]
    log.info("Ridge no plateau found, best k=%d (R²=%.4f)", best, scores[-1])
    return best, r2_scores


def compute_real_data_threshold() -> int:
    days_real = count_real_data_days()
    log.info("Real data days in InfluxDB: %d", days_real)

    if days_real < 3:
        log.info("Too few real data days (%d) — using minimum threshold 7", days_real)
        return 7

    data = _load_data_by_day(min(days_real + 7, 90))
    if data is None:
        log.warning("Could not load data — using max(days_real, 7) as threshold")
        return max(days_real, 7)

    rf_k, rf_scores = evaluate_rf_sufficiency(data)
    ridge_k, ridge_scores = evaluate_ridge_sufficiency(data)

    threshold = max(rf_k, ridge_k, 7)
    log.info("Sufficiency threshold: max(RF k=%d, Ridge k=%d, min=7) = %d", rf_k, ridge_k, threshold)
    return threshold


def compute_sufficiency_with_details() -> dict:
    """Like compute_real_data_threshold(), but returns full details for plotting."""
    days_real = count_real_data_days()
    result = {
        'days_real': days_real,
        'rf_k': days_real,
        'ridge_k': days_real,
        'threshold': max(days_real, 7),
        'rf_f1_scores': {},
        'ridge_r2_scores': {},
    }

    if days_real < 3:
        return result

    data = _load_data_by_day(min(days_real + 7, 90))
    if data is None:
        return result

    rf_k, rf_scores = evaluate_rf_sufficiency(data)
    ridge_k, ridge_scores = evaluate_ridge_sufficiency(data)

    result['rf_k'] = rf_k
    result['ridge_k'] = ridge_k
    result['threshold'] = max(rf_k, ridge_k, 7)
    result['rf_f1_scores'] = rf_scores
    result['ridge_r2_scores'] = ridge_scores

    try:
        from plots_evaluation import generate_all_plots
        generate_all_plots(sufficiency_results=result)
    except Exception as exc:
        log.warning("Could not generate learning curve plot: %s", exc)

    return result


def get_retrain_mode() -> tuple:
    force_real = getattr(config, 'FORCE_REAL_ONLY', False)
    if force_real:
        log.info("FORCE_REAL_ONLY=True → real data only")
        return 'real_only', 0

    days_real = count_real_data_days()
    threshold = compute_real_data_threshold()

    if days_real >= threshold:
        log.info("%d real days ≥ %d threshold → real data only", days_real, threshold)
        return 'real_only', threshold
    else:
        log.info("%d real days < %d threshold → synthetic + real data", days_real, threshold)
        return 'mixed', threshold


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    mode, thresh = get_retrain_mode()
    print(f"Retrain mode: {mode}, threshold: {thresh} days")
