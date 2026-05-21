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

import numpy as np


class _SafeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        return super().default(o)

import requests
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
import modbus_manager as modbus
import influxdb_manager as influx
from flow_sensor     import FlowSensor
from grey_box         import GreyBoxModel
from anomaly_detector import AnomalyDetector
from cause_classifier import CauseClassifier
from ridge_predictor  import RidgePredictor
from model_evaluator  import run_evaluation, should_retrain

logging.basicConfig(
    level  = logging.INFO,
    format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
log = logging.getLogger(__name__)

# ── State ─────────────────────────────────────────────────────────────────────
TEMP_HISTORY: Dict[Tuple, deque] = {}
FLOW_HISTORY: Dict[int, deque]   = {}

latest_sensors:     List[Dict] = []
latest_diagnostic:  Dict       = {}
latest_maintenance: List[Dict] = []

last_valid_sensors: Dict[Tuple, Dict] = {}

ws_clients: Set[WebSocket] = set()

grey_box   = GreyBoxModel()
iso_forest = AnomalyDetector()
rf         = CauseClassifier()
ridge_models: Dict[Tuple, RidgePredictor] = {}
calibration_temps: Dict[Tuple, float]     = {}
diagnostic_history: List[Dict]            = []

flow_sensors: Dict[int, FlowSensor] = {}

# Model health evaluation state
_eval_cycle_counter = 0
_metrics_history = {
    'if_anomaly_rate': [],
    'rf_f1_weighted': [],
}


# ── Startup / Shutdown ────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global flow_sensors
    log.info("Starting Supervision Thermique backend")
    influx.init_influxdb()
    await modbus.init_modbus()

    if config.FLOW_SENSOR_PINS:
        flow_sensors = {
            gid: FlowSensor(pin=pin)
            for gid, pin in config.FLOW_SENSOR_PINS.items()
        }
        log.info("Flow sensors initialized: %s", flow_sensors)
    else:
        flow_sensors = {}
        log.info("No flow sensor pins configured, using default flow rate")

    _load_calibrations()
    try:
        import modbus_simulator
        asyncio.create_task(_retrain_all_ridge())
        log.info("Simulation mode: Ridge pre-entraîné au démarrage")
    except ImportError:
        pass
    asyncio.create_task(monitoring_loop())
    asyncio.create_task(daily_retrain_loop())
    asyncio.create_task(model_health_loop())
    log.info("Backend ready — port %d", config.WS_PORT)
    yield
    await modbus.close_modbus()
    for sensor in flow_sensors.values():
        sensor.close()
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
        pass
    except Exception:
        log.warning("WS client error", exc_info=True)
    finally:
        ws_clients.discard(ws)
        log.info("WS client disconnected — total: %d", len(ws_clients))


# ── Simulation mode control (HTTP) ──────────────────────────────────────────────
class _ModeRequest(BaseModel):
    mode: str

@app.post("/api/sim/mode")
async def set_sim_mode(req: _ModeRequest):
    try:
        import modbus_simulator
        modbus_simulator.set_mode(req.mode)
        return {"status": "ok", "mode": req.mode}
    except ImportError:
        raise HTTPException(status_code=404, detail="Simulation non disponible en mode production")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Monitoring loop ───────────────────────────────────────────────────────────
async def monitoring_loop():
    while True:
        try:
            await asyncio.wait_for(_cycle(), timeout=25.0)
        except asyncio.TimeoutError:
            log.error("Cycle timed out — tentative de reconnexion Modbus")
            await modbus.close_modbus()
            await modbus.init_modbus()
        except asyncio.CancelledError:
            log.warning("Monitoring loop cancelled — restarting")
        except Exception as exc:
            log.error("Cycle error: %s", exc, exc_info=True)
        await asyncio.sleep(1.0 / config.ACQUISITION_HZ)


async def _cycle():
    global latest_sensors, latest_diagnostic

    readings = await modbus.read_all_sensors(calibration_temps)

    # Read heater temperature (simulated or real)
    temp_heater = None
    try:
        import modbus_simulator
        temp_heater = modbus_simulator.read_heater_temp()
    except ImportError:
        temp_heater = await modbus.read_heater_temp()
    if temp_heater is None:
        temp_heater = config.T_HEATER

    # Read all 4 flow sensors
    flow_readings = {}
    for gid, sensor in flow_sensors.items():
        flow_readings[gid] = sensor.read_lpm()
    flow_lpm = float(np.mean(list(flow_readings.values()))) if flow_readings else config.FLOW_DEFAULT_LPM

    # Update rolling histories
    for r in readings:
        key = (r.group_id, r.mold_id)
        if key not in TEMP_HISTORY:
            TEMP_HISTORY[key] = deque(maxlen=3600)
        if r.temperature is not None:
            TEMP_HISTORY[key].append(r.temperature)
    for gid, flpm in flow_readings.items():
        if gid not in FLOW_HISTORY:
            FLOW_HISTORY[gid] = deque(maxlen=3600)
        FLOW_HISTORY[gid].append(flpm)

    # Grey-box (per-group flow)
    delta_T_map  = {}
    grey_results = {}
    for r in readings:
        key = (r.group_id, r.mold_id)
        if r.temperature is not None:
            g_flow = flow_readings.get(r.group_id, flow_lpm)
            gb = grey_box.compute(r.group_id, r.mold_id, r.temperature, g_flow)
            grey_results[key] = gb
            delta_T_map[key]  = gb['delta_T_calcaire']

    # Anomaly detection
    temp_history_dict = {k: list(v) for k, v in TEMP_HISTORY.items()}
    features = iso_forest.extract_features(
        temp_history      = temp_history_dict,
        flow_history      = {gid: list(v) for gid, v in FLOW_HISTORY.items()},
        delta_T_calcaires = delta_T_map,
    )

    anomaly_result = {'anomaly_detected': False, 'anomaly_score': None}
    cause_result   = {'cause': 'NORMAL', 'confidence': 1.0, 'method': 'default', 'proba_dict': {}}
    affected_molds = []

    if features is not None:
        anomaly_result = iso_forest.predict(features)
        if anomaly_result['anomaly_detected']:
            affected_molds = [r.mold_id for r in readings if r.status in ('ALERTE', 'CRITIQUE')]
            affected_ratio = len(affected_molds) / config.N_MOLDS
            sudden_drop    = any(
                len(list(TEMP_HISTORY.get(k, []))) >= 120 and
                list(TEMP_HISTORY[k])[-1] - list(TEMP_HISTORY[k])[-120] < -1.0
                for k in TEMP_HISTORY
            )
            flow_drop = flow_lpm < 0.5 * config.FLOW_DEFAULT_LPM

            # Build the full 10-feature vector for Random Forest
            # (iso_forest.extract_features returns 8, RF expects 10)
            # Missing: flow_drop_flag, delta_T_calcaire_slope, drift_R_squared
            all_temps_for_r2 = []
            for key, hist in TEMP_HISTORY.items():
                if len(hist) >= 10:
                    all_temps_for_r2.extend(list(hist)[-300:])
            if all_temps_for_r2:
                x = np.arange(len(all_temps_for_r2))
                coeffs = np.polyfit(x, all_temps_for_r2, 1)
                y_pred = np.polyval(coeffs, x)
                ss_res = np.sum((np.array(all_temps_for_r2) - y_pred) ** 2)
                ss_tot = np.sum((np.array(all_temps_for_r2) - np.mean(all_temps_for_r2)) ** 2)
                drift_R_squared = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.9
            else:
                drift_R_squared = 0.9

            dT_vals = list(delta_T_map.values())
            delta_T_calcaire_slope = float(np.mean(dT_vals) / 7.0) if dT_vals else 0.0

            rf_features = np.array([[
                features[0][0],                    # slope_T_mold
                features[0][1],                    # variance_T_mold
                features[0][2],                    # affected_molds_ratio
                features[0][3],                    # sudden_drop_flag
                features[0][4],                    # flow_rate
                float(flow_drop),                  # flow_drop_flag
                features[0][5],                    # flow_variance
                delta_T_calcaire_slope,            # delta_T_calcaire_slope
                drift_R_squared,                   # drift_R_squared
                features[0][7],                    # autocorr_lag1
            ]])

            rule_result = rf.physical_rules(
                affected_ratio=affected_ratio,
                sudden_drop=sudden_drop,
                flow_rate=flow_lpm,
                flow_drop=flow_drop,
                temp_heater=temp_heater,
            )
            cause_result = rule_result if rule_result else (
                rf.predict(rf_features) if rf.trained else cause_result
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

        temp   = r.temperature
        status = r.status
        dev    = r.deviation

        # If the sensor didn't respond, reuse the last known good value
        # so the UI stays stable instead of blinking "--"
        if temp is None and key in last_valid_sensors:
            prev = last_valid_sensors[key]
            temp = prev['temperature']
            dev  = prev['deviation']

        entry = {
            'group_id':         r.group_id,
            'mold_id':          r.mold_id,
            'position':         r.position,
            'temperature':      temp,
            'status':           status,
            'threshold':        r.threshold,
            'deviation':        dev,
            'timestamp':        r.timestamp,
            'epaisseur_mm':     gb.get('epaisseur_mm'),
            'delta_T_calcaire': gb.get('delta_T_calcaire'),
            'urgence':          gb.get('urgence', 'OK'),
            'degradation_pct':  gb.get('degradation_pct', 0),
        }

        sensor_list.append(entry)

        if temp is not None:
            last_valid_sensors[key] = {
                'temperature': temp,
                'deviation':   dev,
            }

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

    # ENVOI WEBHOOK N8N — severity 3 niveaux
    if anomaly_result['anomaly_detected']:
        worst_status = 'OK'
        for s in latest_sensors:
            st = s.get('status', 'OK')
            if st == 'CRITIQUE':
                worst_status = 'CRITIQUE'
                break
            if st == 'ALERTE':
                worst_status = 'ALERTE'
        severity_map = {'CRITIQUE': 'CRITICAL', 'ALERTE': 'WARNING', 'OK': 'WARNING'}
        try:
            requests.post(
                config.N8N_WEBHOOK_ALERT,
                json={
                    'timestamp': datetime.now().isoformat(),
                    'severity': severity_map.get(worst_status, 'WARNING'),
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
            log.info("Alert sent to n8n webhook (severity: %s)", severity_map.get(worst_status, 'WARNING'))
        except Exception as e:
            log.warning("n8n webhook failed: %s", e)

    influx.write_sensors(readings, delta_T_map)
    for gid, flpm in flow_readings.items():
        influx.write_flow(gid, flpm)
    await _broadcast_all()

    # Model health evaluation cycle counter
    global _eval_cycle_counter
    _eval_cycle_counter += 1


# ── Broadcast ─────────────────────────────────────────────────────────────────
async def _broadcast_all():
    global ws_clients
    try:
        payload = json.dumps({
            'sensors':     latest_sensors,
            'diagnostic':  latest_diagnostic,
            'maintenance': latest_maintenance,
        }, cls=_SafeEncoder)
    except Exception:
        log.warning("Broadcast serialization failed", exc_info=True)
        return
    dead = set()
    for ws in list(ws_clients):
        try:
            await asyncio.wait_for(ws.send_text(payload), timeout=5.0)
        except asyncio.TimeoutError:
            dead.add(ws)
        except Exception:
            dead.add(ws)
    ws_clients -= dead


async def _broadcast_to(ws: WebSocket):
    try:
        await ws.send_text(json.dumps({
            'sensors':     latest_sensors,
            'diagnostic':  latest_diagnostic,
            'maintenance': latest_maintenance,
        }, cls=_SafeEncoder))
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


async def _retrain_if_rf():
    log.info("Retraining Isolation Forest + Random Forest from InfluxDB data")
    try:
        raw = influx.query_recent(minutes=config.EVAL_WINDOW_MINUTES)
        from model_evaluator import build_feature_vectors, auto_label_anomaly, auto_label_cause
        features_if, features_rf = build_feature_vectors(raw)
        if features_if is None:
            log.warning("Retrain skipped: insufficient data")
            return

        n_samples = max(len(raw.get('temperatures', [])), 50)
        if features_if.shape[0] == 1:
            X_if = features_if
            for _ in range(max(n_samples // 10, 5)):
                noise = np.random.randn(1, 8) * 0.05
                X_if = np.vstack([X_if, features_if + noise])
        else:
            X_if = features_if
        iso_forest.train(X_if)
        log.info("Isolation Forest retrained on %d samples", len(X_if))

        if features_rf is not None and raw.get('temperatures'):
            X_rf_list, y_rf_list = [], []
            true_cause = auto_label_cause(raw)
            if true_cause:
                if features_rf.shape[0] == 1:
                    X_rf = features_rf
                    for _ in range(max(n_samples // 10, 5)):
                        noise = np.random.randn(1, 10) * 0.05
                        X_rf = np.vstack([X_rf, features_rf + noise])
                else:
                    X_rf = features_rf
                y_list = [true_cause] * len(X_rf)
                rf.train(X_rf, y_list)
                log.info("Random Forest retrained on %d samples, cause: %s", len(X_rf), true_cause)
    except Exception as exc:
        log.error("Retrain IF/RF failed: %s", exc, exc_info=True)


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


# ── Model health loop ─────────────────────────────────────────────────────────
async def model_health_loop():
    global _eval_cycle_counter, _metrics_history
    while True:
        try:
            await asyncio.sleep(1.0)
            if _eval_cycle_counter < config.EVAL_INTERVAL_CYCLES:
                continue

            _eval_cycle_counter = 0
            log.info("Model health evaluation starting...")

            if_metrics, rf_metrics = run_evaluation(
                iso_forest, rf, influx,
                minutes=config.EVAL_WINDOW_MINUTES
            )

            if 'error' in if_metrics or 'error' in rf_metrics:
                log.warning("Model health evaluation skipped: %s / %s",
                            if_metrics.get('error'), rf_metrics.get('error'))
                continue

            anomaly_rate = if_metrics.get('anomaly_rate', 0)
            rf_f1 = rf_metrics.get('f1_weighted', 0)

            _metrics_history['if_anomaly_rate'].append(anomaly_rate)
            _metrics_history['rf_f1_weighted'].append(rf_f1)

            if len(_metrics_history['if_anomaly_rate']) > config.EVAL_PERSISTENCE:
                _metrics_history['if_anomaly_rate'].pop(0)
                _metrics_history['rf_f1_weighted'].pop(0)

            decision, reasons = should_retrain(
                _metrics_history,
                if_anomaly_rate_max=config.IF_ANOMALY_RATE_MAX,
                rf_f1_weighted_min=config.RF_F1_WEIGHTED_MIN,
                persistence=config.EVAL_PERSISTENCE,
            )

            if decision:
                log.warning("Model retrain triggered: %s", reasons)
                await _retrain_if_rf()
                _metrics_history = {'if_anomaly_rate': [], 'rf_f1_weighted': []}
                log.info("Model retrain completed, metrics history reset")

        except asyncio.CancelledError:
            break
        except Exception as exc:
            log.error("Model health loop error: %s", exc, exc_info=True)


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
