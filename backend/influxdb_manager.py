# influxdb_manager.py
# Writes sensor readings to InfluxDB using the existing configuration.
# Uses batch writes (12 points per HTTP POST) to minimize latency.
# Also provides query helpers for the ML models.

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

import config

log = logging.getLogger(__name__)

_client    = None
_write_api = None
_query_api = None


def init_influxdb():
    """Initialize the InfluxDB client. Uses the existing token/org/bucket from config."""
    global _client, _write_api, _query_api
    _client    = InfluxDBClient(url=config.INFLUX_URL, token=config.INFLUX_TOKEN, org=config.INFLUX_ORG)
    _write_api = _client.write_api(write_options=SYNCHRONOUS)
    _query_api = _client.query_api()
    log.info("InfluxDB client initialized — bucket: %s", config.INFLUX_BUCKET)


def write_sensors(readings, delta_T_calcaire_map: Dict = None):
    """
    Write all 12 sensor readings as a single batch HTTP POST.
    Each point contains: measurement=temperature, tags, fields, timestamp.
    """
    if _write_api is None:
        log.warning("InfluxDB not initialized — skipping write")
        return

    points = []
    for r in readings:
        mold_key = (r.group_id, r.mold_id)
        dT_calc  = (delta_T_calcaire_map or {}).get(mold_key, 0.0)

        p = (
            Point("temperature")
            .tag("mold_id",   str(r.mold_id))
            .tag("group_id",  str(r.group_id))
            .tag("position",  r.position)
            .tag("status",    r.status)
            .field("temperature",     r.temperature if r.temperature is not None else 0.0)
            .field("threshold",       r.threshold)
            .field("deviation",       r.deviation if r.deviation is not None else 0.0)
            .field("delta_T_calcaire", dT_calc)
        )
        points.append(p)

    try:
        _write_api.write(bucket=config.INFLUX_BUCKET, org=config.INFLUX_ORG, record=points)
    except Exception as exc:
        log.error("InfluxDB write error: %s", exc)


def query_daily_mean_mold(group_id: int, mold_id: int, days_back: int = 90) -> List[Dict]:
    """
    Query the daily mean temperature for a specific mold.
    Returns list of { day_offset: int, mean_temp: float } dicts.
    Used by the Ridge polynomial model for calibration and prediction.
    """
    if _query_api is None:
        return []

    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{days_back}d)
      |> filter(fn: (r) => r._measurement == "temperature")
      |> filter(fn: (r) => r._field == "delta_T_calcaire")
      |> filter(fn: (r) => r.group_id == "{group_id}" and r.mold_id == "{mold_id}")
      |> aggregateWindow(every: 1d, fn: mean, createEmpty: false)
      |> yield(name: "daily_mean")
    '''
    try:
        tables = _query_api.query(flux, org=config.INFLUX_ORG)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    'timestamp': record.get_time(),
                    'value':     record.get_value(),
                })
        # Convert to day offset from first record
        if results:
            t0 = results[0]['timestamp']
            for i, r in enumerate(results):
                r['day_offset'] = (r['timestamp'] - t0).days
        return results
    except Exception as exc:
        log.error("InfluxDB query error mold (%d,%d): %s", group_id, mold_id, exc)
        return []


def query_calibration_temp(group_id: int, mold_id: int) -> Optional[float]:
    """
    Return T_mold_jour1: the mean temperature from the very first day of operation.
    This is used to compute delta_T_normal for the grey-box model.
    """
    if _query_api is None:
        return None

    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: 0)
      |> filter(fn: (r) => r._measurement == "temperature")
      |> filter(fn: (r) => r._field == "temperature")
      |> filter(fn: (r) => r.group_id == "{group_id}" and r.mold_id == "{mold_id}")
      |> first()
    '''
    try:
        tables = _query_api.query(flux, org=config.INFLUX_ORG)
        for table in tables:
            for record in table.records:
                return record.get_value()
        return None
    except Exception as exc:
        log.error("InfluxDB calibration query error: %s", exc)
        return None


def close_influxdb():
    """Close the InfluxDB client."""
    global _client
    if _client:
        _client.close()
        log.info("InfluxDB client closed")
