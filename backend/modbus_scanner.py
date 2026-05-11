#!/usr/bin/env python3
"""
modbus_scanner.py — Scan the RS485 bus to discover Modbus slave IDs.
Stop AUTOMATICALLY at --stop (default 12 for this project).

Usage:
    python3 modbus_scanner.py              # scan IDs 1-12
    python3 modbus_scanner.py --stop 247   # scan all
    python3 modbus_scanner.py --baud 19200 # different baudrate
"""

import argparse
import asyncio
import sys

from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

DEFAULT_PORT     = '/dev/ttyUSB0'
DEFAULT_BAUD     = 9600
DEFAULT_TIMEOUT  = 0.8   # increased for reliability

async def scan(port: str, baud: int, start_id: int, stop_id: int):
    client = AsyncModbusSerialClient(
        port=port, baudrate=baud,
        parity='N', stopbits=1, bytesize=8,
        timeout=DEFAULT_TIMEOUT,
    )
    ok = await client.connect()
    if not ok:
        print(f"[ERREUR] Impossible d'ouvrir {port}")
        print("  -> Lancer d'abord : sudo systemctl stop supervision-backend")
        sys.exit(1)

    print(f"\n{'ID':>4}  {'Raw':>6}  {'Temp':>8}  Status")
    print("-" * 40)

    found = []
    for slave_id in range(start_id, stop_id + 1):
        raw  = None
        temp = None
        try:
            result = await client.read_holding_registers(0, count=2, slave=slave_id)
            if result.isError():
                status = "pas de reponse"
            else:
                raw  = result.registers[0]
                temp = raw * 0.1
                status = f"OK  -> {temp:.1f} deg C"
                found.append((slave_id, raw, temp))
        except (ModbusException, Exception) as e:
            status = "ERROR"

        raw_str  = str(raw)  if raw  is not None else "--"
        temp_str = f"{temp:.1f}" if temp is not None else "--"
        print(f"{slave_id:>4}  {raw_str:>6}  {temp_str:>7}C  {status}")

    client.close()

    print("\n" + "=" * 50)
    print(f"Resultat : {len(found)} capteur(s) detecte(s) : IDs = {[f[0] for f in found]}")

    if found:
        print("\n--- SENSOR_MAP a coller dans config.py ---")
        print("SENSOR_MAP = {")
        positions = {1: 'gauche', 2: 'centre', 3: 'droite'}
        for sid, raw, temp in found:
            gid = (sid - 1) // 3 + 1
            pos = (sid - 1) % 3 + 1

            print(f"    ({gid}, {pos}): ({sid}, 0),  "
                  f"# Heater {gid} - {positions.get(pos,pos)} "
                  f"[slave {sid}, {temp:.1f}C detectee]")
        print("}")
    else:
        print("\nAucun capteur detecte.")
        print("Verifications :")
        print("  1. Câble A+ -> A+, B- -> B- (pas inverse)")
        print("  2. Alimentation 12V/24V du capteur")
        print("  3. Baudrate correct (defaut 9600)")
        print("  4. Un seul capteur branche pour le test initial")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',  default=DEFAULT_PORT)
    parser.add_argument('--baud',  type=int, default=DEFAULT_BAUD)
    parser.add_argument('--start', type=int, default=1)
    parser.add_argument('--stop',  type=int, default=12)  # 12 par defaut
    args = parser.parse_args()

    print(f"Scan MODBUS RTU sur {args.port} @ {args.baud} baud")
    print(f"IDs {args.start} a {args.stop}")
    asyncio.run(scan(args.port, args.baud, args.start, args.stop))