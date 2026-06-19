import pytest
from datetime import datetime
from modbus_manager import SensorReading


def test_sensor_reading_creation():
    r = SensorReading(
        group_id=1, mold_id=1, position='gauche',
        temperature=43.5, status='OK', threshold=45.0,
        deviation=-1.5, timestamp='2025-05-26T10:00:00'
    )
    assert r.group_id == 1
    assert r.mold_id == 1
    assert r.position == 'gauche'
    assert r.temperature == 43.5
    assert r.status == 'OK'
    assert r.deviation == -1.5


def test_sensor_reading_none_temperature():
    r = SensorReading(
        group_id=2, mold_id=2, position='centre',
        temperature=None, status='ERREUR', threshold=45.0,
        deviation=None, timestamp='2025-05-26T10:00:00'
    )
    assert r.temperature is None
    assert r.status == 'ERREUR'
    assert r.deviation is None


def test_sensor_reading_repr():
    r = SensorReading(1, 1, 'gauche', 43.5, 'OK', 45.0, -1.5, '2025-05-26T10:00:00')
    s = repr(r)
    assert 'SensorReading' in s
    assert '43.5' in s
    assert 'OK' in s
