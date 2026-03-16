# modbus_manager.py
# Reads all 12 temperature sensors via MODBUS RTU over RS485.
# Uses pymodbus with asyncio for non-blocking parallel reads.
# Returns a list of SensorReading dataclass instances.

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

import config

log = logging.getLogger(__name__)


@dataclass
class SensorReading:
    group_id    : int
    mold_id     : int
    position    : str
    temperature : Optional[float]
    status      : str        # "OK" | "ALERTE" | "ERREUR"
    threshold   : float
    deviation   : Optional[float]
    timestamp   : str


_client: Optional[AsyncModbusSerialClient] = None


async def init_modbus() -> bool:
    """Open the MODBUS serial connection. Returns True on success."""
    global _client
    _client = AsyncModbusSerialClient(
        port     = config.MODBUS_PORT,
        baudrate = config.MODBUS_BAUDRATE,
        parity   = config.MODBUS_PARITY,
        stopbits = config.MODBUS_STOPBITS,
        bytesize = config.MODBUS_BYTESIZE,
        timeout  = config.MODBUS_TIMEOUT,
    )
    connected = await _client.connect()
    if connected:
        log.info("MODBUS connection established on %s", config.MODBUS_PORT)
    else:
        log.error("MODBUS connection failed on %s", config.MODBUS_PORT)
    return connected


async def _read_one(slave: int, register: int) -> Optional[float]:
    """Read a single holding register and return the temperature in degrees C."""
    if _client is None:
        return None
    try:
        result = await _client.read_holding_registers(register, count=1, slave=slave)
        if result.isError():
            return None
        raw = result.registers[0]
        return raw * config.TEMP_SCALE_FACTOR
    except (ModbusException, Exception) as exc:
        log.debug("MODBUS read error slave=%d: %s", slave, exc)
        return None


async def read_all_sensors(calibration_temps: dict) -> List[SensorReading]:
    """
    Read all 12 sensors concurrently.
    calibration_temps: { mold_key: float } — T_mold_jour1 per mold.
    Returns a list of SensorReading, one per sensor.
    """
    now = datetime.now().isoformat(timespec='seconds')

    # Build coroutines for all sensors
    tasks = {}
    for (gid, mid), (slave, reg) in config.SENSOR_MAP.items():
        tasks[(gid, mid)] = asyncio.create_task(_read_one(slave, reg))

    # Await all in parallel
    await asyncio.gather(*tasks.values(), return_exceptions=True)

    readings = []
    for (gid, mid), task in tasks.items():
        temp = task.result() if not isinstance(task.result(), Exception) else None
        pos  = config.POSITION_MAP.get(mid, 'unknown')

        if temp is None:
            status    = 'ERREUR'
            deviation = None
        elif temp < config.T_MOLD_CRITICAL:
            status    = 'ALERTE'
            deviation = round(temp - config.T_HEATER, 3)
        else:
            status    = 'OK'
            deviation = round(temp - config.T_HEATER, 3)

        readings.append(SensorReading(
            group_id    = gid,
            mold_id     = mid,
            position    = pos,
            temperature = round(temp, 2) if temp is not None else None,
            status      = status,
            threshold   = config.T_HEATER,
            deviation   = deviation,
            timestamp   = now,
        ))

    return readings


async def close_modbus():
    """Close the MODBUS connection cleanly."""
    global _client
    if _client:
        _client.close()
        _client = None
        log.info("MODBUS connection closed")
