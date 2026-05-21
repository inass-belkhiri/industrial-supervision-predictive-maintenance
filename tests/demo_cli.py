import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import requests

BASE_URL = "http://localhost:8001"

MODES = [
    ('1', 'NORMAL',       'all temperatures stable around 44-45°C'),
    ('2', 'GRADUAL_DROP', 'slow temperature decay (-0.03°C per call)'),
    ('3', 'SUDDEN_DROP',  'sudden -2.5°C drop at 60th call'),
    ('4', 'HEATER_FAIL',  'all molds dropping below 42°C (heater failure)'),
    ('5', 'PUMP_FAIL',    'global drop + erratic readings (pump failure)'),
    ('6', 'NOISY',        'normal with 10% random ERREUR readings'),
]


def set_mode(mode: str):
    try:
        resp = requests.post(f"{BASE_URL}/api/sim/mode", json={"mode": mode}, timeout=3)
        if resp.status_code == 200:
            print(f"  ✓ Mode changé : {mode}")
        else:
            data = resp.json()
            print(f"  ✗ Erreur {resp.status_code} : {data.get('detail', resp.text)}")
    except requests.ConnectionError:
        print(f"  ✗ Impossible de se connecter au backend ({BASE_URL})")
    except Exception as e:
        print(f"  ✗ Erreur : {e}")


def auto_sequence():
    modes_seq = [
        ('NORMAL',       2),
        ('GRADUAL_DROP', 2),
        ('SUDDEN_DROP',  1),
        ('HEATER_FAIL',  1),
        ('NORMAL',       0.5),
        ('PUMP_FAIL',    1),
        ('NOISY',        1),
        ('NORMAL',       0),
    ]
    print("\n  Séquence automatique de démonstration :")
    for mode, pause in modes_seq:
        set_mode(mode)
        if pause > 0:
            import time
            time.sleep(pause)
    print("  Terminé.\n")


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def main():
    while True:
        clear_screen()
        print("=" * 60)
        print("  SUPERVISION THERMIQUE — Contrôle de la Simulation")
        print("=" * 60)
        print()
        for key, mode, desc in MODES:
            print(f"  {key}. {mode:<15s}   {desc}")
        print()
        print("  A. Séquence automatique (enchaîne tous les modes)")
        print("  Q. Quitter")
        print()
        choice = input("  Choix : ").strip().upper()

        if choice == 'Q':
            print("  Au revoir.")
            break

        if choice == 'A':
            auto_sequence()
            input("  Appuyez sur Entrée pour continuer...")
            continue

        matched = [m for k, m, d in MODES if k == choice]
        if matched:
            set_mode(matched[0])
            input("  Appuyez sur Entrée pour continuer...")
        else:
            print("  Choix invalide.")
            input("  Appuyez sur Entrée...")

    print()


if __name__ == '__main__':
    main()
