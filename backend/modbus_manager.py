# modbus_manager.py
# Reads all temperature sensors via MODBUS RTU over RS485.
# Uses pymodbus with asyncio. Reads are strictly sequential because
# Modbus RTU is half-duplex: only one request/response exchange can be
# in flight at a time on the RS485 bus.
#
# FIX: replaced asyncio.gather + wait_for with a pure sequential for-loop.
# gather was creating all tasks simultaneously; when wait_for cancelled a
# timed-out Future, pymodbus still resolved it later → InvalidStateError
# → WebSocket ECONNRESET on the frontend.

import asyncio
import logging
from dataclasses import dataclass
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


_client  : Optional[AsyncModbusSerialClient] = None
_bus_lock: Optional[asyncio.Lock]            = None   # one request at a time on RS485


async def init_modbus() -> bool:
    """Open the MODBUS serial connection. Returns True on success."""
    global _client, _bus_lock
    _bus_lock = asyncio.Lock()
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
    """
    Read a single holding register and return the temperature in degrees C.

    Uses pymodbus's built-in timeout (config.MODBUS_TIMEOUT) rather than
    asyncio.wait_for — wait_for cancels the underlying pymodbus future,
    corrupting the client state and breaking all subsequent reads.
    """
    if _client is None or _bus_lock is None:
        return None
    try:
        async with _bus_lock:
            result = await _client.read_holding_registers(
                register, count=1, slave=slave
            )
        if result.isError():
            return None
        raw = result.registers[0]
        return raw * config.TEMP_SCALE_FACTOR
    except asyncio.InvalidStateError:
        return None
    except asyncio.TimeoutError:
        return None
    except (ModbusException, Exception):
        return None


async def read_all_sensors(calibration_temps: dict) -> List[SensorReading]:
    """
    Read all sensors strictly sequentially (required by RS485 half-duplex).

    FIX: replaced asyncio.gather with a plain for-loop.
    gather launched all coroutines concurrently; they piled up on the Lock
    and wait_for timeouts caused InvalidStateError races in pymodbus.
    A sequential for-loop is correct, safe, and fast enough for <= 12 sensors
    at 9600 baud (each read takes ~100 ms max including timeout).
    """
    now      = datetime.now().isoformat(timespec='seconds')
    readings = []

    for (gid, mid), (slave, reg) in zip(
        config.SENSOR_MAP.keys(),
        config.SENSOR_MAP.values()
    ):
        temp = await _read_one(slave, reg)
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

    # If ALL sensors failed, try to reconnect Modbus (max once per 30s)
    if readings and all(r.temperature is None for r in readings):
        now_ts = datetime.now().timestamp()
        elapsed = now_ts - getattr(read_all_sensors, '_last_reconnect', 0)
        if elapsed > 30:
            read_all_sensors._last_reconnect = now_ts
            log.warning("All sensors returned None — attempting Modbus reconnection")
            await close_modbus()
            await init_modbus()
        else:
            log.debug("All sensors None, reconnect debounced (%.0fs since last)", elapsed)

    return readings


async def close_modbus():
    """Close the MODBUS connection cleanly."""
    global _client
    if _client:
        _client.close()
        _client = None
        log.info("MODBUS connection closed")
