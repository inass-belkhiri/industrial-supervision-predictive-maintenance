# tests/flow_simulator.py
# Simulates 4 YF-S201 flow sensors (one per heater group) for testing.
# Drop-in replacement for flow_sensor.FlowSensor class

import random
import time
import logging

import config

log = logging.getLogger(__name__)

_simulated_flows = {
    1: config.FLOW_DEFAULT_LPM,
    2: config.FLOW_DEFAULT_LPM,
    3: config.FLOW_DEFAULT_LPM,
    4: config.FLOW_DEFAULT_LPM,
}

_sim_call_count = 0


def reset_simulated_flows():
    global _simulated_flows, _sim_call_count
    _simulated_flows = {gid: config.FLOW_DEFAULT_LPM for gid in config.FLOW_SENSOR_PINS}
    _sim_call_count = 0


class SimulatedFlowSensor:
    def __init__(self, pin=None, k_factor=7.5):
        self.pin = pin
        self.k_factor = k_factor
        # Assign a group_id based on pin -> reverse lookup FLOW_SENSOR_PINS
        self.group_id = None
        for gid, p in config.FLOW_SENSOR_PINS.items():
            if p == pin:
                self.group_id = gid
                break
        if self.group_id is None:
            self.group_id = 1  # fallback
        log.info("SimulatedFlowSensor on pin %s -> group %d", pin, self.group_id)

    def read_lpm(self) -> float:
        global _sim_call_count
        _sim_call_count += 1

        gid = self.group_id
        base = _simulated_flows.get(gid, config.FLOW_DEFAULT_LPM)

        # Normal: slight gaussian variation around base
        if _sim_call_count < 200:
            return max(0, base + random.gauss(0, 0.3))

        # After 200 calls: simulate pump failure on group 3
        if gid == 3 and _sim_call_count > 200:
            return max(0, 2.0 + random.gauss(0, 0.5))

        # After 400 calls: simulate recovery
        if gid == 3 and _sim_call_count > 400:
            return max(0, base + random.gauss(0, 0.5))

        return max(0, base + random.gauss(0, 0.3))

    def close(self):
        log.info("SimulatedFlowSensor group %d closed", self.group_id)


# Patch: replace FlowSensor in flow_sensor module at import time
def patch_flow_sensor():
    import flow_sensor
    flow_sensor.FlowSensor = SimulatedFlowSensor
    flow_sensor.HAS_GPIO = True
    log.info("flow_sensor.FlowSensor patched with SimulatedFlowSensor")
