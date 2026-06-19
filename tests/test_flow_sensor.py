import sys
import os
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

mock_gpio = MagicMock()
sys.modules['gpiozero'] = mock_gpio

from flow_sensor import FlowSensor
import config


class TestFlowSensor:
    def test_conversion_frequency_to_flow(self):
        sensor = FlowSensor(pin=17, k_factor=7.5)
        sensor.last_read_time = 1000.0
        sensor.pulse_count = 75

        with patch('time.time', return_value=1001.0):
            flow = sensor.read_lpm()

        assert flow == pytest.approx(10.0, abs=0.01)
        assert sensor.pulse_count == 0

    def test_spike_rejection_and_no_hardware(self):
        sensor = FlowSensor(pin=17, k_factor=7.5)
        sensor.last_read_time = 1000.0
        sensor.pulse_count = 500

        with patch('time.time', return_value=1001.0):
            flow = sensor.read_lpm()

        assert flow == config.FLOW_DEFAULT_LPM

        sensor.sensor = None
        flow = sensor.read_lpm()
        assert flow == config.FLOW_DEFAULT_LPM
