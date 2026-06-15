# tests/flow_simulator.py
# Simulates YF-S201 flow sensors for testing (one per heater group).
# Drop-in replacement for flow_sensor.FlowSensor class.
# Mode-dependant flow: call set_mode(mode) to change the flow scenario.

import random
import logging

import config

log = logging.getLogger(__name__)

_simulated_flows = {gid: config.FLOW_DEFAULT_LPM for gid in config.FLOW_SENSOR_PINS}
_FLOW_MODE    = 'NORMAL'
_FLOW_COUNTER = 0


def set_mode(mode: str):
    global _FLOW_MODE, _FLOW_COUNTER, _simulated_flows
    _FLOW_MODE = mode
    _FLOW_COUNTER = 0
    _simulated_flows = {gid: config.FLOW_DEFAULT_LPM for gid in config.FLOW_SENSOR_PINS}
    log.info("Flow simulator mode set to '%s'", mode)


def get_mode() -> str:
    return _FLOW_MODE


def reset_simulated_flows():
    global _simulated_flows
    _simulated_flows = {gid: config.FLOW_DEFAULT_LPM for gid in config.FLOW_SENSOR_PINS}


class SimulatedFlowSensor:
    def __init__(self, pin=None, k_factor=7.5):
        self.pin = pin
        self.k_factor = k_factor
        self.group_id = None
        for gid, p in config.FLOW_SENSOR_PINS.items():
            if p == pin:
                self.group_id = gid
                break
        if self.group_id is None:
            self.group_id = 1
        log.info("SimulatedFlowSensor on pin %s -> group %d", pin, self.group_id)

    def read_lpm(self) -> float:
        global _FLOW_COUNTER
        _FLOW_COUNTER += 1

        gid = self.group_id
        base = _simulated_flows.get(gid, config.FLOW_DEFAULT_LPM)

        if _FLOW_MODE == 'PUMP_FAIL':
            return max(0, 2.0 + random.gauss(0, 0.3))

        if _FLOW_MODE == 'NOISY':
            return max(0, base + random.gauss(0, 3.0))

        if _FLOW_MODE == 'GRADUAL_DROP':
            decay = _FLOW_COUNTER * 0.02
            return max(0, base - decay + random.gauss(0, 0.3))

        return max(0, base + random.gauss(0, 0.3))

    def close(self):
        log.info("SimulatedFlowSensor group %d closed", self.group_id)


def patch_flow_sensor():
    import flow_sensor
    flow_sensor.FlowSensor = SimulatedFlowSensor
    flow_sensor.HAS_GPIO = True
    log.info("flow_sensor.FlowSensor patched with SimulatedFlowSensor")
