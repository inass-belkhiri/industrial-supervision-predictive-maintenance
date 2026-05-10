#!/usr/bin/env python3
"""
modbus_scanner.py — Scan the RS485 bus to discover Modbus slave IDs and read
holding register 0 from each. Run this ONCE to build your SENSOR_MAP in config.py.

Usage:
    python modbus_scanner.py              # scan IDs 1-247 at 9600 baud
    python modbus_scanner.py --baud 19200  # different baudrate
    python modbus_scanner.py --start 1 --stop 50  # custom range

Requires: pymodbus (already in your venv)
"""

import argparse
import asyncio
import sys

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

DEFAULT_PORT     = '/dev/ttyUSB0'
DEFAULT_BAUD     = 9600
DEFAULT_PARITY   = 'N'
DEFAULT_STOPBITS = 1
DEFAULT_BYTESIZE = 8
DEFAULT_TIMEOUT  = 0.5

async def scan(port: str, baud: int, start_id: int, stop_id: int):
    client = AsyncModbusSerialClient(
        port=port, baudrate=baud, parity=DEFAULT_PARITY,
        stopbits=DEFAULT_STOPBITS, bytesize=DEFAULT_BYTESIZE,
        timeout=DEFAULT_TIMEOUT,
    )
    ok = await client.connect()
    if not ok:
        print(f"[ERREUR] Impossible d'ouvrir {port}")
        sys.exit(1)

    print(f"\n{'ID':>4}  {'Value':>8}  {'Hex':>8}  {'Status'}")
    print("-" * 42)

    found = []
    for slave_id in range(start_id, stop_id + 1):
        try:
            result = await client.read_holding_registers(0, count=1, slave=slave_id)
            if result.isError():
                status = "NO RESPONSE"
            else:
                raw = result.registers[0]
                temp = raw * 0.1  # assuming TEMP_SCALE_FACTOR = 0.1
                status = f"OK  ({temp:.1f} deg C)"
                found.append((slave_id, raw, temp))
        except (ModbusException, Exception):
            status = "ERROR"

        print(f"{slave_id:>4}  {raw if 'OK' in status else '--':>8}  "
              f"{hex(raw) if 'OK' in status else '--':>8}  {status}")

    await client.close()

    print("\n" + "=" * 50)
    print(f"Found {len(found)} responding slaves: {[f[0] for f in found]}")

    if found:
        print("\nSENSOR_MAP for config.py:")
        print("SENSOR_MAP = {")
        for idx, (sid, raw, temp) in enumerate(found, 1):
            gid = (idx - 1) // 3 + 1
            mid = ((idx - 1) % 3) + 1
            print(f"    ({gid}, {mid}): ({sid}, 0),")
        print("}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scan Modbus RTU bus for sensor IDs')
    parser.add_argument('--port',    default=DEFAULT_PORT,   help='Serial port (default: /dev/ttyUSB0)')
    parser.add_argument('--baud',    type=int, default=DEFAULT_BAUD, help='Baudrate (default: 9600)')
    parser.add_argument('--start',   type=int, default=1,    help='First slave ID to scan (default: 1)')
    parser.add_argument('--stop',    type=int, default=247,  help='Last slave ID to scan (default: 247)')
    args = parser.parse_args()

    print(f"Scanning Modbus RTU on {args.port} @ {args.baud} baud")
    print(f"Slave IDs {args.start} to {args.stop}")
    asyncio.run(scan(args.port, args.baud, args.start, args.stop))
