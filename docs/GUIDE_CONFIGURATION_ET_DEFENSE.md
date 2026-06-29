# Guide de Configuration et Défense PFE

## Table des Matières
1. [Défendre le Frontend (sans compétences React/JS)](#1-défendre-le-frontend)
2. [Configurer les IDs Modbus des Capteurs](#2-configurer-les-ids-modbus)
3. [Configurer InfluxDB](#3-configurer-influxdb)
4. [Flow Sensor — Réponse au Jury](#4-flow-sensor)
5. [ML Auto-Labeling — Réponse au Jury](#5-ml-auto-labeling)
6. [Prototype Adoucisseur — Concept](#6-prototype-adoucisseur)

---

## 1. Défendre le Frontend

### Stratégie de Positionnement

**Ne dites pas**: "Je ne connais pas React"
**Dites**: "Mon expertise est dans les niveaux 1 et 2 de l'architecture — l'acquisition temps réel, le modèle physique et le diagnostic ML. Le dashboard React est une couche de présentation standard qui consomme l'API WebSocket que j'ai conçue."

### Slides de Présentation Clés

**Slide Architecture** (mettez votre temps ici):
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Niveau 1       │    │  Niveau 2        │    │  Niveau 3       │
│  Acquisition    │    │  Traitement ML   │    │  Présentation   │
│                 │    │                  │    │                 │
│  • Modbus RTU   │───▶│  • Grey-Box      │───▶│  • WebSocket    │
│  • Capteurs T°  │    │  • Isolation F.  │    │  • React/Vite   │
│  • Débitmètre   │    │  • Random Forest │    │  • Telegram     │
│  • RPi 4 8GB    │    │  • Ridge + AMDEC │    │                  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
     ← VOTRE CŒUR DE MÉTIER →              Couche de présentation
                                            (boilerplate standard)
```

**Si on vous demande d'expliquer le frontend:**
> *"Le frontend est un client WebSocket qui se connecte à ws://localhost:8001/ws. Il reçoit un JSON avec trois clés: sensors (températures temps réel), diagnostic (résultat ML avec cause et confiance), et maintenance (prédiction d'encrassement par moule). Le hook useWebSocket.js gère la reconnexion automatique et les composants React affichent les données sous forme de jauges et de cartes."*

**Points à maîtriser (sans coder):**
- Savoir que `App.jsx` contient le router vers 3 onglets: Supervision, Diagnostic, Maintenance
- Savoir que `useWebSocket.js` utilise `new WebSocket('ws://localhost:8001/ws')` et parse le JSON reçu
- Savoir que les données sont affichées via Recharts (graphiques) et des cartes TailwindCSS

---

## 2. Configurer les IDs Modbus

### Comprendre le Système

Chaque capteur de température sur le bus RS485 a un **slave ID** unique (1-247). Votre code lit le **holding register 0** de chaque slave et multiplie la valeur brute par `TEMP_SCALE_FACTOR = 0.1` pour obtenir la température en °C.

### Étape 1: Scanner le Bus

Sur votre Raspberry Pi, lancez le scanner:

```bash
cd /home/pi/supervision_thermique/backend
source venv/bin/activate
python modbus_scanner.py
```

Cela va tester tous les IDs de 1 à 247 et afficher:
```
  ID     Value       Hex  Status
------------------------------------------
   1       435      0x1b3  OK  (43.5 deg C)
   2       440      0x1b8  OK  (44.0 deg C)
   ...
  15         --        --  NO RESPONSE
```

### Étape 2: Identifier les Capteurs

Notez quels IDs répondent et leurs valeurs. Si vous avez 12 capteurs + 1 débitmètre, vous devriez voir 13 réponses.

### Étape 3: Configurer SENSOR_MAP

Ouvrez `config.py` et mettez à jour:

```python
SENSOR_MAP = {
    # (groupe, moule) -> (slave_id, register)
    (1, 1): (1, 0),   # Groupe 1, Moule gauche = Slave ID 1
    (1, 2): (2, 0),   # Groupe 1, Moule centre = Slave ID 2
    (1, 3): (3, 0),   # Groupe 1, Moule droite = Slave ID 3
    # ... etc
}
```

**Important**: Le débitmètre doit avoir un ID différent des 12 capteurs. Par défaut c'est `FLOW_SENSOR_SLAVE = 13`.

### Étape 4: Vérifier le SCALE_FACTOR

Si le scanner affiche une valeur brute de 435 mais que la température réelle est 43.5°C:
- `TEMP_SCALE_FACTOR = 0.1` (435 × 0.1 = 43.5) ✓

Pour le débitmètre, consultez la datasheet. Souvent:
- Valeur brute 500 = 5.00 L/min → `FLOW_SCALE_FACTOR = 0.01`

### Étape 5: Tester

```bash
python -c "
import asyncio
import modbus_manager as modbus

async def test():
    await modbus.init_modbus()
    readings = await modbus.read_all_sensors({})
    for r in readings:
        print(f'Moule ({r.group_id},{r.mold_id}): {r.temperature}°C [{r.status}]')
    await modbus.close_modbus()

asyncio.run(test())
"
```

---

## 3. Configurer InfluxDB

### 3.1 Vérifier qu'InfluxDB tourne

```bash
sudo systemctl status influxdb
# Doit afficher "active (running)"
```

### 3.2 Accéder à l'Interface Web

Ouvrez dans un navigateur: `http://localhost:8086` ou `http://IP_RPI:8086`

Connectez-vous avec:
- Username: `admin`
- Password: `monitorTEMP26` (ou celui que vous avez défini)

### 3.3 Vérifier Bucket et Token

1. Allez dans **Data → Buckets** — vérifiez que le bucket `sensors` existe
2. Allez dans **Data → API Tokens** — copiez le token admin

### 3.4 Mettre à jour config.py

```python
INFLUX_URL    = 'http://localhost:8086'
INFLUX_TOKEN  = 'VOTRE_TOKEN_ICI'      # Remplacez YOUR_INFLUX_TOKEN_HERE
INFLUX_ORG    = 'temperature-monitoring'
INFLUX_BUCKET = 'sensors'
```

### 3.5 Tester la Connexion

```bash
cd /home/pi/supervision_thermique/backend
source venv/bin/activate
python -c "
import config
from influxdb_client import InfluxDBClient

client = InfluxDBClient(url=config.INFLUX_URL, token=config.INFLUX_TOKEN, org=config.INFLUX_ORG)
buckets = client.buckets_api().find_buckets().buckets
print('Buckets disponibles:')
for b in buckets:
    print(f'  - {b.name}')
client.close()
"
```

Doit afficher:
```
Buckets disponibles:
  - _monitoring
  - _tasks
  - sensors
```

### 3.6 Vérifier que les Données Arrivent

Après avoir lancé le backend (`python main.py`), allez dans InfluxDB UI → **Data Explorer**:

```flux
from(bucket: "sensors")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "temperature")
  |> filter(fn: (r) => r._field == "temperature")
  |> aggregateWindow(every: 10s, fn: mean)
```

Vous devriez voir 12 lignes (une par capteur) avec des températures.

### 3.7 Structure des Données dans InfluxDB

Chaque point écrit a cette structure:

```
Measurement: temperature
Tags:
  - mold_id: "1"
  - group_id: "1"
  - position: "gauche"
  - status: "OK" | "ALERTE" | "ERREUR"
Fields:
  - temperature: 43.52
  - threshold: 45.0
  - deviation: -1.48
  - delta_T_calcaire: 0.0
Timestamp: automatique
```

---

## 4. Flow Sensor — Réponse au Jury

**Ce qui a été fait**: Le code a été mis à jour pour lire le débitmètre via Modbus (slave ID 13) au lieu d'utiliser une valeur hardcoded.

**Si le débitmètre n'est pas encore connecté physiquement**, dites:

> *"Le débitmètre est prévu dans l'architecture avec un slave ID dédié sur le bus Modbus. Le code supporte déjà sa lecture en temps réel. Sur le site de Yazaki, le débitmètre [marque/modèle] sera installé et son scale factor configuré dans le fichier config. En attendant, le système utilise la valeur nominale de 16.5 L/min comme fallback, ce qui permet de valider toute la chaîne ML et Grey-Box."*

**Variable à ajuster**: `FLOW_SCALE_FACTOR` dans `config.py` — dépend de la datasheet de votre débitmètre.

---

## 5. ML Auto-Labeling — Réponse au Jury

**Le problème**: Vous n'avez pas de données étiquetées (pas d'historique de pannes réelles avec causes connues).

**Votre approche**: L'auto-labeling utilise des règles physiques déterministes pour générer des labels à partir de données brutes.

**Réponse au jury**:

> *"En milieu industriel, il est rare d'avoir des données étiquetées — personne ne note systématiquement 'panne pompe à 14h32'. Mon approche bootstrap les labels à partir de signatures physiques observables:
>
> - Si T_heater chute + tous les moules affectés → HEATER_RESISTANCE_HS (certain)
> - Si débit chute brutalement + tous les moules → HEATER_POMPE_HS (certain)
> - Si variance élevée + R² faible + peu de moules → BULLES_AIR (probable)
>
> Ces règles sont les mêmes que celles du niveau 1 du classifieur. Les cas ambigus sont laissés au Random Forest pour apprendre des patterns subtils. La classe_weight='balanced' compense le déséquilibre naturel des classes."*

**Pour renforcer**: Mentionnez que l'accuracy de ~85% est sur des données synthétiques/simulées et que le vrai test sera en production où le système s'améliorera avec les retours des techniciens.

---

## 6. Prototype Adoucisseur

### Concept

L'adoucisseur d'eau est la **solution préventive** au problème d'encrassement détecté par votre système. Il complète parfaitement votre PFE:

```
Votre système actuel: DÉTECTION → DIAGNOSTIC → ALERTE
Prototype adoucisseur: PRÉVENTION → RÉDUCTION ENCRASSEMENT
```

### Architecture Proposée

**Niveau matériel:**
- Résine échangeuse d'ions (résine cationique Na⁺)
- Capteur de dureté en sortie (capteur conductivité ou TDS)
- Vanne 3 voies motorisée (pour régénération)
- Bac à saumure (NaCl pour régénération)
- Raspberry Pi pour le contrôle (peut être le même que le système actuel)

**Niveau logiciel (à ajouter au backend):**
```python
# Nouveau module: ml/water_softener.py
class WaterSoftenerController:
    """
    Contrôle l'adoucisseur basé sur:
    1. Dureté de l'eau entrante (capteur TDS/conductivité)
    2. Volume traité (débitmètre intégré)
    3. Seuil de régénération (configurable)
    """
    def should_regenerate(self, hardness_ppm: float, volume_m3: float) -> bool:
        # Logique de décision
        pass
```

### Slide de Présentation

**Titre: "Perspective: Prototype d'Adoucisseur d'Eau"**

```
┌─────────────────────────────────────────────┐
│  Boucle Fermée: Détection → Action          │
│                                             │
│  Capteurs T° ──▶ Grey-Box ──▶ Alerte calcaire │
│                      │                       │
│                      ▼                       │
│              Adoucisseur ◀─── Régénération   │
│              (résine Na⁺)    automatique     │
│                      │                       │
│                      ▼                       │
│              Eau adoucie → Moules            │
└─────────────────────────────────────────────┘
```

**Ce que vous pouvez dire:**

> *"Mon système détecte l'encrassement et alerte. La prochaine étape logique est d'agir préventivement. J'ai conçu un prototype d'adoucisseur à résine échangeuse d'ions qui s'intègre directement: quand le Grey-Box détecte une épaisseur de calcaire critique, le système peut déclencher la régénération de l'adoucisseur automatiquement. C'est le passage d'un système de supervision à un système de contrôle en boucle fermée."*

### Implémentation Minimale (si vous voulez le faire)

1. **Capteur TDS/Conductivité** (~50 MAD) → lecture analogique via ADC MCP3008 sur le RPi
2. **Servomoteur ou relais** pour la vanne 3 voies
3. **Code Python** simple:
   ```python
   if durete > seuil or volume_traite > volume_max:
       activer_regeneration()
   ```

Voulez-vous que je développe le code complet du prototype adoucisseur?

---

## Checklist Avant Soutenance

- [ ] Lancer `modbus_scanner.py` pour vérifier les IDs des capteurs
- [ ] Mettre `INFLUX_TOKEN` dans `config.py`
- [ ] Tester `python main.py` et vérifier que les données arrivent dans InfluxDB
- [ ] Préparer la slide architecture avec distinction niveaux 1-2-3
- [ ] Préparer la réponse sur le frontend (boilerplate vs expertise embarquée)
- [ ] Préparer la réponse sur l'auto-labeling ML
- [ ] Préparer la slide "Perspective: Adoucisseur"
- [ ] Vérifier que `FLOW_SENSOR_ENABLED = True` fonctionne avec le débitmètre connecté
