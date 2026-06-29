import sys
import os
import random
import asyncio
import logging

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.join(ROOT, 'backend'))
sys.path.insert(0, os.path.join(ROOT, 'ml'))

os.chdir(os.path.join(ROOT, 'tests'))

import config
import data_generator
import modbus_simulator
from anomaly_detector import AnomalyDetector
from cause_classifier import CauseClassifier

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger('train_sim_models')

N_CYCLES = {
    'NORMAL':       500,
    'GRADUAL_DROP': 200,
    'SUDDEN_DROP':  200,
    'NOISY':        200,
    'HEATER_FAIL':  200,
    'PUMP_FAIL':    200,
    'FUITE':        200,
}


def _generate_flow(mode: str, call_idx: int) -> float:
    if mode == 'PUMP_FAIL':
        val = 2.0 + random.gauss(0, 0.3)
    elif mode == 'NOISY':
        val = config.FLOW_DEFAULT_LPM + random.gauss(0, 3.0)
    elif mode == 'GRADUAL_DROP':
        val = config.FLOW_DEFAULT_LPM - call_idx * 0.02 + random.gauss(0, 0.3)
    elif mode == 'FUITE':
        val = 10.0 - call_idx * 0.01 + random.gauss(0, 0.3)
    else:
        val = config.FLOW_DEFAULT_LPM + random.gauss(0, 0.3)
    return max(0, val)


async def collect_normal():
    iso_extractor = AnomalyDetector()
    temp_history = {}
    flow_history = {}
    features_if = []

    log.info("Collecting NORMAL only for IF (%d cycles)", N_CYCLES['NORMAL'])
    modbus_simulator.set_mode('NORMAL')

    for call in range(N_CYCLES['NORMAL']):
        readings = await modbus_simulator.read_all_sensors(None)
        for r in readings:
            key = (r.group_id, r.mold_id)
            if key not in temp_history:
                temp_history[key] = []
            if r.temperature is not None:
                temp_history[key].append(r.temperature)
                if len(temp_history[key]) > 3600:
                    temp_history[key] = temp_history[key][-3600:]

        flow_val = _generate_flow('NORMAL', call)
        for gid in config.FLOW_SENSOR_PINS:
            if gid not in flow_history:
                flow_history[gid] = []
            flow_history[gid].append(flow_val)
            if len(flow_history[gid]) > 3600:
                flow_history[gid] = flow_history[gid][-3600:]

        if len(temp_history.get((1, 1), [])) < config.FEATURE_WINDOW_SECONDS:
            continue

        delta_T_map = {}
        for r in readings:
            key = (r.group_id, r.mold_id)
            if r.temperature is not None:
                delta_T_map[key] = max(0, config.T_HEATER - r.temperature - data_generator.DELTA_T_HEURISTIC)

        feat_8d = iso_extractor.extract_features(temp_history, flow_history, delta_T_map)
        if feat_8d is None:
            continue

        features_if.append(feat_8d[0])

    log.info("  NORMAL IF features: %d", len(features_if))
    if len(features_if) < 100:
        log.error("Too few IF features (%d) — aborting", len(features_if))
        sys.exit(1)

    log.info("=" * 60)
    log.info("Training Isolation Forest on %d NORMAL-only samples...", len(features_if))
    X_if = np.vstack(features_if)
    iso = AnomalyDetector()
    iso.trained = False
    iso.train(X_if)
    log.info("Isolation Forest saved")

    return iso


async def collect_all_for_rf():
    features_rf = []
    labels_rf = []
    iso_extractor = AnomalyDetector()

    for mode, n_cycles in N_CYCLES.items():
        log.info("Collecting RF features: %s (%d cycles)", mode, n_cycles)
        modbus_simulator.set_mode(mode)

        temp_history = {}
        flow_history = {}

        for call in range(n_cycles):
            readings = await modbus_simulator.read_all_sensors(None)

            for r in readings:
                key = (r.group_id, r.mold_id)
                if key not in temp_history:
                    temp_history[key] = []
                if r.temperature is not None:
                    temp_history[key].append(r.temperature)
                    if len(temp_history[key]) > 3600:
                        temp_history[key] = temp_history[key][-3600:]

            flow_val = _generate_flow(mode, call)
            for gid in config.FLOW_SENSOR_PINS:
                if gid not in flow_history:
                    flow_history[gid] = []
                flow_history[gid].append(flow_val)
                if len(flow_history[gid]) > 3600:
                    flow_history[gid] = flow_history[gid][-3600:]

            if len(temp_history.get((1, 1), [])) < config.FEATURE_WINDOW_SECONDS:
                continue

            delta_T_map = {}
            for r in readings:
                key = (r.group_id, r.mold_id)
                if r.temperature is not None:
                    delta_T_map[key] = max(0, config.T_HEATER - r.temperature - data_generator.DELTA_T_HEURISTIC)

            feat_8d = iso_extractor.extract_features(temp_history, flow_history, delta_T_map)
            if feat_8d is None:
                continue

            f = feat_8d[0]
            flow_rate = f[4]
            flow_drop = float(flow_rate < 0.5 * config.FLOW_DEFAULT_LPM)

            all_temps = []
            for key, hist in temp_history.items():
                if len(hist) >= 10:
                    all_temps.extend(list(hist)[-300:])
            if all_temps:
                x_arr = np.arange(len(all_temps))
                coeffs = np.polyfit(x_arr, all_temps, 1)
                y_pred = np.polyval(coeffs, x_arr)
                ss_res = np.sum((np.array(all_temps) - y_pred) ** 2)
                ss_tot = np.sum((np.array(all_temps) - np.mean(all_temps)) ** 2)
                drift_R_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.9
            else:
                drift_R_squared = 0.9

            dT_vals = list(delta_T_map.values())
            delta_T_calcaire_slope = float(np.mean(dT_vals) / 7.0) if dT_vals else 0.0

            feat_10d = np.array([[
                f[0], f[1], f[2], f[3], f[4],
                flow_drop, f[5], delta_T_calcaire_slope,
                drift_R_squared, f[7],
            ]])

            features_rf.append(feat_10d[0])
            labels_rf.append(CauseClassifier.auto_label(
                affected_ratio=float(f[2]),
                sudden_drop=bool(f[3]),
                flow_drop=bool(flow_drop),
                flow_rate=float(f[4]),
                variance=float(f[1]),
                R_squared=drift_R_squared,
                delta_T_calcaire_slope=delta_T_calcaire_slope,
                nominal_flow=config.FLOW_DEFAULT_LPM,
            ))

        log.info("  -> RF features so far: %d", len(features_rf))

    log.info("=" * 60)
    log.info("Training Random Forest on %d samples (%d classes)...",
             len(features_rf), len(set(labels_rf)))
    X_rf = np.vstack(features_rf)
    rf = CauseClassifier()
    rf.trained = False
    rf.train(X_rf, labels_rf)
    log.info("Random Forest saved")

    from collections import Counter
    dist = Counter(labels_rf)
    log.info("Class distribution:")
    for cls, count in sorted(dist.items(), key=lambda x: -x[1]):
        log.info("  %-30s %6d (%.1f%%)", cls, count, count / len(labels_rf) * 100)

    return rf


async def collect_and_train():
    await collect_normal()
    await collect_all_for_rf()
    log.info("Done — models ready for simulation in tests/models/")


if __name__ == '__main__':
    log.info("=" * 60)
    log.info("PRE-TRAINING ML MODELS ON SIMULATION MODES")
    log.info("=" * 60)
    asyncio.run(collect_and_train())
