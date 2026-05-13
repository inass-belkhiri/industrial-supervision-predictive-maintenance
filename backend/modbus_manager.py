# modbus_manager.py
# Reads all 12 temperature sensors via MODBUS RTU over RS485.
# Uses pymodbus with asyncio.  Reads are serialized with a Lock because
# Modbus RTU is half-duplex: only one request/response exchange can be
# in flight at a time on the RS485 bus.  Concurrent tasks caused
# asyncio.InvalidStateError when a late response arrived after its
# Future had already been cancelled by wait_for.
# Returns a list of SensorReading dataclass instances.

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

    The Lock ensures only one Modbus request is on the RS485 bus at a
    time, preventing the InvalidStateError that occurred when pymodbus
    tried to resolve a Future that wait_for had already cancelled.
    """
    if _client is None or _bus_lock is None:
        return None
    try:
        async with _bus_lock:
            result = await asyncio.wait_for(
                _client.read_holding_registers(register, count=1, slave=slave),
                timeout=config.MODBUS_TIMEOUT,
            )
        if result.isError():
            return None
        raw = result.registers[0]
        return raw * config.TEMP_SCALE_FACTOR
    except asyncio.TimeoutError:
        log.debug("MODBUS timeout slave=%d reg=%d", slave, register)
        return None
    except asyncio.InvalidStateError:
        # Safety net: pymodbus late-response race condition
        log.debug("MODBUS late response (InvalidStateError) slave=%d reg=%d", slave, register)
        return None
    except (ModbusException, Exception) as exc:
        log.debug("MODBUS read error slave=%d: %s", slave, exc)
        return None


async def read_all_sensors(calibration_temps: dict) -> List[SensorReading]:
    """
    Read all 12 sensors sequentially (required by the RS485 half-duplex bus).
    calibration_temps: { mold_key: float } — T_mold_jour1 per mold.
    Returns a list of SensorReading, one per sensor.
    """
    now = datetime.now().isoformat(timespec='seconds')

    # Sequential reads: each _read_one acquires the lock internally.
    # asyncio.gather is kept so the event loop stays free between lock
    # acquisitions (other coroutines can run while we wait for the bus).
    keys  = list(config.SENSOR_MAP.keys())
    tasks = [asyncio.create_task(_read_one(slave, reg))
             for (slave, reg) in config.SENSOR_MAP.values()]
    temps = await asyncio.gather(*tasks, return_exceptions=True)

    readings = []
    for (gid, mid), temp_or_exc in zip(keys, temps):
        temp = temp_or_exc if not isinstance(temp_or_exc, Exception) else None
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
