# tests/data_generator.py
# Generates synthetic historical data and injects it into InfluxDB.
# Supports ML training (Ridge, Isolation Forest) and calibration.

import sys
import os
import random
import logging
from datetime import datetime, timedelta

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

import config
import influxdb_manager as influx

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

N_DAYS   = 60   # number of days to generate
SAMPLE_HZ = 1   # samples per second (stored as 1/min aggregate to keep InfluxDB light)

TEMPERATURE_SCENARIOS = {
    'normal': {
        'weight': 0.80,
        'T_mean': 44.5,
        'T_std':  0.3,
        'flow_mean': 16.5,
        'flow_std':  0.5,
    },
    'calcaire': {
        'weight': 0.10,
        'T_mean': 43.0,
        'T_std':  0.4,
        'flow_mean': 13.0,
        'flow_std':  1.0,
    },
    'pompe_hs': {
        'weight': 0.05,
        'T_mean': 39.0,
        'T_std':  1.5,
        'flow_mean': 3.0,
        'flow_std':  0.5,
    },
    'bruit': {
        'weight': 0.05,
        'T_mean': 44.0,
        'T_std':  1.2,
        'flow_mean': 15.0,
        'flow_std':  3.0,
    },
}


def generate_daily_pattern(day_offset: int) -> dict:
    r = random.random()
    cumul = 0.0
    chosen = 'normal'
    for name, scenario in TEMPERATURE_SCENARIOS.items():
        cumul += scenario['weight']
        if r <= cumul:
            chosen = name
            break
    return TEMPERATURE_SCENARIOS[chosen]


def generate_daily_temperature(
    day_offset: int, mold_id: int, scenario: dict
) -> list:
    t_base = scenario['T_mean'] + random.gauss(0, 0.1)
    if mold_id <= 3:
        t_base += 0.2
    records = []
    for minute in range(0, 1440, 5):
        t = t_base + random.gauss(0, scenario['T_std'])
        if day_offset > 30:
            t -= 0.02 * (day_offset - 30)
        records.append({
            'minute': minute,
            'temperature': round(max(30, t), 2),
        })
    return records


def generate_flow_rate(day_offset: int, scenario: dict, group_id: int) -> float:
    base = scenario['flow_mean'] + random.gauss(0, scenario['flow_std'])
    if group_id == 3 and day_offset > 20:
        base *= 0.6
    return round(max(0, base), 2)


def inject_historical_data():
    log.info("Generating %d days of synthetic data...", N_DAYS)
    influx.init_influxdb()

    from influxdb_client import Point

    total_points = 0

    for day in range(N_DAYS):
        timestamp = datetime.now() - timedelta(days=N_DAYS - day)
        scenario = generate_daily_pattern(day)

        # Write temperature data (1 point per 5 minutes per mold)
        for (gid, mid), (slave, reg) in config.SENSOR_MAP.items():
            temps = generate_daily_temperature(day, mid, scenario)
            for rec in temps:
                t = rec['temperature']
                status = 'ALERTE' if t < config.T_MOLD_CRITICAL else 'OK'
                deviation = round(t - config.T_HEATER, 3)
                ts = timestamp + timedelta(minutes=rec['minute'])

                p = (
                    Point("temperature")
                    .tag("mold_id",   str(mid))
                    .tag("group_id",  str(gid))
                    .tag("position",  config.POSITION_MAP.get(mid, 'unknown'))
                    .tag("status",    status)
                    .field("temperature",     t)
                    .field("threshold",       config.T_HEATER)
                    .field("deviation",       deviation)
                    .field("delta_T_calcaire", max(0, round(config.T_HEATER - t - 1.0, 4)))
                )
                try:
                    influx._write_api.write(
                        bucket=config.INFLUX_BUCKET,
                        org=config.INFLUX_ORG,
                        record=p,
                    )
                    total_points += 1
                except Exception as e:
                    log.warning("Write error day %d mold (%d,%d): %s", day, gid, mid, e)

        # Write flow data (1 point per hour per group)
        for gid in config.FLOW_SENSOR_PINS:
            flow_val = generate_flow_rate(day, scenario, gid)
            ts = timestamp + timedelta(hours=12)
            p = (
                Point("flow")
                .tag("group_id", str(gid))
                .tag("unit", "lpm")
                .field("flow_rate", flow_val)
            )
            try:
                influx._write_api.write(
                    bucket=config.INFLUX_BUCKET,
                    org=config.INFLUX_ORG,
                    record=p,
                )
                total_points += 1
            except Exception as e:
                log.warning("Flow write error day %d group %d: %s", day, gid, e)

        if (day + 1) % 10 == 0:
            log.info("  Day %d/%d — %d points written", day + 1, N_DAYS, total_points)

    influx.close_influxdb()
    log.info("Done — %d total points injected into InfluxDB", total_points)


if __name__ == '__main__':
    inject_historical_data()
