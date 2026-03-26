<<<<<<< HEAD
# Supervision Thermique Industrielle

Système de supervision thermique pour ligne de production industrielle avec détection d'anomalies par machine learning et analyse AMDEC.

## Fonctionnalités

- **Acquisition temps réel** : 12 capteurs de température via Modbus RTU
- **Monitoring visuel** : Dashboard React avec graphiques en temps réel
- **Détection d'anomalies** : Isolation Forest + Random Forest pour classification des causes
- **Analyse AMDEC** : Priorisation des modes de défaillance (G×O×D)
- **Alertes automatisées** : Workflows n8n (Telegram, Email)
- **Maintenance prédictive** : Modèle Grey-Box pour estimation de l'encrassement calcaire

## Architecture

```
┌─────────────────┐     WebSocket      ┌──────────────────┐
│   Frontend      │◄──────────────────►│   Backend        │
│   (React/Vite)  │                    │   (FastAPI)      │
└─────────────────┘                    └────────┬─────────┘
                                                │
                          ┌─────────────────────┼─────────────────────┐
                          │                     │                     │
                    ┌─────▼─────┐        ┌──────▼──────┐       ┌──────▼─────┐
                    │  Modbus   │        │   ML Models │       │  InfluxDB  │
                    │  Sensors  │        │  (sklearn)  │       │  (history) │
                    └───────────┘        └─────────────┘       └────────────┘
```

## Structure du Projet

```
supervision_thermique/
├── backend/                 # API FastAPI + WebSocket
│   ├── main.py             # Point d'entrée
│   ├── config.py           # Configuration locale (non versionnée)
│   ├── config.py.example   # Template de configuration
│   ├── modbus_manager.py   # Communication Modbus RTU
│   ├── influxdb_manager.py # Stockage time-series
│   └── requirements.txt
├── frontend/               # Interface React
│   ├── src/
│   │   ├── App.jsx
│   │   └── components/     # Composants React
│   ├── package.json
│   └── vite.config.js
├── ml/                     # Modèles Machine Learning
│   └── cause_classifier.py # Random Forest pour diagnostic
├── n8n_workflows/          # Workflows d'automatisation
│   └── workflow_1_alertes.json
└── setup_rpi.sh            # Script d'installation Raspberry Pi
```

## Installation

### Prérequis

- Python 3.11+
- Node.js 18+
- InfluxDB 2.x
- n8n (optionnel, pour les alertes)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copier et configurer
cp config.py.example config.py
# Éditer config.py avec vos paramètres

# Lancer
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run build
# Les fichiers statiques sont générés dans dist/
```

### Raspberry Pi (Déploiement)

```bash
chmod +x setup_rpi.sh
./setup_rpi.sh
```

## Configuration

Copier `backend/config.py.example` vers `backend/config.py` et configurer :

| Paramètre | Description | Défaut |
|-----------|-------------|--------|
| `MODBUS_PORT` | Port série capteurs | `/dev/ttyUSB0` |
| `INFLUX_URL` | URL InfluxDB | `http://localhost:8086` |
| `T_HEATER` | Consigne température | `45.0` °C |
| `T_MOLD_CRITICAL` | Seuil critique | `42.0` °C |

## Analyse AMDEC

Les modes de défaillance sont priorisés selon l'analyse AMDEC (Gravité × Occurrence × Détection) :

| Priorité | Mode de Défaillance | G | O | D | Criticité |
|----------|---------------------|---|---|---|-----------|
| 1 | NIVEAU_BAS_VANNE_PANNE | 9 | 4 | 5 | 180 |
| 2 | HEATER_RESISTANCE_HS | 8 | 4 | 5 | 160 |
| 3 | CALCAIRE_TUYAUX | 8 | 4 | 3 | 96 |
| 4 | HEATER_POMPE_HS | 9 | 2 | 5 | 90 |
| 5 | BULLES_AIR | 6 | 5 | 3 | 90 |
| 6 | FUITE_CIRCUIT | 6 | 5 | 2 | 60 |
| 7 | ISOLATION_DEGRADEE | 5 | 3 | 3 | 45 |

## API WebSocket

Le backend expose une API WebSocket pour le temps réel :

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.temperatures : { mold_id: temperature }
  // data.flow_rate : débit en L/min
  // data.diagnostic : résultat ML
};
```

## Workflows n8n

Importer `n8n_workflows/workflow_1_alertes.json` dans votre instance n8n pour activer :
- Alertes Telegram (opérateurs + chef d'équipe)
- Emails de notification
- Webhook de diagnostic

## Technologies Utilisées

- **Backend** : FastAPI, WebSocket, PyModbus, InfluxDB Client
- **Frontend** : React 18, Vite, TailwindCSS, Recharts
- **ML** : scikit-learn (Isolation Forest, Random Forest)
- **Base de données** : InfluxDB 2.x (time-series)
- **Automatisation** : n8n
- **Hardware** : Raspberry Pi, LED WS2812, Capteurs Modbus RTU

## Développement

### Lancer en mode développement

```bash
# Backend
cd backend
source venv/bin/activate
python main.py

# Frontend (dans un autre terminal)
cd frontend
npm run dev
```

### Tests

```bash
cd backend
pytest
```

## Auteurs

- ENSA Kenitra
- Yazaki Maroc
- 2025-2026

## Licence

Ce projet est propriétaire. Tous droits réservés.
=======
# Supervision Thermique Industrielle : Diagnostic intelligent des Causes et Maintenance Prédictive de l'Encrassement par Soft Sensing et Machine Learning

  ***Projet de Fin d'Études 2025-2026 - ENSA Kénitra***

## Vue d'Ensemble
Ce projet, réalisé dans le cadre du Projet de Fin d'Études (PFE) 2025-2026 à l'ENSA Kénitra, a été développé pour Yazaki Morocco. L'objectif principal est de superviser la ligne de production de mousse (foaming), qui comprend 12 moules, afin de détecter et diagnostiquer les causes de baisse de température. Le système intègre des technologies de machine learning et de soft sensing pour une maintenance prédictive.

## Fonctionnalités Principales

Le projet est un système de supervision thermique avancé qui passe d'une simple surveillance à un diagnostique intelligent des causes et une maintenance prédictive. Les fonctionnalités clés incluent :

- **Acquisition de données**
  - Lecture Modbus des capteurs
  - Stockage dans InfluxDB
  - Fréquence : 1 seconde

- **Analyse AMDEC**
  - 7 modes de défaillance
  - Classification des causes
  - Calcul de criticité

- **Alertes**
  - Webhook n8n
  - Notifications email
  - Tableau de bord temps réel

- **Machine Learning**
  - Détection d'anomalies
  - Classification des causes
  - Prédiction maintenance


## Architecture Technique
L'architecture du projet est structurée en trois niveaux distincts :

- **Niveau 1** : Acquisition Physique

Composé d'un Raspberry Pi 4 8GB qui interroge les 12 capteurs de température et 3 capteurs de débit via Modbus RTU.

Inclut un système d'alertes visuelles avec une LED WS2812B.

- **Niveau 2** : Traitement et Machine Learning

     - **Isolation Forest** pour la détection d'anomalies (contamination 5%, 200 estimators).

     - **Random Forest** pour classifier la cause de l'anomalie (7 classes basées sur l'AMDEC, accuracy ~85%, 100 estimators).

     - **Ridge Regression** et un modèle Grey-Box pour la maintenance prédictive et l'estimation de l'épaisseur de calcaire (IC 90% avec bootstrap  1000 iterations).

L'AMDEC est intégrée pour prioriser la criticité des défaillances (calculée par Gravité × Occurrence × Détection).

- **Niveau 3** : Présentation et Automatisation

   - **Dashboard React** : Interface utilisateur pour la visualisation en temps réel via WebSocket composé de 3 onglets, supervision thermique, diagnostic intelligent et maintenance prédictive.

   - **InfluxDB** : Base de données pour le stockage des séries temporelles.

   - **n8n** : Plateforme d'automatisation pour la gestion des alertes (Telegram/Email) et la génération de rapports.

## Protocoles de Communication
Le système utilise plusieurs protocoles pour assurer la communication entre ses différents composants :

| Protocole | Usage | Port |
|:----------|:------|-----:|
| Modbus RTU | Capteurs | RS-485 |
| WebSocket | Temps réel | 8000 |
| HTTP/REST | API | 8000 |
| InfluxDB HTTP | Stockage | 8086 |
| n8n Webhooks | Alertes | 5678 |

## Modèle Grey-Box et Soft Sensing
L'innovation majeure du projet réside dans l'utilisation d'un modèle Grey-Box pour le soft sensing. Ce modèle physique estime l'épaisseur de calcaire dans les tuyaux en utilisant des données indirectes : températures d'entrée et de sortie, débit et température ambiante. Le principe repose sur un bilan thermique, où la résistance thermique du dépôt de calcaire est déduite des mesures selon la formule clé :

 ***e = R_calcaire × λ × A***    avec   ***R_calcaire = ΔT_calcaire / Q***   

 ***ΔT_calcaire(t)= ΔT_mesuré(t) − ΔT_normal***

 ***ΔT_normal= T_heater − T_mold_jour1***

 ***ΔT_mesuré(t)= T_heater − T_mold(t)***

Cela permet de prédire l'encrassement sans capteurs dédiés, réduisant ainsi les arrêts de ligne pour maintenance.

## Analyse AMDEC et Classes de Défaillance
Les modes de défaillance sont priorisés selon l'analyse AMDEC (Gravité × Occurrence × Détection). Le modèle Random Forest est entraîné à reconnaître les 7 classes suivantes :

| Défaillances | Priorité | Criticité |
|:-------------|:--------|--------: |
| NIVEAU_BAS_VANNE_PANNE | 1 | 180 |
| HEATER_RESISTANCE_HS | 2 | 160 |
| CALCAIRE_TUYAUX | 3 | 96 |
| HEATER_POMPE_HS | 4 | 90 |
| BULLES_AIR | 5 | 90 |
| FUITE_CIRCUIT  | 6 | 60 |
| ISOLATION_DEGRADEE | 7 | 45 |

## Installation et déploiement 
**Stack Backend**

| Technologie | Rôle |
|-------------|------|
| FastAPI | API REST + WebSocket |
| Uvicorn | Serveur ASGI |
| PyModbus | Communication Modbus RTU |
| InfluxDB Client | Base de données temps-réel |
| scikit-learn | ML (Isolation Forest, Random Forest, Ridge) |
| Pandas / NumPy | Analyse de données |
| Pydantic | Validation des données |
| python-dotenv | Variables d'environnement |

**Stack Frontend**

| Technologie | Rôle |
|-------------|------|
| React 18 | Framework UI |
| Vite | Build tool |
| TailwindCSS | Styles CSS |
| Recharts | Graphiques |
| WebSocket | Communication temps réel |
| React Router | Navigation |

```bash
#Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

#Frontend
  cd frontend
  npm install
  npm run dev
  
#n8n via PM2
# Installer n8n globalement
 npm install -g n8n
# Lancer avec PM2
 pm2 start n8n --name "n8n-workflows"
 pm2 save
 pm2 startup
```

## Variables d'Environnement

### Backend (`.env`)

| Variable | Description | Exemple |
|----------|-------------|---------|
| `INFLUXDB_URL` | URL de la base InfluxDB | `http://localhost:8086` |
| `INFLUXDB_TOKEN` | Token d'authentification | `votre-token` |
| `INFLUXDB_ORG` | Organisation | `yazaki` |
| `INFLUXDB_BUCKET` | Bucket de données | `supervision` |
| `MODBUS_PORT` | Port série Modbus | `/dev/ttyUSB0` |
| `MODBUS_BAUDRATE` | Baudrate Modbus | `9600` |
| `N8N_WEBHOOK_ALERT` | Webhook n8n alerte | `http://localhost:5678/webhook/alert` |

### Frontend (`.env`)

| Variable | Description | Exemple |
|----------|-------------|---------|
| `VITE_API_URL` | URL API backend | `http://localhost:8000` |
| `VITE_WS_URL` | URL WebSocket | `ws://localhost:8000/ws` |

### Configuration

```bash
# Backend
cp backend/config.example.py backend/config.py
echo "INFLUXDB_TOKEN=votre-token" >> backend/.env

# Frontend
echo "VITE_API_URL=http://localhost:8000" >> frontend/.env
```
## 📁 Structure du Projet

<details>
<summary><b>📂 Cliquez pour voir la structure complète du projet</b></summary>
 
 ```
 supervision_thermique/
├── backend/
│ ├── config.py.example
│ ├── influxdb_manager.py
│ ├── main.py
│ ├── modbus_manager.py
│ └── requirements.txt
├── frontend/
│ ├── src/
│ │ ├── components/
│ │ │ ├── CircularGauge.jsx
│ │ │ ├── DiagnosticTab.jsx
│ │ │ ├── MaintenanceTab.jsx
│ │ │ ├── MoldCard.jsx
│ │ │ └── SupervisionTab.jsx
│ │ ├── hooks/
│ │ │ └── useWebSocket.js
│ │ ├── App.jsx
│ │ ├── index.css
│ │ └── main.jsx
│ ├── index.html
│ ├── package.json
│ ├── postcss.config.js
│ ├── tailwind.config.js
│ └── vite.config.js
├── ml/
│ ├── anomaly_detector.py
│ ├── cause_classifier.py
│ ├── grey_box.py
│ └── ridge_predictor.py
├── n8n_workflows/
│ ├── workflow_1_alertes.json
│ └── workflow_2_rapport_quotidien.json
├── tests/
│ ├── test_modbus.py
│ ├── test_ml.py
│ ├── test_api.py
│ └── test_websocket.py
├── docs/
│ └── images/
│ ├── architecture.png
│ ├── dashboard.png
│ ├── n8n_workflow.png
│ └── led_alert.jpg
├── .gitignore
├── setup_rpi.sh
└── README.md
```          
</details>
>>>>>>> 20bd0111b0a6a3f4cf46028695e924b1ab5ad46f
