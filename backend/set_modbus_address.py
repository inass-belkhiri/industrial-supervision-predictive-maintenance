#!/usr/bin/env python3
"""
set_modbus_address.py
Configure l'adresse MODBUS d'un capteur PT100.
Registre d'adresse : 0x0002 (découvert par scan des registres)

Usage:
    python3 set_modbus_address.py --current 1 --new 2
    python3 set_modbus_address.py --current 1 --new 5
    ... jusqu'à 12
"""

import argparse
import asyncio
import sys
from pymodbus.client import AsyncModbusSerialClient

PORT             = '/dev/ttyUSB0'
BAUD             = 9600
TIMEOUT          = 2.0
ADDRESS_REGISTER = 0x0002
MAX_RETRIES      = 3


async def make_client():
    client = AsyncModbusSerialClient(
        port=PORT, baudrate=BAUD,
        parity='N', stopbits=1, bytesize=8,
        timeout=TIMEOUT,
    )
    ok = await client.connect()
    return client if ok else None


async def read_temp(addr: int):
    """Tente de lire la température à une adresse. Retourne None si échec."""
    client = await make_client()
    if client is None:
        return None
    try:
        r = await client.read_holding_registers(0, count=1, slave=addr)
        if not r.isError():
            return r.registers[0] * 0.1
        return None
    except Exception:
        return None
    finally:
        client.close()


async def write_address(current_addr: int, new_addr: int):
    """Envoie la commande d'écriture. L'exception de redémarrage est ignorée."""
    client = await make_client()
    if client is None:
        return
    try:
        await client.write_register(ADDRESS_REGISTER, new_addr, slave=current_addr)
    except Exception:
        # Exception attendue : le module redémarre avec la nouvelle adresse
        # avant que pymodbus reçoive une réponse valide. L'écriture a bien eu lieu.
        pass
    finally:
        client.close()


async def set_address(current_addr: int, new_addr: int):

    # ── Étape 1 : Vérifier que le capteur est présent ───────────────────────
    print(f"\nRecherche du capteur a l'adresse {current_addr}...")
    temp = await read_temp(current_addr)

    if temp is None:
        # Peut-être qu'une tentative précédente a déjà écrit new_addr
        print(f"  Aucun capteur a {current_addr} — verification a {new_addr}...")
        temp_new = await read_temp(new_addr)
        if temp_new is not None:
            print(f"  [INFO] Capteur deja a l'adresse {new_addr} : {temp_new:.1f} deg C")
            print(f"  -> Adresse correcte, rien a faire.")
            _print_next(new_addr)
            return
        else:
            print(f"[ERREUR] Capteur introuvable aux adresses {current_addr} et {new_addr}")
            print(f"  -> Verifier le cablage A+/B-")
            print(f"  -> Ou scanner : python3 modbus_scanner.py --stop 247")
            sys.exit(1)

    print(f"  Capteur detecte : {temp:.1f} deg C")

    # ── Étape 2 : Boucle d'écriture avec vérification ───────────────────────
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\nChangement d'adresse : {current_addr} -> {new_addr}  (tentative {attempt}/{MAX_RETRIES})")

        await write_address(current_addr, new_addr)
        print(f"  Commande envoyee. Attente redemarrage (4s)...")
        await asyncio.sleep(4)

        # Vérifier la nouvelle adresse
        temp_new = await read_temp(new_addr)
        if temp_new is not None:
            print(f"\n[OK] Capteur repond a l'adresse {new_addr} : {temp_new:.1f} deg C")
            _print_next(new_addr)
            return

        await asyncio.sleep(1)

        # Vérifier si l'ancienne adresse répond encore (write raté)
        temp_old = await read_temp(current_addr)
        if temp_old is not None:
            print(f"  [WARN] Write echoue — capteur encore a {current_addr} : {temp_old:.1f} deg C")
            if attempt < MAX_RETRIES:
                print(f"  Nouvelle tentative dans 2s...")
                await asyncio.sleep(2)
            continue

        # Ni l'une ni l'autre — module peut-être encore en redémarrage
        print(f"  [WARN] Capteur non trouve aux adresses {current_addr} et {new_addr}. Attente 3s...")
        await asyncio.sleep(3)
        temp_new2 = await read_temp(new_addr)
        if temp_new2 is not None:
            print(f"\n[OK] Capteur repond a l'adresse {new_addr} : {temp_new2:.1f} deg C")
            _print_next(new_addr)
            return

    # ── Échec après MAX_RETRIES ──────────────────────────────────────────────
    print(f"\n[ERREUR] Echec apres {MAX_RETRIES} tentatives.")
    print(f"  -> Scanner pour trouver l'adresse reelle du capteur :")
    print(f"  -> python3 modbus_scanner.py --stop 247")
    sys.exit(1)


def _print_next(new_addr: int):
    print(f"\n  -> Debrancher ce capteur (A+ et B- uniquement)")
    print(f"  -> Brancher le capteur suivant seul sur A+/B-")
    if new_addr < 12:
        print(f"  -> Commande : python3 set_modbus_address.py --current 1 --new {new_addr + 1}")
    else:
        print(f"  -> Tous les capteurs configures !")
        print(f"  -> Rebrancher tous les A+ et B-")
        print(f"  -> python3 modbus_scanner.py")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--current', type=int, required=True,
                        help='Adresse actuelle du capteur branche (1 par defaut usine)')
    parser.add_argument('--new', type=int, required=True,
                        help='Nouvelle adresse (2 a 12)')
    args = parser.parse_args()

    if not (1 <= args.current <= 247):
        print("[ERREUR] --current doit etre entre 1 et 247")
        sys.exit(1)
    if not (1 <= args.new <= 247):
        print("[ERREUR] --new doit etre entre 1 et 247")
        sys.exit(1)

    asyncio.run(set_address(args.current, args.new))
