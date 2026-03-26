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
