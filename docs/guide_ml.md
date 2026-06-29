# Guide du Module ML — Supervision Thermique Industrielle

---

## 1. Architecture : pourquoi `ml/` est séparé de `backend/` ?

```
supervision_thermique/
├── backend/          ← Orchestration : API, WebSocket, Modbus, InfluxDB
│   ├── main.py       ← Point d'entrée FastAPI (boucle monitoring + re-training)
│   ├── config.py     ← Configuration centralisée
│   └── ...
├── ml/               ← Définitions des modèles (bibliothèque ML réutilisable)
│   ├── anomaly_detector.py
│   ├── cause_classifier.py
│   ├── grey_box.py
│   ├── ridge_predictor.py
│   ├── train_models.py
│   ├── model_evaluator.py
│   ├── data_sufficiency.py
│   └── plots_evaluation.py
├── models/           ← Artefacts sérialisés (.pkl) — contrat entre ml/ et backend/
│   ├── isolation_forest.pkl
│   ├── scaler_if.pkl
│   ├── random_forest.pkl
│   ├── label_encoder.pkl
│   ├── ridge/ridge_{gid}_{mid}.pkl
│   └── training_report.json
└── tests/            ← Simulation et tests
    ├── modbus_simulator.py
    ├── flow_simulator.py
    ├── data_generator.py
    ├── run_simulated.py
    ├── train_sim_models.py
    ├── demo_cli.py
    └── test_*.py
```

**Principe :**
- `ml/` contient les **définitions** des modèles (classes, entraînement, inférence, évaluation)
- `backend/` importe depuis `ml/` via `sys.path.insert(0, ML_DIR)` dans `main.py` (lignes 13-15)
- `models/` contient les fichiers `.pkl` — c'est le **contrat** : `ml/` les produit, `backend/` les consomme

**Avantages :**
- `ml/` peut être testé et exécuté indépendamment
- `backend/` ne fait qu'utiliser les modèles — pas de couplage fort
- Possibilité de servir les modèles via une API ML dédiée plus tard

---

## 2. Les 4 modèles de Machine Learning

### 2.1 Isolation Forest — `ml/anomaly_detector.py`

**Rôle :** Détection d'anomalies non supervisée. Repère les comportements thermiques anormaux.

**Algorithme :** `sklearn.ensemble.IsolationForest`
- 200 estimateurs, contamination=5%, random_state=42
- Features normalisées par `StandardScaler`

**Features (8 dimensions) :**

| # | Feature | Sens |
|---|---------|------|
| 0 | `slope_T_mold` | Pente linéaire moyenne des températures |
| 1 | `variance_T_mold` | Variance moyenne entre moules |
| 2 | `affected_molds_ratio` | Fraction de moules sous le seuil critique |
| 3 | `sudden_drop_flag` | 1 si un moule a chuté > 1°C en 2 min |
| 4 | `flow_rate` | Débit pompe actuel |
| 5 | `flow_variance` | Variance du débit sur la fenêtre |
| 6 | `delta_T_calcaire_mean` | Moyenne du delta_T_calcaire |
| 7 | `autocorr_lag1` | Autocorrélation moyenne des températures |

**Cycle de vie :**
1. `extract_features(temp_history, flow_history, delta_T_calcaires)` → feature vector (8,)
2. `train(feature_matrix)` → entraîne le modèle + sauvegarde `.pkl`
3. `predict(features)` → `{anomaly_detected: bool, anomaly_score: float}`

**Fichiers produits :** `models/isolation_forest.pkl`, `models/scaler_if.pkl`

---

### 2.2 Random Forest — `ml/cause_classifier.py`

**Rôle :** Classification supervisée de la cause racine d'une anomalie.

**Algorithme :** `sklearn.ensemble.RandomForestClassifier`
- 100 estimateurs, max_depth=10, class_weight='balanced', random_state=42

**Classes (7 modes AMDEC) :**

| Classe | Description |
|--------|-------------|
| `CALCAIRE_TUYAUX` | Encrassement calcaire progressif |
| `HEATER_POMPE_HS` | Pompe de chauffage en panne |
| `HEATER_RESISTANCE_HS` | Résistance chauffante HS |
| `NIVEAU_BAS_VANNE_PANNE` | Niveau bas / vanne défectueuse |
| `BULLES_AIR` | Air dans le circuit hydraulique |
| `FUITE_CIRCUIT` | Fuite dans le circuit |
| `ISOLATION_DEGRADEE` | Isolation thermique dégradée |

**Architecture hybride :**
1. **Niveau 1 — Règles physiques** (`physical_rules()`) : cas certains à 100%
2. **Niveau 2 — Random Forest** (`predict()`) : pour les cas ambigus

**Règles physiques :**

| Condition | Cause |
|-----------|-------|
| T_heater < 44°C ET ratio affecté > 0.8 | `HEATER_RESISTANCE_HS` |
| ratio > 0.8 ET drop brusque ET flow_drop | `HEATER_POMPE_HS` |
| ratio > 0.7 ET flow < 30% nominal ET pas drop | `NIVEAU_BAS_VANNE_PANNE` |
| Sinon | `None` → ML |

**Auto-labellisation** (`auto_label()`) : règles utilisées pour générer des labels à partir de données historiques non labellisées.

**Features (10 dimensions) :** les 8 de l'IF + `flow_drop_flag` + `delta_T_calcaire_slope` + `drift_R_squared`.

**Fichiers produits :** `models/random_forest.pkl`, `models/label_encoder.pkl`

---

### 2.3 Grey-Box Model — `ml/grey_box.py`

**Rôle :** Estimation physique en temps réel de l'épaisseur de calcaire (soft sensor). Aucun apprentissage ML — modèle basé sur la loi de Fourier.

**Formules clés :**
```
Q = (débit / N_moules) × ρ × Cp × delta_T_mesuré
R_calcaire = delta_T_calcaire / Q
épaisseur (mm) = R_calcaire × λ × A_surface × 1000
```

**Niveaux d'urgence :**

| Température | Urgence |
|-------------|---------|
| ≥ 42°C | OK |
| ≥ 41,5°C | FAIBLE |
| ≥ 41,0°C | MOYEN |
| ≥ 40,5°C | HAUTE |
| < 40,5°C | URGENT |

**Pas de fichiers `.pkl`** — pas de paramètres appris.

---

### 2.4 Ridge Polynomial — `ml/ridge_predictor.py`

**Rôle :** Prédiction du nombre de jours restants avant un seuil critique de calcaire (maintenance prédictive).

**Algorithme :** `sklearn.linear_model.Ridge` avec `PolynomialFeatures(degree=2)`
- Alpha = 1.0 (régularisation L2)
- Un modèle par moule : `ridge_{gid}_{mid}.pkl`

**Bootstrap (1000 itérations) :** pour calculer les intervalles de confiance à 90%
- `borne_basse` = 5e percentile (cas pessimiste)
- `borne_haute` = 95e percentile (cas optimiste)
- `jours_maintenance` = médiane

**Contrainte :** nécessite au moins `RIDGE_MIN_DAYS` (7) enregistrements quotidiens.

**Fichiers produits :** `models/ridge/ridge_{gid}_{mid}.pkl` (contient model, X_data, y_data, n_days, poly)

---

## 3. Pipeline d'entraînement

### 3.1 Entraînement initial (manuel, une fois) — `ml/train_models.py`

```
Usage: python ml/train_models.py [--days 21] [--step 30] [--window 30] [--eval] [--plots]
```

**Étapes :**
1. Chargement des données depuis InfluxDB (températures, delta_T_calcaire, débits)
2. Fenêtrage glissant (`build_windows`) : découpe en fenêtres de `window` secondes avec un pas de `step` secondes
3. Extraction des features 8D (IF) et 10D (RF)
4. Auto-labellisation via règles physiques
5. Entraînement Isolation Forest → `models/isolation_forest.pkl`
6. Entraînement Random Forest → `models/random_forest.pkl`
7. (Optionnel `--eval`) Split temporel 80/20, rapport de classification, F1 macro
8. (Optionnel `--plots`) Graphiques : t-SNE, ROC, histogrammes
9. Sauvegarde du rapport → `models/training_report.json`

### 3.2 Re-training quotidien (automatique) — `backend/main.py`

**Boucle `daily_retrain_loop()` :**
- Se déclenche à `RETRAIN_HOUR` (configurable, défaut 5h du matin)
- Appelle `_retrain_all_ridge()`
- Recharge les 90 derniers jours depuis InfluxDB
- Ré-entraîne les modèles Ridge pour chaque moule
- Met à jour `latest_maintenance` avec les nouvelles prédictions
- Génère les graphiques Ridge via `plots_evaluation.generate_all_plots()`

### 3.3 Re-training sur dégradation — `backend/main.py`

**Boucle `model_health_loop()` :**
- S'exécute toutes les `EVAL_INTERVAL_CYCLES` (~10 min)
- Appelle `model_evaluator.run_evaluation()`
- Si les métriques se dégradent → `should_retrain()` → `_retrain_if_rf()`

**Seuils de dégradation (configurables) :**

| Métrique | Seuil | Persistance |
|----------|-------|-------------|
| Taux d'anomalie IF | > 15% (`IF_ANOMALY_RATE_MAX`) | 3 évaluations |
| F1-weighted RF | < 0.75 (`RF_F1_WEIGHTED_MIN`) | 3 évaluations |

---

## 4. Data Sufficiency — `ml/data_sufficiency.py`

**Rôle :** Déterminer si on a assez de données réelles pour abandonner les données synthétiques.

### Modes de retraining :

| Mode | Condition | Description |
|------|-----------|-------------|
| `mixed` | jours_réels < seuil | Données réelles + bruit synthétique |
| `real_only` | jours_réels ≥ seuil | Données réelles uniquement |

### Calcul du seuil :
1. Charger les données par jour depuis InfluxDB
2. Pour chaque `k` dans `[3, 5, 7, 10, 14, 21, 28]` :
   - Entraîner RF avec `k` jours → mesurer F1 macro
   - Entraîner Ridge avec `k` jours → mesurer R²
3. Détecter le **plateau** (quand ajouter des jours n'améliore plus)
4. Seuil = `max(plateau_RF, plateau_Ridge, 7)`

### Appelé par :
- `get_retrain_mode()` dans `_retrain_all_ridge()` et `_retrain_if_rf()`
- `compute_sufficiency_with_details()` → génère learning curves

---

## 5. Model Evaluator — `ml/model_evaluator.py`

**Rôle :** Surveillance continue de la santé des modèles en production.

**Fonctionnement :**
1. `fetch_recent(influx_module, minutes=30)` → données brutes des dernières 30 min
2. `build_feature_vectors(raw_data)` → feature vectors IF (8D) + RF (10D)
3. `auto_label_anomaly(raw_data)` → pseudo-label d'anomalie (0/1)
4. `auto_label_cause(raw_data)` → pseudo-label de cause
5. `evaluate_isolation_forest()` → métriques (tp, fp, fn, tn, anomaly_score)
6. `evaluate_random_forest()` → métriques (pred vs true, confidence)
7. `should_retrain(metrics_history)` → décision de retraining

**Métriques suivies dans l'historique :**
- `if_anomaly_rate` : proportion d'anomalies détectées
- `rf_f1_weighted` : précision de la classification

---

## 6. Plots Evaluation — `ml/plots_evaluation.py`

**Rôle :** Génération de graphiques pour évaluer la qualité des modèles.

**Graphiques produits (dans `models/plots/`) :**

| Graphique | Fonction | Déclencheur |
|-----------|----------|-------------|
| t-SNE Clusters | `plot_rf_tsne()` | `train_models.py --plots` |
| ROC Curve | `plot_if_roc()` | `train_models.py --plots` |
| IF Score Histogram | `plot_if_histogram()` | `train_models.py --plots` |
| Ridge Regression | `plot_ridge_regression()` | `_retrain_all_ridge()` + `train_models.py --plots` |
| Learning Curves | `plot_learning_curve()` | `compute_sufficiency_with_details()` |

**Dépendance :** matplotlib (backend 'Agg' — sans affichage, sauvegarde directe en PNG).

---

## 7. Simulation (sans capteurs)

Tout le framework de simulation permet de développer et tester sans matériel.

### 7.1 Modbus Simulator — `tests/modbus_simulator.py`

Remplace `modbus_manager.read_all_sensors()` par des données simulées.

**6 modes disponibles :**

| Mode | Comportement |
|------|--------------|
| `NORMAL` | Températures stables autour de 44°C |
| `GRADUAL_DROP` | Refroidissement progressif (simule calcaire) |
| `SUDDEN_DROP` | Chute brutale sur certains moules |
| `NOISY` | Normal avec 10% d'erreurs de lecture |
| `HEATER_FAIL` | Tous les moules refroidissent (panne chauffage) |
| `PUMP_FAIL` | Panne pompe + débit bas |

**Changement de mode en cours de route :**
```python
from modbus_simulator import set_mode
set_mode('SUDDEN_DROP')
```
Ou via l'API HTTP : `POST /api/sim/mode` avec `{"mode": "SUDDEN_DROP"}`
Ou via `tests/demo_cli.py` (interface interactive).

### 7.2 Flow Simulator — `tests/flow_simulator.py`

Remplace `flow_sensor.FlowSensor` par des débits simulés, adaptés à chaque mode.

### 7.3 Data Generator — `tests/data_generator.py`

Génère 60 jours de données synthétiques réalistes et les injecte dans InfluxDB.

**Scénarios de température :**

| Scénario | Poids | Description |
|----------|-------|-------------|
| `normal` | 75% | Fonctionnement normal |
| `calcaire` | 10% | Dérive progressive (encrassement) |
| `pompe_hs` | 5% | Panne pompe |
| `bruit` | 5% | Capteurs bruyants |
| `critique` | 5% | Dégradation sévère |

**Caractéristiques :**
- Cycle journalier (sinusoïde amplitude 0,4°C, min à 5h, max à 14h)
- Dérive d'encrassement par groupe (entre -0,015 et -0,030 °C/jour après le jour 20)
- Défauts localisés aléatoires (probabilité 10%/jour, durée 2-4 cycles)
- Débits par groupe avec scénarios cohérents

### 7.4 Lancement en simulation — `tests/run_simulated.py`

```bash
python tests/run_simulated.py
```

**Ce qu'il fait :**
1. Patche `modbus_manager.read_all_sensors` → `modbus_simulator.read_all_sensors`
2. Patche `FlowSensor` → `flow_simulator`
3. Seed InfluxDB avec 60 jours de données synthétiques
4. Démarre le backend FastAPI complet (monitoring, WebSocket, re-training)

**Les tâches asynchrones lancées :**
- `monitoring_loop()` → cycle d'acquisition 1 Hz
- `daily_retrain_loop()` → re-training Ridge quotidien
- `model_health_loop()` → évaluation + re-training sur dégradation
- `_retrain_all_ridge()` → pré-entraînement Ridge au démarrage (mode simulation)

### 7.5 Entraînement par simulation — `tests/train_sim_models.py`

```bash
python tests/train_sim_models.py
```

Cycle à travers les 6 modes simulateur, collecte les features en boucle, entraîne IF (sur mode NORMAL) et RF (sur tous les modes), sauvegarde dans `models/`.

### 7.6 CLI de démonstration — `tests/demo_cli.py`

```bash
python tests/demo_cli.py
```

Interface interactive qui envoie des requêtes HTTP pour changer le mode de simulation en temps réel.

---

## 8. Cycle de vie complet : du capteur à l'affichage

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. Acquisition (1 Hz)                                                       │
│    modbus_manager.read_all_sensors() → SensorReading[]                      │
│    flow_sensor.read_lpm() → float                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. Grey-Box (temps réel)                                                    │
│    GreyBoxModel.compute(gid, mid, T_mold, flow) → épaisseur, urgence       │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. Anomaly Detection (temps réel)                                           │
│    AnomalyDetector.extract_features() → features 8D                        │
│    AnomalyDetector.predict(features) → anomalie ? oui/non                  │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. Cause Classification (si anomalie)                                       │
│    CauseClassifier.physical_rules() → cause certaine ?                      │
│    CauseClassifier.predict(features 10D) → cause + confiance               │
├─────────────────────────────────────────────────────────────────────────────┤
│ 5. Enrichissement AMDEC                                                     │
│    config.AMDEC_FAILURE_MODES[cause] → criticité, priorité, actions        │
├─────────────────────────────────────────────────────────────────────────────┤
│ 6. Stockage                                                                 │
│    influxdb_manager.write_sensors(readings, delta_T_map)                   │
│    influxdb_manager.write_flow(gid, flow_lpm)                              │
├─────────────────────────────────────────────────────────────────────────────┤
│ 7. Diffusion WebSocket                                                      │
│    {sensors, diagnostic, maintenance} → frontend React                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 8. Alerting (si seuils dépassés)                                            │
│    Telegram + Email → opérateurs / chef                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│ 9. Model Health (toutes les ~10 min)                                        │
│    model_evaluator.run_evaluation() → métriques                             │
│    should_retrain() → re-training si nécessaire                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ 10. Re-training quotidien (5h du matin)                                     │
│     Ridge predictor mis à jour avec les 90 derniers jours                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Paramètres ML configurables dans `config.py`

| Paramètre | Défaut | Description |
|-----------|--------|-------------|
| `FEATURE_WINDOW_SECONDS` | 30 | Fenêtre glissante pour l'extraction de features |
| `RIDGE_MIN_DAYS` | 7 | Jours minimum avant d'entraîner Ridge |
| `BOOTSTRAP_N` | 1000 | Nombre d'itérations bootstrap pour les intervalles de confiance |
| `RETRAIN_HOUR` | 5 | Heure du re-training quotidien |
| `FORCE_REAL_ONLY` | False | Forcer l'utilisation des données réelles uniquement |
| `EVAL_INTERVAL_CYCLES` | 600 | Cycles entre 2 évaluations (~10 min à 1 Hz) |
| `EVAL_WINDOW_MINUTES` | 30 | Fenêtre de données pour l'évaluation |
| `EVAL_PERSISTENCE` | 3 | Évaluations consécutives avant retraining |
| `IF_ANOMALY_RATE_MAX` | 0.15 | Taux d'anomalie max avant retraining |
| `RF_F1_WEIGHTED_MIN` | 0.75 | F1 min avant retraining |

---

## 10. Résumé des fichiers `.pkl` produits

| Fichier | Produit par | Consommé par |
|---------|-------------|--------------|
| `models/isolation_forest.pkl` | `train_models.py`, `_retrain_if_rf()` | `AnomalyDetector._load()` |
| `models/scaler_if.pkl` | `train_models.py`, `_retrain_if_rf()` | `AnomalyDetector._load()` |
| `models/random_forest.pkl` | `train_models.py`, `_retrain_if_rf()` | `CauseClassifier._load()` |
| `models/label_encoder.pkl` | `train_models.py`, `_retrain_if_rf()` | `CauseClassifier._load()` |
| `models/ridge/ridge_{gid}_{mid}.pkl` | `_retrain_all_ridge()` | `RidgePredictor._load()` |
| `models/training_report.json` | `train_models.py --eval` | Consultation manuelle |
| `models/plots/*.png` | `train_models.py --plots`, `_retrain_all_ridge()` | Consultation manuelle |
