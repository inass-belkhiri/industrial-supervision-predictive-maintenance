# Algorithme de Test d'Alerte (test_alerting.py)

## Objectif

Tester l'envoi d'alertes Telegram et Email **sans dépendre du ML** (Isolation Forest, Random Forest).  
Le script simule une alerte en utilisant les **températures réelles** lues depuis InfluxDB.

---

## Déroulement

```
┌─────────────────────────────────────────────────────┐
│                    1. CONFIG                         │
│   Vérifier que TELEGRAM_BOT_TOKEN est bien configuré │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│             2. CONNEXION INFLUXDB                     │
│   influx.init_influxdb()                              │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│           3. LECTURE TEMPÉRATURES                     │
│   get_affected_molds()                                │
│   ┌───────────────────────────────────────────────┐  │
│   │ 3.1 query_recent(minutes=5)                   │  │
│   │ 3.2 Grouper par (group_id, mold_id)           │  │
│   │ 3.3 Garder la dernière valeur de chaque moule │  │
│   └──────────┬────────────────────────────────────┘  │
│              │                                       │
│              ▼                                       │
│   ┌───────────────────────────────────────────────┐  │
│   │ 3.4 Appliquer les seuils par moule :           │  │
│   │                                               │  │
│   │  temp < 40°C  →  CRITIQUE  →  affected=True   │  │
│   │  40 ≤ t < 42  →  ALERTE    →  affected=True   │  │
│   │  t ≥ 42°C     →  OK        →  affected=False  │  │
│   └──────────┬────────────────────────────────────┘  │
│              │                                       │
│              ▼                                       │
│   Retourne : (affected_molds, worst_status, temps)   │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              4. ENVOI D'ALERTE                        │
│                                                       │
│   Si affected_molds non vide :                        │
│     severity = map(worst_status)                      │
│       CRITIQUE → "CRITICAL"                           │
│       ALERTE   → "WARNING"                            │
│                                                       │
│   Si affected_molds vide :                            │
│     severity = "WARNING" (test forcé)                 │
│                                                       │
│   alerting.send_alert(                                │
│     severity,                                         │
│     cause="Modèles ML pas encore entraînés",          │
│     confidence=None,                                  │
│     actions=[...],                                    │
│     amdec_criticite=None,                             │
│     amdec_priorite=None,                              │
│     affected_molds=affected,                          │
│   )                                                   │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│         5. VÉRIFICATION MANUELLE                      │
│   - Chat Telegram (groupe opérateurs + chef)         │
│   - Boîte email (chef d'équipe)                      │
└─────────────────────────────────────────────────────┘
```

---

## Seuils de température

| Température mesurée | Status modbus | Severité alerte | Alerte envoyée |
|---|---|---|---|
| `T < 40°C` | `CRITIQUE` | `CRITICAL` | Telegram opérateurs + chef + Email |
| `40°C ≤ T < 42°C` | `ALERTE` | `WARNING` | Telegram opérateurs uniquement |
| `T ≥ 42°C` | `OK` | Aucune | Aucune |

---

## Structure de `get_affected_molds()`

**Entrée** : Aucune (lecture InfluxDB)

**Sortie** :
```python
(
    affected_molds: List[int],   # IDs des moules en dessous des seuils
    worst_status: str,           # "OK" | "ALERTE" | "CRITIQUE"
    temps: Dict[int, float],     # {mold_id: temperature}
)
```

**Algorithme** :
1. Appeler `influx.query_recent(minutes=5)` → récupère toutes les températures des 5 dernières minutes
2. Pour chaque entrée, stocker la **plus récente** par moule
3. Pour chaque moule, comparer sa température aux seuils
4. Construire la liste des IDs affectés
5. Déterminer le pire status parmi tous les moules

---

## Exemple d'exécution

```bash
$ python tests/test_alerting.py
```

Sortie console :
```
==================================================
TEST ALERTES - Telegram & Email
==================================================

Températures actuelles :
  Moule 1: 44.2°C
  Moule 2: 43.8°C
  Moule 3: 41.5°C
  Moule 4: 39.7°C
  Moule 5: 42.1°C
  Moule 6: 41.0°C
  Moule 7: 43.5°C

Moules affectés : [3, 4, 6]
Pire statut      : CRITIQUE
--------------------------------------------------
Test envoyé - vérifie Telegram et Email
==================================================
```

Messages reçus :
- **Telegram opérateurs** : 🔴 ALERTE CRITIQUE avec cause, moules 3,4,6, actions
- **Telegram chef** : 🔴 ALERTE CRITIQUE (identique)
- **Email chef** : ALERTE CRITIQUE avec mêmes informations
