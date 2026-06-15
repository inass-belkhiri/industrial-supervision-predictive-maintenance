# tests/run_simulated.py
# Launches the backend with 100% simulated data (Modbus + Flow).
# No hardware required — all 12 temperature sensors + 4 flow sensors are mocked.

import sys
import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
)
log = logging.getLogger(__name__)

# ── Patch imports BEFORE the backend starts ────────────────────────────────────

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

# 1. Patch modbus_manager
import modbus_simulator
import modbus_manager
modbus_manager.read_all_sensors = modbus_simulator.read_all_sensors
log.info("modbus_manager.read_all_sensors → modbus_simulator (mode: NORMAL)")

# 2. Patch FlowSensor
import flow_simulator
flow_simulator.patch_flow_sensor()

# 3. Override config to force simulation-safe settings
import config
config.MODBUS_PORT = '/dev/ttySIMULATED'

# ── Seed InfluxDB with synthetic historical data ──────────────────────────────
try:
    log.info("Seeding InfluxDB with 60 days of synthetic data...")
    import data_generator
    data_generator.inject_historical_data()
    log.info("Historical data injected — Ridge will have data for maintenance predictions")
except Exception as exc:
    log.warning("Could not seed historical data: %s", exc)

# ── Start backend ──────────────────────────────────────────────────────────────

import uvicorn
from main import app

BANNER = f"""
{'=' * 60}
  SUPERVISION THERMIQUE — MODE SIMULATION
{'=' * 60}
  12 capteurs de température simulés
  4  débitmètres YF-S201 simulés
  InfluxDB : {config.INFLUX_URL}
  Backend  : http://{config.WS_HOST}:{config.WS_PORT}
  Frontend : http://localhost:5173 (npm run dev)

  Modes disponibles dans modbus_simulator:
    NORMAL       - températures stables
    GRADUAL_DROP - refroidissement progressif
    SUDDEN_DROP  - chute brutale sur un moule
    NOISY        - normal avec 10% d'erreurs
    HEATER_FAIL  - panne chauffage global
    PUMP_FAIL    - panne pompe + débit bas

  Pour changer de mode:
    from modbus_simulator import set_mode
    set_mode('SUDDEN_DROP')
{'=' * 60}
"""

if __name__ == '__main__':
    print(BANNER)
    log.info("Starting simulated backend...")
    uvicorn.run("main:app", host=config.WS_HOST, port=config.WS_PORT, reload=False)
