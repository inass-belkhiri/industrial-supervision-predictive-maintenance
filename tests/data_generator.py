import sys
import os
import random
import math
import logging
from datetime import datetime, timedelta

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

import config
import influxdb_manager as influx

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

N_DAYS   = 60
SAMPLE_HZ = 1


def _clean(v, n):
    """Round float to n decimals with guaranteed clean float64 representation."""
    return float(f"{v:.{n}f}")

# ── Group temperature offsets (physical: distance from heater inlet) ──────────
GROUP_TEMP_OFFSET = {
    1: +0.3,
    2:  0.0,
    3: -0.3,
    4: -0.5,
}

# ── Mold position offsets within a group (gauche=edge, centre=hottest) ───────
MOLD_POSITION_OFFSET = {
    1: -0.1,
    2: +0.3,
}

# ── Encrassement drift rate per group (°C/day, after day 20) ─────────────────
# Groups with lower flow or higher temp tend to scale faster
ENCRASSEMENT_DRIFT = {
    1: -0.015,
    2: -0.025,
    3: -0.030,
    4: -0.020,
}

# ── Daily cycle amplitude (ambient temperature effect) ───────────────────────
DAILY_CYCLE_AMPLITUDE = 0.4
# Phase offset so minimum is at ~5h, maximum at ~14h
DAILY_CYCLE_PHASE = 0.21

DELTA_T_HEURISTIC = 1.0  # used also in train_sim_models.py

# ── Localized defect probability per day ──────────────────────────────────────
LOCAL_DEFECT_PROB = 0.10
LOCAL_DEFECT_DROP_RANGE = (0.5, 1.5)
LOCAL_DEFECT_DURATION = (2, 4)

TEMPERATURE_SCENARIOS = {
    'normal': {
        'weight': 0.60,
        'T_std':  0.3,
        'flow_mean': 16.5,
        'flow_std':  0.5,
        'T_scenario_offset': 0.0,
    },
    'calcaire': {
        'weight': 0.06,
        'T_std':  0.3,
        'flow_mean': 13.0,
        'flow_std':  1.0,
        'T_scenario_offset': -1.0,
        'intra_day_drift': -0.003,
    },
    'pompe_hs': {
        'weight': 0.04,
        'T_std':  1.0,
        'flow_mean': 3.0,
        'flow_std':  0.5,
        'T_scenario_offset': -8.0,
    },
    'resistance_hs': {
        'weight': 0.05,
        'T_std':  0.6,
        'flow_mean': 14.0,
        'flow_std':  1.0,
        'T_scenario_offset': -5.0,
    },
    'vanne_panne': {
        'weight': 0.05,
        'T_std':  1.2,
        'flow_mean': 0.3,
        'flow_std':  0.1,
        'T_scenario_offset': -6.0,
    },
    'fuite_circuit': {
        'weight': 0.08,
        'T_std':  0.5,
        'flow_mean': 10.0,
        'flow_std':  0.5,
        'T_scenario_offset': -5.0,
        'flow_decay': -0.001,
    },
    'isolation': {
        'weight': 0.04,
        'T_std':  0.3,
        'flow_mean': 16.5,
        'flow_std':  0.5,
        'T_scenario_offset': -6.0,
        'intra_day_drift': -0.015,
        'affected_mold': (1, 1),
    },
    'bruit': {
        'weight': 0.08,
        'T_std':  1.2,
        'flow_mean': 15.0,
        'flow_std':  3.0,
        'T_scenario_offset': 0.0,
    },
}

# ── Flow rate baseline per group (L/min) ─────────────────────────────────────
GROUP_FLOW_BASELINE = {
    1: 16.0,
    2: 16.5,
    3: 17.0,
    4: 16.2,
}


def generate_daily_pattern(day_offset: int) -> str:
    r = random.random()
    cumul = 0.0
    chosen = 'normal'
    for name, scenario in TEMPERATURE_SCENARIOS.items():
        cumul += scenario['weight']
        if r <= cumul:
            chosen = name
            break
    return chosen


def daily_cycle_offset(minute: int) -> float:
    return DAILY_CYCLE_AMPLITUDE * math.sin(
        2 * math.pi * (minute / 1440.0 - DAILY_CYCLE_PHASE)
    )


def generate_daily_temperature(
    day_offset: int, group_id: int, mold_id: int, scenario: dict, chosen: str = 'normal'
) -> list:
    group_offset  = GROUP_TEMP_OFFSET.get(group_id, 0.0)
    mold_offset   = MOLD_POSITION_OFFSET.get(mold_id, 0.0)
    drift         = 0.0
    if day_offset > 20:
        max_drift = ENCRASSEMENT_DRIFT.get(group_id, -0.02) * (N_DAYS - 20)
        drift = max_drift * (1 - math.exp(-0.05 * (day_offset - 20)))

    intra_day_drift = scenario.get('intra_day_drift', 0.0)
    n_affected = scenario.get('n_affected_molds', 6)
    affected_mold = scenario.get('affected_mold', None)
    is_affected = (group_id, mold_id) == affected_mold if affected_mold else (mold_id <= n_affected)

    defect_mold = None
    defect_duration = 0
    defect_drop = 0.0
    if random.random() < LOCAL_DEFECT_PROB:
        defect_mold = mold_id
        defect_duration = random.randint(*LOCAL_DEFECT_DURATION)
        defect_drop = random.uniform(*LOCAL_DEFECT_DROP_RANGE)

    noise_std = scenario.get('T_std', 0.3) * 0.08 / 0.3
    records = []
    prev_temp = None
    sc_offset = scenario.get('T_scenario_offset', 0.0) if is_affected else 0.0
    intra_drift = intra_day_drift if is_affected else 0.0
    alpha = 0.30 if abs(sc_offset) > 4.0 else 0.12 if abs(sc_offset) > 2.0 else 0.03
    for minute in range(0, 1440, 5):
        cycle = daily_cycle_offset(minute)

        target = config.T_HEATER + group_offset + mold_offset + cycle + drift + sc_offset + intra_drift * minute

        if prev_temp is None:
            prev_temp = target + random.gauss(0, noise_std)
        else:
            prev_temp = (1-alpha) * prev_temp + alpha * target + random.gauss(0, noise_std)
        t = prev_temp

        if mold_id == defect_mold and minute < defect_duration * 5:
            t -= defect_drop

        records.append({
            'minute': minute,
            'temperature': _clean(max(25, t), 1),
        })
    return records


def generate_flow_rate(
    day_offset: int, scenario: dict, group_id: int,
    scenario_name: str = 'normal', minute: int = 0
) -> float:
    base = GROUP_FLOW_BASELINE.get(group_id, config.FLOW_DEFAULT_LPM)
    flow_mean = scenario['flow_mean']
    flow_std  = scenario['flow_std']
    flow_decay = scenario.get('flow_decay', 0.0)
    if flow_mean < 5.0:
        val = flow_mean + random.gauss(0, flow_std)
    else:
        val = base * (flow_mean / config.FLOW_DEFAULT_LPM) + random.gauss(0, flow_std)
    if flow_decay:
        val += flow_decay * minute
    if scenario_name == 'pompe_hs' and group_id != 1:
        val *= 0.85
    if group_id == 3 and day_offset > 20:
        val *= 0.6
    return _clean(max(0, val), 2)


def inject_historical_data():
    log.info("Generating %d days of synthetic data...", N_DAYS)
    influx.init_influxdb()

    from influxdb_client import Point
    from grey_box import GreyBoxModel
    grey = GreyBoxModel()

    total_points = 0
    calibration_done = set()

    # Delete old data — two separate calls (InfluxDB v2.x doesn't support OR in predicates)
    try:
        from influxdb_client.client.delete_api import DeleteApi
        delete_api = DeleteApi(influx._client)
        for measurement in ('temperature', 'flow'):
            delete_api.delete(
                start=datetime(2020, 1, 1),
                stop=datetime.now(),
                predicate=f'_measurement="{measurement}"',
                bucket=config.INFLUX_BUCKET,
                org=config.INFLUX_ORG,
            )
        log.info("Old InfluxDB data deleted successfully")
    except Exception as exc:
        log.warning("Could not delete old data: %s", exc)

    for day in range(N_DAYS):
        timestamp = datetime.now() - timedelta(days=N_DAYS - day)
        # Day 0 forced to 'normal' so grey-box calibration is on clean 45°C baseline
        scenario_name = 'normal' if day == 0 else generate_daily_pattern(day)
        scenario = TEMPERATURE_SCENARIOS[scenario_name]

        batch = []

        for (gid, mid), (slave, reg) in config.SENSOR_MAP.items():
            temps = generate_daily_temperature(day, gid, mid, scenario, scenario_name)
            g_flow = generate_flow_rate(day, scenario, gid, scenario_name)
            for rec in temps:
                t = rec['temperature']
                if t < config.T_MOLD_CRITICAL:
                    status = 'CRITIQUE'
                elif t < config.T_MOLD_WARNING:
                    status = 'ALERTE'
                else:
                    status = 'OK'
                deviation = _clean(t - config.T_HEATER, 1)
                ts = timestamp + timedelta(minutes=rec['minute'])

                if (gid, mid) not in calibration_done:
                    grey.set_calibration(gid, mid, t)
                    calibration_done.add((gid, mid))

                gb = grey.compute(gid, mid, t, g_flow)

                p = (
                    Point("temperature")
                    .tag("mold_id",   str(mid))
                    .tag("group_id",  str(gid))
                    .tag("position",  config.POSITION_MAP.get(mid, 'unknown'))
                    .tag("status",    status)
                    .field("temperature",     _clean(t, 1))
                    .field("threshold",       _clean(config.T_HEATER, 1))
                    .field("deviation",       _clean(deviation, 1))
                    .field("delta_T_calcaire", _clean(gb['delta_T_calcaire'], 2))
                    .time(ts)
                )
                if (gid, mid) == (1, 1):
                    p = p.field("epaisseur_mm", _clean(gb['epaisseur_mm'], 2))
                batch.append(p)

        for gid in config.FLOW_SENSOR_PINS:
            for minute in range(0, 1440, 5):
                flow_val = generate_flow_rate(day, scenario, gid, scenario_name, minute)
                ts = timestamp + timedelta(minutes=minute)
                p = (
                    Point("flow")
                    .tag("group_id", str(gid))
                    .tag("unit", "lpm")
                    .field("flow_rate", _clean(flow_val, 2))
                    .time(ts)
                )
                batch.append(p)

        try:
            influx._write_api.write(
                bucket=config.INFLUX_BUCKET,
                org=config.INFLUX_ORG,
                record=batch,
            )
            total_points += len(batch)
        except Exception as e:
            log.warning("Batch write error day %d: %s", day, e)

        if (day + 1) % 10 == 0:
            log.info("  Day %d/%d — %d points written", day + 1, N_DAYS, total_points)

    influx.close_influxdb()
    log.info("Done — %d total points injected into InfluxDB", total_points)


if __name__ == '__main__':
    inject_historical_data()
