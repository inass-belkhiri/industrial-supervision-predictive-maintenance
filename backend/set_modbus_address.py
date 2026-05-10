#!/usr/bin/env python3
"""
set_modbus_address.py
Configure l'adresse MODBUS d'un capteur PT100.
Brancher UN SEUL capteur à la fois sur le bus RS485.

Usage:
    python3 set_modbus_address.py --current 1 --new 2
    python3 set_modbus_address.py --current 1 --new 3
    ... jusqu'à 12
"""

import argparse
import asyncio
import sys
from pymodbus.client import AsyncModbusSerialClient

PORT     = '/dev/ttyUSB0'
BAUD     = 9600
PARITY   = 'N'
STOPBITS = 1
BYTESIZE = 8
TIMEOUT  = 2.0

# Registres connus pour les modules PT100 MODBUS XY-MD02 / similaires
# Le registre d'adresse varie selon le fabricant — on essaie les plus courants
ADDRESS_REGISTERS = [
    0x0101,   # XY-MD02, SHT20 MODBUS
    0x00FF,   # variante
    0x0010,   # autre fabricant
    0x0014,   # autre
]

async def read_temp(client, slave_id):
    """Lit la temperature pour confirmer la communication."""
    result = await client.read_holding_registers(0, count=1, slave=slave_id)
    if result.isError():
        return None
    return result.registers[0] * 0.1

async def set_address(current_addr: int, new_addr: int):
    client = AsyncModbusSerialClient(
        port=PORT, baudrate=BAUD, parity=PARITY,
        stopbits=STOPBITS, bytesize=BYTESIZE, timeout=TIMEOUT,
    )
    ok = await client.connect()
    if not ok:
        print(f"[ERREUR] Impossible d'ouvrir {PORT}")
        print("  -> sudo systemctl stop supervision-backend")
        sys.exit(1)

    print(f"\nRecherche du capteur a l'adresse {current_addr}...")

    # Verify current address responds
    temp = await read_temp(client, current_addr)
    if temp is None:
        print(f"[ERREUR] Aucun capteur ne repond a l'adresse {current_addr}")
        print("  Verifier : capteur branche ? adresse correcte ?")
        client.close()
        sys.exit(1)

    print(f"  Capteur detecte : {temp:.1f} deg C")
    print(f"\nChangement d'adresse : {current_addr} -> {new_addr}")

    # Try each known address register
    success = False
    for reg in ADDRESS_REGISTERS:
        try:
            result = await client.write_register(reg, new_addr, slave=current_addr)
            if not result.isError():
                print(f"  Registre 0x{reg:04X} ecrit avec succes")
                success = True
                break
            else:
                print(f"  Registre 0x{reg:04X} : echec (normal si mauvais registre)")
        except Exception as e:
            print(f"  Registre 0x{reg:04X} : exception {e}")

    if not success:
        print("\n[ATTENTION] Aucun registre standard n'a accepte l'ecriture.")
        print("  Ce module utilise peut-etre un logiciel PC proprietaire.")
        print("  Consulter la datasheet du module pour le registre d'adresse.")
        client.close()
        sys.exit(1)

    # Wait for reboot
    print("\nAttente redemarrage capteur (2 secondes)...")
    await asyncio.sleep(2)

    # Verify new address works
    temp2 = await read_temp(client, new_addr)
    if temp2 is not None:
        print(f"\n[OK] Capteur repond maintenant a l'adresse {new_addr}")
        print(f"     Temperature : {temp2:.1f} deg C")
        print(f"\n  Debrancher ce capteur et brancher le suivant.")
        print(f"  Commande suivante : python3 set_modbus_address.py --current 1 --new {new_addr + 1}")
    else:
        print(f"\n[ATTENTION] Le capteur ne repond pas encore a {new_addr}")
        print("  Essayer de relancer le scanner pour confirmer.")

    client.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--current', type=int, required=True,
                        help='Adresse actuelle du capteur (probablement 1)')
    parser.add_argument('--new',     type=int, required=True,
                        help='Nouvelle adresse a assigner (2 a 12)')
    args = parser.parse_args()

    if not (1 <= args.new <= 247):
        print("[ERREUR] L'adresse doit etre entre 1 et 247")
        sys.exit(1)

    asyncio.run(set_address(args.current, args.new))
