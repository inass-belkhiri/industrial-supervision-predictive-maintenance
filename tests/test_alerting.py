import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import config
import alerting
import influxdb_manager as influx


def get_affected_molds():
    """Lit les dernières températures depuis InfluxDB et retourne
    (liste_moules_affectes, pire_status, températures_par_moule)."""
    data = influx.query_recent(minutes=5)

    latest_per_mold = {}
    for entry in data['temperatures']:
        key = (entry['group'], entry['mold'])
        ts  = entry['time']
        if key not in latest_per_mold or ts > latest_per_mold[key]['time']:
            latest_per_mold[key] = entry

    affected   = []
    temps      = {}
    worst_status = 'OK'

    for (g, m), entry in latest_per_mold.items():
        t = entry['value']
        temps[int(m)] = t
        if t < config.T_MOLD_CRITICAL:
            affected.append(int(m))
            worst_status = 'CRITIQUE'
        elif t < config.T_MOLD_WARNING:
            affected.append(int(m))
            if worst_status != 'CRITIQUE':
                worst_status = 'ALERTE'

    return affected, worst_status, temps


def main():
    if 'ton_token' in config.TELEGRAM_BOT_TOKEN or 'YOUR_BOT' in config.TELEGRAM_BOT_TOKEN:
        print("[ERREUR] TELEGRAM_BOT_TOKEN est encore un placeholder dans config.py")
        return

    influx.init_influxdb()

    affected, worst_status, temps = get_affected_molds()

    print("=" * 50)
    print("TEST ALERTES - Telegram & Email")
    print("=" * 50)
    print(f"\nTempératures actuelles :")
    for mid, t in sorted(temps.items()):
        print(f"  Moule {mid}: {t:.1f}°C")
    print(f"\nMoules affectés : {affected}")
    print(f"Pire statut      : {worst_status}")
    print("-" * 50)

    if not affected:
        print("Aucun moule en dessous des seuils. Envoi d'un test WARNING.")
        alerting.send_alert(
            severity='WARNING',
            cause='Modèles ML pas encore entraînés',
            confidence=None,
            actions=["Aucun moule en dessous des seuils - test uniquement"],
            amdec_criticite=None,
            amdec_priorite=None,
            affected_molds=[],
        )
    else:
        severity_map = {'CRITIQUE': 'CRITICAL', 'ALERTE': 'WARNING', 'OK': 'WARNING'}
        alerting.send_alert(
            severity=severity_map.get(worst_status, 'WARNING'),
            cause='Modèles ML pas encore entraînés',
            confidence=None,
            actions=[
                "Test d'alerte - Modèles ML pas encore entraînés",
                "Vérifier les température manuellement",
            ],
            amdec_criticite=None,
            amdec_priorite=None,
            affected_molds=affected,
        )

    print("\nTest envoyé - vérifie Telegram et Email")
    print("=" * 50)


if __name__ == '__main__':
    main()
