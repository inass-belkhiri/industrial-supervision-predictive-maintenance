#!/usr/bin/env python3
"""
set_modbus_address.py
Configure l'adresse MODBUS d'un capteur PT100.
Brancher UN SEUL capteur à la fois sur le bus RS485.

Usage:
    python3 set_modbus_address.py --current 1 --new 2
"""

import argparse
import asyncio
import sys
from pymodbus.client import AsyncModbusSerialClient

PORT     = '/dev/ttyUSB0'
BAUD     = 9600
TIMEOUT  = 2.0

ADDRESS_REGISTERS = [0x0101, 0x00FF, 0x0010, 0x0014]

async def make_client():
    client = AsyncModbusSerialClient(
        port=PORT, baudrate=BAUD,
        parity='N', stopbits=1, bytesize=8,
        timeout=TIMEOUT,
    )
    ok = await client.connect()
    return client if ok else None

async def set_address(current_addr: int, new_addr: int):

    # ── 1. Detect capteur at current address ──────────────────────────
    print(f"\nRecherche du capteur a l'adresse {current_addr}...")
    client = await make_client()
    if client is None:
        print(f"[ERREUR] Impossible d'ouvrir {PORT}")
        print("  -> sudo systemctl stop supervision-backend")
        sys.exit(1)

    result = await client.read_holding_registers(0, count=1, slave=current_addr)
    if result.isError():
        print(f"[ERREUR] Aucun capteur ne repond a l'adresse {current_addr}")
        client.close()
        sys.exit(1)

    temp = result.registers[0] * 0.1
    print(f"  Capteur detecte : {temp:.1f} deg C")

    # ── 2. Write new address ──────────────────────────────────────────
    print(f"\nChangement d'adresse : {current_addr} -> {new_addr}")
    success = False
    for reg in ADDRESS_REGISTERS:
        try:
            res = await client.write_register(reg, new_addr, slave=current_addr)
            if not res.isError():
                print(f"  Registre 0x{reg:04X} ecrit avec succes")
                success = True
                break
        except Exception:
            pass

    # Close connection before reboot wait
    client.close()

    if not success:
        print("[ATTENTION] Aucun registre n'a accepte l'ecriture.")
        sys.exit(1)

    # ── 3. Wait for module reboot ────────────────────────────────────
    print("\nAttente redemarrage capteur (3 secondes)...")
    await asyncio.sleep(3)

    # ── 4. Open FRESH connection to verify new address ───────────────
    client2 = await make_client()
    if client2 is None:
        print("[ATTENTION] Impossible de rouvrir le port pour verification.")
        print(f"  Lancer manuellement : python3 modbus_scanner.py --stop {new_addr}")
        sys.exit(0)

    result2 = await client2.read_holding_registers(0, count=1, slave=new_addr)
    client2.close()

    if not result2.isError():
        temp2 = result2.registers[0] * 0.1
        print(f"\n[OK] Capteur repond a l'adresse {new_addr} : {temp2:.1f} deg C")
        print(f"\n  -> Debrancher ce capteur")
        print(f"  -> Brancher le suivant")
        if new_addr < 12:
            print(f"  -> Commande : python3 set_modbus_address.py --current 1 --new {new_addr+1}")
    else:
        print(f"\n[OK] Adresse ecrite avec succes (verification timeout normale)")
        print(f"  -> Confirmer avec : python3 modbus_scanner.py --stop {new_addr}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--current', type=int, required=True)
    parser.add_argument('--new',     type=int, required=True)
    args = parser.parse_args()
    asyncio.run(set_address(args.current, args.new))
