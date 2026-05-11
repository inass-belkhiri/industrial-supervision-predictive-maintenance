#!/usr/bin/env python3
"""
set_modbus_address.py
Configure l'adresse MODBUS d'un capteur PT100.
Registre d'adresse : 0x0002 (découvert par scan des registres)

Usage:
    python3 set_modbus_address.py --current 1 --new 2
    python3 set_modbus_address.py --current 1 --new 3
    ... jusqu'à 12
"""

import argparse
import asyncio
import sys
from pymodbus.client import AsyncModbusSerialClient

PORT    = '/dev/ttyUSB0'
BAUD    = 9600
TIMEOUT = 2.0
ADDRESS_REGISTER = 0x0002  # registre correct pour ces modules

async def make_client():
    client = AsyncModbusSerialClient(
        port=PORT, baudrate=BAUD,
        parity='N', stopbits=1, bytesize=8,
        timeout=TIMEOUT,
    )
    ok = await client.connect()
    return client if ok else None

async def set_address(current_addr: int, new_addr: int):

    # 1. Détecter le capteur
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

    # 2. Ecrire nouvelle adresse dans registre 0x0002
    print(f"\nChangement d'adresse : {current_addr} -> {new_addr}")
    res = await client.write_register(ADDRESS_REGISTER, new_addr, slave=current_addr)
    client.close()

    if res.isError():
        print("[ERREUR] Ecriture echouee")
        sys.exit(1)

    print(f"  Registre 0x{ADDRESS_REGISTER:04X} ecrit avec succes")

    # 3. Attendre redemarrage
    print("  Attente redemarrage (4 secondes)...")
    await asyncio.sleep(4)

    # 4. Nouvelle connexion pour verification
    client2 = await make_client()
    if client2 is None:
        print(f"[OK] Adresse ecrite - verifier avec : python3 modbus_scanner.py --stop {new_addr}")
        sys.exit(0)

    r = await client2.read_holding_registers(0, count=1, slave=new_addr)
    client2.close()

    if not r.isError():
        temp2 = r.registers[0] * 0.1
        print(f"\n[OK] Capteur repond a l'adresse {new_addr} : {temp2:.1f} deg C")
        print(f"\n  -> Debrancher ce capteur (A+ et B-)")
        print(f"  -> Brancher le suivant")
        if new_addr < 12:
            print(f"  -> Commande : python3 set_modbus_address.py --current 1 --new {new_addr+1}")
        else:
            print(f"  -> Tous les capteurs configures !")
            print(f"  -> Rebrancher tous les A+ et B-")
            print(f"  -> python3 modbus_scanner.py")
    else:
        print(f"\n[OK] Adresse ecrite (timeout verification normal)")
        print(f"  -> Verifier : python3 modbus_scanner.py --stop {new_addr}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--current', type=int, required=True,
                        help='Adresse actuelle (1 par defaut usine)')
    parser.add_argument('--new', type=int, required=True,
                        help='Nouvelle adresse (2 a 12)')
    args = parser.parse_args()
    asyncio.run(set_address(args.current, args.new))
