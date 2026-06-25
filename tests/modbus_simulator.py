# tests/modbus_simulator.py
# Simulates 12 Modbus temperature sensors for testing without hardware.
# Drop-in replacement for modbus_manager.read_all_sensors()

import math
import random
import logging
from datetime import datetime
from typing import List, Optional

import config
from modbus_manager import SensorReading

log = logging.getLogger(__name__)

SIMULATION_MODES = {
    'NORMAL':       'all temperatures stable around 44-45°C',
    'GRADUAL_DROP': 'slow temperature decay (-0.03°C per call)',
    'SUDDEN_DROP':  'sudden -5°C drop below critical threshold on all molds',
    'NOISY':        'normal with 10% random ERREUR readings + random fluctuations',
    'HEATER_FAIL':  'all molds dropping below 42°C (heater failure)',
    'PUMP_FAIL':    'global drop + erratic readings (pump failure)',
}

_call_counter = 0
_current_mode  = 'NORMAL'
_base_temps    = {}

# References to backend in-memory histories (attached by main.py at startup)
_temp_history_ref   = None
_flow_history_ref   = None
_last_valid_ref     = None


def attach_histories(temp_history, flow_history, last_valid_sensors):
    global _temp_history_ref, _flow_history_ref, _last_valid_ref
    _temp_history_ref = temp_history
    _flow_history_ref = flow_history
    _last_valid_ref   = last_valid_sensors
    log.info("Simulator attached to backend histories")


def _clear_backend_histories():
    if _temp_history_ref is not None:
        _temp_history_ref.clear()
    if _flow_history_ref is not None:
        _flow_history_ref.clear()
    if _last_valid_ref is not None:
        _last_valid_ref.clear()
    log.info("Backend histories cleared for mode switch")


def set_mode(mode: str):
    global _current_mode, _call_counter, _base_temps
    if mode not in SIMULATION_MODES:
        raise ValueError(f"Unknown mode: {mode}. Choices: {list(SIMULATION_MODES.keys())}")
    _current_mode = mode
    _call_counter = 0
    _base_temps   = {}
    _clear_backend_histories()
    log.info("Simulator mode set to '%s' — %s", mode, SIMULATION_MODES[mode])


def get_mode() -> str:
    return _current_mode


def read_heater_temp() -> float:
    if _current_mode == 'HEATER_FAIL':
        decay = max(_call_counter * 0.02, 0)
        return round(45.0 - decay, 2)
    return round(45.0 + random.gauss(0, 0.3), 2)


async def read_all_sensors(calibration_temps: dict = None) -> List[SensorReading]:
    global _call_counter, _base_temps

    _call_counter += 1
    now = datetime.now().isoformat(timespec='seconds')

    # Initialize base temperatures on first call
    if not _base_temps:
        for (gid, mid), (slave, reg) in config.SENSOR_MAP.items():
            t = config.T_HEATER - 0.5 + random.uniform(-0.3, 0.3)
            _base_temps[(gid, mid)] = t

    readings = []

    for (gid, mid), (slave, reg) in config.SENSOR_MAP.items():
        key = (gid, mid)
        base = _base_temps[key]
        temp = None

        if _current_mode == 'NORMAL':
            temp = base + random.gauss(0, 0.15)
            temp = max(temp, config.T_MOLD_WARNING + 0.5)

        elif _current_mode == 'GRADUAL_DROP':
            decay = _call_counter * 0.03
            temp = base - decay + random.gauss(0, 0.1)
            temp = max(temp, 35.0)

        elif _current_mode == 'SUDDEN_DROP':
            temp = base + random.gauss(0, 0.1)
            if _call_counter == 60:
                temp -= 5.0
                _base_temps[key] = temp
            temp = max(temp, 35.0)

        elif _current_mode == 'NOISY':
            if random.random() < 0.10:
                temp = None
            else:
                temp = base + random.gauss(0, 0.15) + random.uniform(-1.5, 1.5)
                temp = max(temp, 35.0)

        elif _current_mode == 'HEATER_FAIL':
            decay = _call_counter * 0.02
            temp = base - decay + random.gauss(0, 0.2)
            temp = max(temp, 30.0)

        elif _current_mode == 'PUMP_FAIL':
            if _call_counter < 50:
                temp = base + random.gauss(0, 0.15)
            else:
                temp = base - random.uniform(2.0, 4.0) + random.gauss(0, 0.5)
            temp = max(temp, 30.0)

        # Determine status (3 levels)
        if temp is None:
            status    = 'ERREUR'
            deviation = None
        elif temp < config.T_MOLD_CRITICAL:
            status    = 'CRITIQUE'
            deviation = round(temp - config.T_HEATER, 1)
        elif temp < config.T_MOLD_WARNING:
            status    = 'ALERTE'
            deviation = round(temp - config.T_HEATER, 1)
        else:
            status    = 'OK'
            deviation = round(temp - config.T_HEATER, 1)

        readings.append(SensorReading(
            group_id    = gid,
            mold_id     = mid,
            position    = config.POSITION_MAP.get(mid, 'unknown'),
            temperature = round(temp, 1) if temp is not None else None,
            status      = status,
            threshold   = config.T_HEATER,
            deviation   = deviation,
            timestamp   = now,
        ))

    return readings
