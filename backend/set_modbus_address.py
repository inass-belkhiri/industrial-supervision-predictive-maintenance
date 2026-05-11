#!/usr/bin/env python3
"""
"""

import argparse
import asyncio
import sys
from pymodbus.client import AsyncModbusSerialClient
from pymodbus.exceptions import ModbusException

PORT = '/dev/ttyUSB0'
BAUD = 9600
TIMEOUT = 2.0
ADDR_REG = 0x0002
MAX_RETRIES = 3
REBOOT_WAIT = 5   # secondes après écriture

async def make_client():
    client = AsyncModbusSerialClient(
        port=PORT, baudrate=BAUD,
        parity='N', stopbits=1, bytesize=8,
        timeout=TIMEOUT
    )
    if await client.connect():
        return client
    return None

async def read_temp_and_addr(slave_id):
    """Retourne (température, adresse_lue) ou (None, None) si échec."""
    client = await make_client()
    if not client:
        return None, None
    try:
        # Lecture registre 0 = température, registre 2 = adresse (optionnel)
        rr = await client.read_holding_registers(0, count=3, slave=slave_id)
        if rr.isError():
            return None, None
        temp = rr.registers[0] * 0.1 if len(rr.registers) > 0 else None
        addr_read = rr.registers[2] if len(rr.registers) > 2 else None
        return temp, addr_read
    except ModbusException:
        return None, None
    finally:
        client.close()

async def write_address(current, new):
    """Écrit la nouvelle adresse et attend le redémarrage. Retourne True si l'écriture semble réussie."""
    client = await make_client()
    if not client:
        return False
    try:
        # On écrit avec un timeout réduit car la réponse sera interrompue
        await asyncio.wait_for(
            client.write_register(ADDR_REG, new, slave=current),
            timeout=1.0
        )
        # Si on arrive ici, c'est que l'écriture a été confirmée (rare)
        return True
    except (asyncio.TimeoutError, ModbusException, Exception):
        # La plupart du temps, on aura une exception car le capteur redémarre.
        # On considère que l'écriture a quand même eu lieu.
        return True
    finally:
        client.close()

async def set_address(current, new):
    print(f"\n=== Changement d'adresse : {current} → {new} ===")

    # 1. Vérifier présence à l'ancienne adresse
    temp_old, _ = await read_temp_and_addr(current)
    if temp_old is None:
        # Peut-être déjà changé ?
        temp_new, _ = await read_temp_and_addr(new)
        if temp_new is not None:
            print(f"[INFO] Le capteur répond déjà à {new} : {temp_new:.1f}°C. Rien à faire.")
            return True
        print(f"[ERREUR] Aucun capteur trouvé à {current} ni à {new}.")
        print("  → Vérifiez le câblage ou lancez un scanner.")
        return False

    print(f"Capteur trouvé à {current} – température {temp_old:.1f}°C.")

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\nTentative {attempt}/{MAX_RETRIES} : écriture de {new} dans registre {hex(ADDR_REG)}...")
        success = await write_address(current, new)
        if not success:
            print("  Échec de l'envoi de la commande.")
            continue

        print(f"  Attente {REBOOT_WAIT} secondes pour redémarrage...")
        await asyncio.sleep(REBOOT_WAIT)

        # Vérifier nouvelle adresse
        temp_new, addr_read = await read_temp_and_addr(new)
        if temp_new is not None:
            # Vérifier que ce n'est pas un autre capteur (optionnel)
            print(f"[OK] Capteur répond à {new} : {temp_new:.1f}°C.")
            # Vérifier que l'ancienne adresse ne répond plus
            old_still_alive, _ = await read_temp_and_addr(current)
            if old_still_alive is None:
                print(f"[OK] L'ancienne adresse {current} ne répond plus – changement réussi.")
                return True
            else:
                print(f"[WARN] L'ancienne adresse {current} répond encore ({old_still_alive:.1f}°C) – conflit.")
                # Peut-être deux capteurs branchés ?
                return False
        else:
            print(f"  Aucune réponse à {new} après {REBOOT_WAIT}s.")

        # Vérifier si l'ancienne adresse est toujours là
        temp_old_again, _ = await read_temp_and_addr(current)
        if temp_old_again is not None:
            print(f"  L'ancienne adresse {current} répond toujours ({temp_old_again:.1f}°C). Nouvel essai...")
            await asyncio.sleep(2)
            continue
        else:
            # Ni ancienne ni nouvelle – capteur en train de redémarrer ? Attendre plus
            print("  Aucune réponse ni à l'ancienne ni à la nouvelle adresse. Attente supplémentaire...")
            await asyncio.sleep(3)
            temp_new2, _ = await read_temp_and_addr(new)
            if temp_new2 is not None:
                print(f"[OK] Capteur répond à {new} après délai : {temp_new2:.1f}°C.")
                return True

    print(f"\n[ERREUR] Impossible de changer l'adresse après {MAX_RETRIES} tentatives.")
    print("  → Suggestions :")
    print("     1) Vérifiez que le capteur est seul sur le bus.")
    print("     2) Augmentez REBOOT_WAIT (certains capteurs mettent plus de temps).")
    print("     3) Utilisez le scanner pour trouver l'adresse actuelle :")
    print("        python3 modbus_scanner.py --stop 247")
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--current', type=int, required=True)
    parser.add_argument('--new', type=int, required=True)
    args = parser.parse_args()
    if not (1 <= args.current <= 247 and 1 <= args.new <= 247):
        print("Erreur : adresse hors plage 1-247")
        sys.exit(1)
    result = asyncio.run(set_address(args.current, args.new))
    sys.exit(0 if result else 1)

if __name__ == '__main__':
    main()