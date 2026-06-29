import sys
import os
import json
from unittest.mock import MagicMock, AsyncMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'ml'))

mock_influx = MagicMock()
mock_influx.init_influxdb = MagicMock()
mock_influx.close_influxdb = MagicMock()
mock_influx.write_sensors = MagicMock()
mock_influx.write_flow = MagicMock()
mock_influx.query_recent = MagicMock(return_value={'temperatures': [], 'flows': [], 'delta_T_calcaires': []})
mock_influx.query_daily_mean_mold = MagicMock(return_value=[])
mock_influx.query_calibration_temp = MagicMock(return_value=None)
sys.modules['influxdb_manager'] = mock_influx

mock_modbus = MagicMock()
mock_modbus.init_modbus = AsyncMock()
mock_modbus.close_modbus = AsyncMock()
mock_modbus.read_all_sensors = AsyncMock(return_value=[])
mock_modbus.read_heater_temp = AsyncMock(return_value=45.0)
sys.modules['modbus_manager'] = mock_modbus

mock_alerting = MagicMock()
mock_alerting.send_alert = MagicMock()
sys.modules['alerting'] = mock_alerting

mock_gpio = MagicMock()
sys.modules['gpiozero'] = mock_gpio

from fastapi.testclient import TestClient

from main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


class TestApiIntegration:
    def test_sim_mode_endpoint(self, client):
        response = client.post("/api/sim/mode", json={"mode": "NORMAL"})
        assert response.status_code in (200, 404)

    def test_websocket_connect(self, client):
        with client.websocket_connect("/ws") as ws:
            data = ws.receive_text()
            payload = json.loads(data)
            assert "sensors" in payload
            assert "diagnostic" in payload
            assert "maintenance" in payload

    def test_websocket_reconnect(self, client):
        with client.websocket_connect("/ws") as ws:
            data = json.loads(ws.receive_text())
            assert "sensors" in data

        with client.websocket_connect("/ws") as ws2:
            data2 = json.loads(ws2.receive_text())
            assert "sensors" in data2
