# main.py
# FastAPI backend entry point.
# ML folder is located at ../ml/ relative to this file.
# sys.path is patched at startup so Python can find the ml package.

import sys
import os

# Allow importing from the sibling ml/ folder
# Structure: supervision_thermique/backend/main.py
#            supervision_thermique/ml/grey_box.py
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ML_DIR   = os.path.join(ROOT_DIR, 'ml')
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from collections import deque
from typing import Dict, List, Set, Tuple

import requests
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

import config
import modbus_manager as modbus
import influxdb_manager as influx
from grey_box        import GreyBoxModel
from anomaly_detector import AnomalyDetector
from cause_classifier import CauseClassifier
from ridge_predictor  import RidgePredictor

logging.basicConfig(
    level  = logging.INFO,
    format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
log = logging.getLogger(__name__)

# ── State ─────────────────────────────────────────────────────────────────────
TEMP_HISTORY: Dict[Tuple, deque] = {}
FLOW_HISTORY: deque              = deque(maxlen=3600)

latest_sensors:     List[Dict] = []
latest_diagnostic:  Dict       = {}
latest_maintenance: List[Dict] = []

ws_clients: Set[WebSocket] = set()

grey_box   = GreyBoxModel()
iso_forest = AnomalyDetector()
rf         = CauseClassifier()
ridge_models: Dict[Tuple, RidgePredictor] = {}
calibration_temps: Dict[Tuple, float]     = {}
diagnostic_history: List[Dict]            = []


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting Supervision Thermique backend")
    influx.init_influxdb()
    await modbus.init_modbus()
    _load_calibrations()
    asyncio.create_task(monitoring_loop())
    asyncio.create_task(daily_retrain_loop())
    log.info("Backend ready — port %d", config.WS_PORT)
    yield
    await modbus.close_modbus()
    influx.close_influxdb()
    log.info("Backend shutdown")


app = FastAPI(title="Supervision Thermique Industrielle", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    ws_clients.add(ws)
    log.info("WS client connected — total: %d", len(ws_clients))
    try:
        await _broadcast_to(ws)
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.discard(ws)
        log.info("WS client disconnected — total: %d", len(ws_clients))


# ── Monitoring loop ───────────────────────────────────────────────────────────
async def monitoring_loop():
    while True:
        try:
            await _cycle()
        except Exception as exc:
            log.error("Cycle error: %s", exc, exc_info=True)
        await asyncio.sleep(1.0 / config.ACQUISITION_HZ)


async def _cycle():
    global latest_sensors, latest_diagnostic

    readings = await modbus.read_all_sensors(calibration_temps)
    flow_lpm = config.FLOW_DEFAULT_LPM

    # Update rolling histories
    for r in readings:
        key = (r.group_id, r.mold_id)
        if key not in TEMP_HISTORY:
            TEMP_HISTORY[key] = deque(maxlen=3600)
        if r.temperature is not None:
            TEMP_HISTORY[key].append(r.temperature)
    FLOW_HISTORY.append(flow_lpm)

    # Grey-box
    delta_T_map  = {}
    grey_results = {}
    for r in readings:
        key = (r.group_id, r.mold_id)
        if r.temperature is not None:
            gb = grey_box.compute(r.group_id, r.mold_id, r.temperature, flow_lpm)
            grey_results[key] = gb
            delta_T_map[key]  = gb['delta_T_calcaire']

    # Anomaly detection
    temp_history_dict = {k: list(v) for k, v in TEMP_HISTORY.items()}
    features = iso_forest.extract_features(
        temp_history      = temp_history_dict,
        flow_history      = list(FLOW_HISTORY),
        delta_T_calcaires = delta_T_map,
    )

    anomaly_result = {'anomaly_detected': False, 'anomaly_score': None}
    cause_result   = {'cause': 'NORMAL', 'confidence': 1.0, 'method': 'default', 'proba_dict': {}}
    affected_molds = []

    if features is not None:
        anomaly_result = iso_forest.predict(features)
        if anomaly_result['anomaly_detected']:
            affected_molds = [r.mold_id for r in readings if r.status == 'ALERTE']
            affected_ratio = len(affected_molds) / config.N_MOLDS
            sudden_drop    = any(
                len(list(TEMP_HISTORY.get(k, []))) >= 120 and
                list(TEMP_HISTORY[k])[-1] - list(TEMP_HISTORY[k])[-120] < -1.0
                for k in TEMP_HISTORY
            )
            flow_drop = flow_lpm < 0.5 * config.FLOW_DEFAULT_LPM
            # Get T_heater (assume first sensor reading or separate query)
            temp_heater = config.T_HEATER  # Using config value

            rule_result = rf.physical_rules(
                affected_ratio=affected_ratio,
                sudden_drop=sudden_drop,
                flow_rate=flow_lpm,
                flow_drop=flow_drop,
                temp_heater=temp_heater,
            )
            cause_result = rule_result if rule_result else (
                rf.predict(features) if rf.trained else cause_result
            )

            # ENRICHISSEMENT AMDEC (NOUVEAU)
            cause = cause_result.get('cause')
            if cause and cause in config.AMDEC_FAILURE_MODES:
                amdec_info = config.AMDEC_FAILURE_MODES[cause]
                cause_result['amdec_criticite'] = amdec_info['criticite']
                cause_result['amdec_priorite'] = amdec_info['priorite']
                cause_result['actions'] = amdec_info['actions']
            diagnostic_history.append({
                'timestamp':  datetime.now().isoformat(),
                'cause':      cause_result['cause'],
                'confidence': cause_result['confidence'],
            })
            if len(diagnostic_history) > 100:
                diagnostic_history.pop(0)

    # Build sensor list
    sensor_list = []
    for r in readings:
        key = (r.group_id, r.mold_id)
        gb  = grey_results.get(key, {})
        sensor_list.append({
            'group_id':         r.group_id,
            'mold_id':          r.mold_id,
            'position':         r.position,
            'temperature':      r.temperature,
            'status':           r.status,
            'threshold':        r.threshold,
            'deviation':        r.deviation,
            'timestamp':        r.timestamp,
            'epaisseur_mm':     gb.get('epaisseur_mm'),
            'delta_T_calcaire': gb.get('delta_T_calcaire'),
            'urgence':          gb.get('urgence', 'OK'),
            'degradation_pct':  gb.get('degradation_pct', 0),
        })

    latest_sensors = sensor_list
    latest_diagnostic = {
        'anomaly_detected': anomaly_result['anomaly_detected'],
        'anomaly_score':    anomaly_result['anomaly_score'],
        'cause':            cause_result['cause'],
        'confidence':       cause_result['confidence'],
        'affected_molds':   affected_molds,
        'timestamp':        datetime.now().isoformat(),
        'history':          diagnostic_history[-20:],
        'features': {
            'Score IF': anomaly_result.get('anomaly_score'),
            'Cause':    cause_result['cause'],
            'Methode':  cause_result.get('method', '--'),
        },
    }

    # ENVOI WEBHOOK N8N (NOUVEAU)
    if anomaly_result['anomaly_detected']:
        try:
            requests.post(
                config.N8N_WEBHOOK_ALERT,
                json={
                    'timestamp': datetime.now().isoformat(),
                    'severity': 'CRITICAL' if any(
                        s.get('status') == 'ALERTE' for s in latest_sensors
                    ) else 'WARNING',
                    'cause': cause_result.get('cause'),
                    'confidence': cause_result.get('confidence'),
                    'amdec_criticite': cause_result.get('amdec_criticite'),
                    'amdec_priorite': cause_result.get('amdec_priorite'),
                    'actions': cause_result.get('actions', []),
                    'affected_molds': affected_molds,
                    'alert_type': 'THERMAL_ANOMALY'
                },
                timeout=5
            )
            log.info("Alert sent to n8n webhook")
        except Exception as e:
            log.warning("n8n webhook failed: %s", e)

    influx.write_sensors(readings, delta_T_map)
    await _broadcast_all()


# ── Broadcast ─────────────────────────────────────────────────────────────────
async def _broadcast_all():
    payload = json.dumps({
        'sensors':     latest_sensors,
        'diagnostic':  latest_diagnostic,
        'maintenance': latest_maintenance,
    })
    dead = set()
    for ws in list(ws_clients):
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    ws_clients -= dead


async def _broadcast_to(ws: WebSocket):
    try:
        await ws.send_text(json.dumps({
            'sensors':     latest_sensors,
            'diagnostic':  latest_diagnostic,
            'maintenance': latest_maintenance,
        }))
    except Exception:
        pass


# ── Daily retrain ─────────────────────────────────────────────────────────────
async def daily_retrain_loop():
    while True:
        now      = datetime.now()
        next_run = now.replace(hour=config.RETRAIN_HOUR, minute=0, second=0, microsecond=0)
        if next_run <= now:
            from datetime import timedelta
            next_run = next_run + timedelta(days=1)
        await asyncio.sleep((next_run - now).total_seconds())
        await _retrain_all_ridge()


async def _retrain_all_ridge():
    global latest_maintenance
    log.info("Starting daily Ridge retraining")
    maintenance_list = []

    for (gid, mid) in config.SENSOR_MAP.keys():
        key         = (gid, mid)
        cal         = calibration_temps.get(key, config.T_HEATER - 1.5)
        delta_T_max = max((config.T_HEATER - config.T_MOLD_CRITICAL) - (config.T_HEATER - cal), 0.1)

        predictor = ridge_models.get(key)
        if predictor is None:
            predictor = RidgePredictor(gid, mid, delta_T_max)
            ridge_models[key] = predictor

        records = influx.query_daily_mean_mold(gid, mid, days_back=90)
        if records:
            predictor.fit(records)

        result        = predictor.predict_maintenance()
        history_chart = [{'day': r['day_offset'], 'v': r['value']} for r in records[-90:]]
        sensor        = next((s for s in latest_sensors
                              if s['group_id'] == gid and s['mold_id'] == mid), {})

        entry = {
            'group_id':        gid,
            'mold_id':         mid,
            'position':        config.POSITION_MAP.get(mid, 'unknown'),
            'epaisseur_mm':    sensor.get('epaisseur_mm'),
            'delta_T_calcaire': sensor.get('delta_T_calcaire'),
            'urgence':         sensor.get('urgence', 'OK'),
            'degradation_pct': sensor.get('degradation_pct', 0),
            'history_chart':   history_chart,
        }
        if result:
            entry.update(result)
        maintenance_list.append(entry)

    latest_maintenance = maintenance_list
    log.info("Ridge retraining done — %d molds", len(maintenance_list))


# ── Calibration ───────────────────────────────────────────────────────────────
def _load_calibrations():
    for (gid, mid) in config.SENSOR_MAP.keys():
        T_jour1 = influx.query_calibration_temp(gid, mid) or 43.5
        calibration_temps[(gid, mid)] = T_jour1
        grey_box.set_calibration(gid, mid, T_jour1)
        log.info("Calibration mold (%d,%d): %.2f", gid, mid, T_jour1)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    uvicorn.run("main:app", host=config.WS_HOST, port=config.WS_PORT, reload=False)
