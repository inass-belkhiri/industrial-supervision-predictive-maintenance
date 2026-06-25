# influxdb_manager.py
# Writes sensor readings to InfluxDB using the existing configuration.
# Uses batch writes (12 points per HTTP POST) to minimize latency.
# Also provides query helpers for the ML models.

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import ASYNCHRONOUS

import config

log = logging.getLogger(__name__)


def _clean(v, n):
    """Round float to n decimals with guaranteed clean float64 representation."""
    return float(f"{v:.{n}f}")


_client    = None
_write_api = None
_query_api = None


def init_influxdb():
    """Initialize the InfluxDB client. Uses the existing token/org/bucket from config."""
    global _client, _write_api, _query_api
    try:
        _client    = InfluxDBClient(url=config.INFLUX_URL, token=config.INFLUX_TOKEN, org=config.INFLUX_ORG, timeout=5_000)
        _write_api = _client.write_api(write_options=ASYNCHRONOUS)
        _query_api = _client.query_api()
        health = _client.ping()
        if health:
            log.info("InfluxDB connected — bucket: %s  (version: %s)", config.INFLUX_BUCKET, health)
        else:
            log.error("InfluxDB ping returned unhealthy")
    except Exception as exc:
        log.error("InfluxDB connection failed — %s", exc)
        log.error("Check that InfluxDB is running on %s", config.INFLUX_URL)
        _client    = None
        _write_api = None
        _query_api = None


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
        if r.temperature is None:
            continue

        mold_key = (r.group_id, r.mold_id)
        dT_calc  = (delta_T_calcaire_map or {}).get(mold_key, 0.0)

        p = (
            Point("temperature")
            .tag("mold_id",   str(r.mold_id))
            .tag("group_id",  str(r.group_id))
            .tag("position",  r.position)
            .tag("status",    r.status)
            .field("temperature",     _clean(r.temperature, 1))
            .field("threshold",       _clean(r.threshold, 1))
            .field("deviation",       _clean(r.deviation, 1) if r.deviation is not None else 0.0)
            .field("delta_T_calcaire", _clean(dT_calc, 2))
        )
        points.append(p)

    if not points:
        return

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


def write_flow(group_id: int, flow_lpm: float):
    """Write a single flow measurement to InfluxDB (1 point per group per cycle)."""
    if _write_api is None:
        return
    p = (
        Point("flow")
        .tag("group_id", str(group_id))
        .tag("unit", "lpm")
        .field("flow_rate", _clean(flow_lpm, 2))
    )
    try:
        _write_api.write(bucket=config.INFLUX_BUCKET, org=config.INFLUX_ORG, record=p)
    except Exception as exc:
        log.error("InfluxDB flow write error group %d: %s", group_id, exc)


def query_flow_history(group_id: int, days_back: int = 7) -> List[Dict]:
    """Return hourly-averaged flow history for diagnostic charts."""
    if _query_api is None:
        return []
    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{days_back}d)
      |> filter(fn: (r) => r._measurement == "flow")
      |> filter(fn: (r) => r._field == "flow_rate")
      |> filter(fn: (r) => r.group_id == "{group_id}")
      |> aggregateWindow(every: 1h, fn: mean, createEmpty: false)
    '''
    try:
        tables = _query_api.query(flux, org=config.INFLUX_ORG)
        return [
            {'timestamp': r.get_time(), 'value': r.get_value()}
            for table in tables for r in table.records
        ]
    except Exception as exc:
        log.error("InfluxDB flow history query error group %d: %s", group_id, exc)
        return []


def query_recent(minutes: int = 30) -> dict:
    """
    Fetch recent raw temperature + flow + delta_T_calcaire data from InfluxDB.
    Returns { 'temperatures': [...], 'flows': [...], 'delta_T': [...], 'timestamps': [...] }.
    """
    if _query_api is None:
        return {'temperatures': [], 'flows': [], 'delta_T': [], 'timestamps': []}

    flux = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -{minutes}m)
      |> filter(fn: (r) => r._measurement == "temperature")
      |> filter(fn: (r) => r._field == "temperature" or r._field == "delta_T_calcaire" or r._field == "deviation")
      |> yield(name: "recent")
    '''
    try:
        tables = _query_api.query(flux, org=config.INFLUX_ORG)
        data = {'temperatures': [], 'flows': [], 'delta_T': [], 'timestamps': []}
        for table in tables:
            for record in table.records:
                field = record.get_field()
                val = record.get_value()
                ts = record.get_time()
                data['timestamps'].append(ts)
                group = record.values.get('group_id', '')
                mold = record.values.get('mold_id', '')
                if field == 'temperature':
                    data['temperatures'].append({'group': group, 'mold': mold, 'value': val, 'time': ts})
                elif field == 'delta_T_calcaire':
                    data['delta_T'].append({'group': group, 'mold': mold, 'value': val, 'time': ts})
        # Get flow data
        flow_flux = f'''
        from(bucket: "{config.INFLUX_BUCKET}")
          |> range(start: -{minutes}m)
          |> filter(fn: (r) => r._measurement == "flow")
          |> filter(fn: (r) => r._field == "flow_rate")
          |> yield(name: "flow_recent")
        '''
        flow_tables = _query_api.query(flow_flux, org=config.INFLUX_ORG)
        for table in flow_tables:
            for record in table.records:
                data['flows'].append({
                    'group': record.values.get('group_id', ''),
                    'value': record.get_value(),
                    'time': record.get_time()
                })
        return data
    except Exception as exc:
        log.error("InfluxDB query_recent error: %s", exc)
        return {'temperatures': [], 'flows': [], 'delta_T': [], 'timestamps': []}


def close_influxdb():
    """Close the InfluxDB client."""
    global _client
    if _client:
        _client.close()
        log.info("InfluxDB client closed")
