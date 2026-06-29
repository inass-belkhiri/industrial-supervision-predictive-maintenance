# Guide de Tests et Validation des Modèles ML

## 1. Architecture de la Simulation

Le projet permet de tester l'intégralité du pipeline **sans matériel** grâce à un système de simulation modulaire.

```
┌─────────────────────────────────────────────────────────────────┐
│                     MODE SIMULATION                              │
│  tests/run_simulated.py                                          │
│     ├── monkey-patch modbus_manager → modbus_simulator           │
│     ├── monkey-patch FlowSensor    → SimulatedFlowSensor        │
│     └── lance uvicorn (backend normal)                          │
│                                                                   │
│  Backend (inchangé)                                               │
│     ├── main.py: _cycle() tourne à 1 Hz                          │
│     ├── influxdb_manager: écrit dans InfluxDB                    │
│     ├── ML: anomaly detector, cause classifier, grey-box         │
│     └── WebSocket → Frontend React                               │
└─────────────────────────────────────────────────────────────────┘
```

### Principe

Aucune modification du code de production (`main.py`, `config.py`, etc.) n'est nécessaire. Les mocks sont injectés par **monkey-patching** au moment de l'import dans `run_simulated.py`.

---

## 2. Fichiers de Test

| Fichier | Rôle | Usage |
|---------|------|-------|
| `tests/run_simulated.py` | Point d'entrée du mode simulation | `python tests/run_simulated.py` |
| `tests/modbus_simulator.py` | Génère 12 températures réalistes | Mock automatique |
| `tests/flow_simulator.py` | Génère 4 débits YF-S201 | Mock automatique |
| `tests/data_generator.py` | Injecte N jours d'historique dans InfluxDB | `python tests/data_generator.py` |
| `tests/evaluate_models.py` | Évalue les 4 modèles ML avec métriques | `python tests/evaluate_models.py` |

### 2.1 `run_simulated.py`

**Ce qu'il fait :**
1. Monkey-patch de `modbus_manager.read_all_sensors()` → version simulée
2. Monkey-patch de `flow_sensor.FlowSensor` → `SimulatedFlowSensor`
3. Surcharge `config.MODBUS_PORT` pour éviter d'ouvrir le vrai port série
4. Lance `uvicorn` avec l'application FastAPI normale

**Démarrage :**
```bash
# Terminal 1 : InfluxDB doit tourner
# Terminal 2 :
cd supervision_thermique
python tests/run_simulated.py
# Backend sur http://0.0.0.0:8001

# Terminal 3 : Frontend
cd frontend
npm run dev
# Interface sur http://localhost:5173
```

### 2.2 `modbus_simulator.py`

**Modes de simulation disponibles :**

| Mode | Description |
|------|-------------|
| `NORMAL` | Toutes les températures stables autour de 44-45°C (fonctionnement normal) |
| `GRADUAL_DROP` | Refroidissement progressif de tous les moules (-0.005°C par appel) |
| `SUDDEN_DROP` | Chute brutale de -2.5°C sur un moule aléatoire après 60 cycles |
| `NOISY` | Normal avec 10% de lectures `ERREUR` aléatoires |
| `HEATER_FAIL` | Tous les moules descendent sous 42°C (panne chauffage global) |
| `PUMP_FAIL` | Après 50 cycles, chute chaotique des températures (panne pompe) |

**Changement de mode en direct :**
```python
from modbus_simulator import set_mode
set_mode('SUDDEN_DROP')
```

### 2.3 `data_generator.py`

Génère et injecte dans InfluxDB des données historiques synthétiques.

**Paramètres :**
- `N_DAYS = 60` : nombre de jours générés
- Données température : 1 point toutes les 5 minutes (288 points/jour/moule)
- Données débit : 1 point par heure (24 points/jour/groupe)

**Scénarios de dégradation :**

| Scénario | Poids | Température | Débit | Description |
|----------|-------|-------------|-------|-------------|
| `normal` | 80% | 44.5 ± 0.3°C | 16.5 ± 0.5 L/min | Fonctionnement nominal |
| `calcaire` | 10% | 43.0 ± 0.4°C | 13.0 ± 1.0 L/min | Dépôt calcaire |
| `pompe_hs` | 5% | 39.0 ± 1.5°C | 3.0 ± 0.5 L/min | Panne pompe |
| `bruit` | 5% | 44.0 ± 1.2°C | 15.0 ± 3.0 L/min | Capteur bruité |

**Utilisation :**
```bash
python tests/data_generator.py
```

### 2.4 `evaluate_models.py`

Évalue les 4 modèles ML et produit un rapport complet.

**Utilisation :**
```bash
python tests/evaluate_models.py
```

**Sorties :**
- `evaluation_report.txt` — rapport lisible
- `evaluation_results.json` — données structurées

---

## 3. Métriques de Validation par Modèle

### 3.1 Isolation Forest (Détection d'Anomalies)

**Type :** Non-supervisé

**Principe :** Apprend la distribution des données normales. Tout écart significatif est marqué comme anomalie.

**Métrique clé :** **FPR (False Positive Rate)**

**Protocole de test :**
1. Générer 1800 échantillons normaux + 200 échantillons anormaux
2. Entraîner sur 900 normaux
3. Tester sur 900 normaux + 200 anormaux
4. Compter les faux positifs (normaux classés anormaux) et vrais positifs (anormaux détectés)

**Calcul :**
```
FPR = FP / (FP + TN)
     = normaux détectés anormaux / total normaux

TPR = TP / (TP + FN)
     = anormaux détectés / total anormaux
```

**Objectif :** FPR < 5%

**Interprétation :** Un FPR de 5% signifie que 5% des alertes sont fausses (bruit normal). Le seuil `contamination=0.05` dans le code correspond à ce taux attendu.

### 3.2 Random Forest (Classification des Causes)

**Type :** Supervisé

**Métriques clés :** **Accuracy, F1-score, Matrice de confusion**

**Protocole de test :**
1. Générer ~1500 échantillons étiquetés (7 classes) via `auto_label()`
2. Split 80% train / 20% test (avec stratification)
3. Entraîner le Random Forest
4. Prédire sur le test set

**Rapport de classification :**
```python
from sklearn.metrics import classification_report, confusion_matrix

y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))
```

**Métriques par classe :**

| Métrique | Formule | Signification |
|----------|---------|---------------|
| Precision | TP / (TP + FP) | Parmi les causes prédites X, combien sont vraiment X |
| Recall | TP / (TP + FN) | Parmi les vraies causes X, combien ont été détectées |
| F1-score | 2 × (P × R) / (P + R) | Moyenne harmonique précision/rappel |
| Accuracy | (TP + TN) / Total | Proportion de bonnes prédictions |

**Objectif :** F1-macro > 0.85

**Matrice de confusion :** Les valeurs diagonales sont les bonnes prédictions. Les hors-diagonales sont les confusions. Par exemple, confondre `NIVEAU_BAS_VANNE_PANNE` et `FUITE_CIRCUIT` est une erreur fréquente à surveiller.

### 3.3 Ridge Regression (Maintenance Prédictive)

**Type :** Supervisé (régression)

**Métriques clés :** **RMSE, R², MAE**

**Protocole de test :**
1. Générer 90 jours de données delta_T_calcaire (tendance linéaire + bruit)
2. Split chronologique : 72 jours train, 18 jours test
3. Entraîner le modèle Ridge (polynôme degré 2)
4. Prédire les 18 jours test

**Calcul :**
```python
from sklearn.metrics import mean_squared_error, r2_score

rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2   = r2_score(y_test, y_pred)
mae  = mean_absolute_error(y_test, y_pred)
```

**Interprétation :**

| Métrique | Objectif | Signification |
|----------|----------|---------------|
| RMSE | < 3 jours | Erreur moyenne de prédiction de maintenance |
| R² | > 0.80 | Qualité d'ajustement de la courbe (1 = parfait) |
| MAE | < 2 jours | Erreur absolue moyenne (moins sensible aux outliers que RMSE) |

**Split chronologique (obligatoire pour les séries temporelles) :**
```python
split = int(len(records) * 0.8)
train, test = records[:split], records[split:]
```
On ne shuffle jamais les séries temporelles (risque de data leakage).

### 3.4 Grey-Box (Épaisseur Calcaire)

**Type :** Déterministe (physique)

**Métrique :** **Erreur relative (%)**

**Protocole de test :**
1. Définir des cas théoriques (température moule, débit, état calcaire connu)
2. Comparer la sortie du modèle à la valeur attendue

**Calcul :**
```
Erreur (%) = |delta_T_calcaire_calculé - delta_T_calcaire_attendu|
             / delta_T_calcaire_attendu × 100
```

**Cas de test :**

| Cas | T_mold | Débit | delta_T_calcaire attendu |
|-----|--------|-------|--------------------------|
| Tuyau propre | 44.0°C | 16.5 L/min | 0.0 |
| Dépôt léger | 43.5°C | 16.5 L/min | ~0.5 |
| Dépôt épais | 42.0°C | 14.0 L/min | ~2.0 |
| Faible débit | 43.0°C | 10.0 L/min | ~1.2 |

**Objectif :** Erreur < 10%

---

## 4. Synthèse des Objectifs

| Modèle | Type | Métrique | Objectif | Méthode |
|--------|------|----------|----------|---------|
| **Isolation Forest** | Non-supervisé | FPR | < 5% | Injection anomalies synthétiques |
| **Random Forest** | Supervisé | F1-score (macro) | > 85% | Train/test split (80/20) |
| **Ridge Regression** | Supervisé | RMSE / R² | < 3j / > 0.80 | Split chronologique (80/20) |
| **Grey-Box** | Déterministe | Erreur relative | < 10% | Cas théoriques |

---

## 5. Procédure de Test Complète

```bash
# 1. Vérifier qu'InfluxDB tourne
influx ping

# 2. Injecter des données historiques (optionnel, pour Ridge)
python tests/data_generator.py

# 3. Lancer le backend en mode simulation
python tests/run_simulated.py

# 4. Dans un autre terminal, lancer le frontend
cd frontend && npm run dev

# 5. Changer de mode de simulation (dans un shell Python)
python -c "
from tests.modbus_simulator import set_mode
set_mode('SUDDEN_DROP')
"

# 6. Évaluer les modèles ML séparément
python tests/evaluate_models.py
```

---

## 6. Questions Fréquentes

### Comment splitter les vraies données (80% train / 20% test) ?

Cela dépend du modèle :

- **Random Forest** : les feature vectors (fenêtres de 30s) sont indépendants → `train_test_split(X, y, test_size=0.2, shuffle=True)`
- **Ridge Regression** : série temporelle → split **chronologique** obligatoire (premiers 80% des jours en train, 20% restants en test). Jamais de shuffle.
- **Isolation Forest** : pas de split classique. Entraîner sur une période connue comme normale (ex: premières 2 semaines), tester sur la suite.

### Où sont stockés les modèles entraînés ?

```
backend/models/
├── isolation_forest.pkl        # Modèle Isolation Forest
├── scaler_if.pkl               # StandardScaler associé
├── random_forest.pkl           # Random Forest
├── label_encoder.pkl           # LabelEncoder associé
└── ridge/
    ├── ridge_1_1.pkl           # Ridge mold (1,1)
    ├── ridge_1_2.pkl           # Ridge mold (1,2)
    └── ...                     # 12 fichiers au total
```

### Comment le système sait-il qu'il a assez de données réelles ?

Ce n'est plus une durée fixe — le module `ml/data_sufficiency.py` détermine
automatiquement le **seuil J_seuil** en traçant une courbe d'apprentissage
(performance en fonction du nombre de jours de données réelles). Voir
[section 8](#8-cycle-de-retraining-et-suffisance-des-données).

### Pourquoi la durée d'entraînement de 6 semaines était estimée suffisante ?

Référence historique pour l'ancien seuil fixe :

- **Isolation Forest** : besoin de ~1000-5000 points normaux. À 1 Hz, 6 semaines = 3.6M pts → bien plus qu'assez
- **Random Forest** : features engineering robustes, convergence bien avant 6 semaines
- **Ridge** : 42 points quotidiens (6 semaines) → 6× le minimum de 7 jours. Suffisant pour un polynôme degré 2 régularisé
- **Grey-Box** : pas de données d'entraînement (modèle physique)

### Comment interpréter la matrice de confusion ?

```
               Prédit
          A    B    C    D    E    F    G
Réel  A [TP   .    .    .    .    .    .]   → A bien classé
      B [ .   TP   .    .    .    .    .]   → B bien classé
      C [ FP   .   TP   .    .    .    .]   → C a des FP vers A
```

- **Diagonale** : bonnes prédictions (à maximiser)
- **Hors-diagonale** : erreurs de classification
- Une concentration de valeurs hors-diagonale entre deux classes indique que le modèle ne les distingue pas bien (ex: `NIVEAU_BAS` confondu avec `FUITE_CIRCUIT`)

---

## 7. Ajout du Flow dans InfluxDB

Les débits sont stockés dans une measurement `flow` séparée :

```
_bucket: sensors
  ├── measurement: temperature   ← 12 pts/sec (températures)
  │     tags: mold_id, group_id, position, status
  │     fields: temperature, threshold, deviation, delta_T_calcaire
  │
  └── measurement: flow           ← 4 pts/sec (nouveau)
        tags: group_id, unit
        fields: flow_rate
```

**Requêtes utiles :**

```python
# Écriture (1 pt par groupe par cycle)
influx.write_flow(group_id=1, flow_lpm=16.5)

# Lecture historique (moyenne horaire, 7 derniers jours)
history = influx.query_flow_history(group_id=1, days_back=7)
```

**Avantages :**
- Les débits ne sont plus perdus au redémarrage du backend (auparavant dans une deque mémoire)
- Historique disponible pour le diagnostic rétrospectif
- Corrélation possible : "montre le débit du 5 mars quand T_moule_8 < 42°C"

---

## 8. Cycle de Retraining et Suffisance des Données

### 8.1 Stratégie en deux phases

Le projet traverse deux phases après sa mise en production :

| Phase | Période | Données d'entraînement | Modèles concernés |
|-------|---------|------------------------|-------------------|
| **Amorçage** | J0 → J_seuil | Synthétiques + Réelles (augmentation par bruit) | IF, RF, Ridge |
| **Production** | J_seuil → ∞ | Réelles uniquement | IF, RF, Ridge |

Le seuil `J_seuil` est déterminé automatiquement par le module `ml/data_sufficiency.py`
en fonction de la quantité de données réelles nécessaire pour atteindre les objectifs
de performance de chaque modèle.

### 8.2 Détermination automatique du seuil (`ml/data_sufficiency.py`)

**Principe :** Pour chaque modèle, on trace une **courbe d'apprentissage** : performance
en fonction du nombre de jours de données réelles utilisées pour l'entraînement.
On cherche le point de **plateau** où ajouter plus de données n'améliore plus
significativement les performances.

**Algorithme :**

```
1. Charger toutes les données réelles disponibles dans InfluxDB
2. Grouper les données par jour calendaire
3. Pour k dans [3, 5, 7, 10, 14, 21, 28] jours :
   a. Random Forest : entraîner sur les features des k premiers jours
      → évaluer F1-macro sur les jours restants
   b. Ridge : entraîner sur les k premiers daily records (delta_T_calcaire)
      → évaluer R² sur les jours restants
4. Trouver le plus petit k où :
   - RF : F1-macro ≥ 0.85 ET pente d'amélioration < 0.01 (plateau)
   - Ridge : R² ≥ 0.80 ET pente d'amélioration < 0.01 (plateau)
5. J_seuil = max(k_RF, k_Ridge, 7)   // au moins 7 jours
```

**Fonctions principales :**

| Fonction | Description |
|----------|-------------|
| `count_real_data_days()` | Retourne le nombre de jours depuis la première donnée dans InfluxDB |
| `evaluate_rf_sufficiency(data)` | Évalue le seuil RF par courbe d'apprentissage |
| `evaluate_ridge_sufficiency(data)` | Évalue le seuil Ridge par courbe d'apprentissage |
| `compute_real_data_threshold()` | Calcule J_seuil = max(RF, Ridge, 7) |
| `get_retrain_mode()` | Retourne `('real_only', J_seuil)` ou `('mixed', J_seuil)` |

### 8.3 Cycle quotidien

```
┌──────────────────────────────────────────────────────────────────┐
│                       CYCLE DE RETRAINING                         │
│                                                                   │
│  Démarrage (1 fois)                                               │
│     ├── get_retrain_mode() → mode + J_seuil                      │
│     ├── Si mode == 'mixed' :                                      │
│     │    └── Retrain IF + RF + Ridge (réel + bruit synthétique)   │
│     └── Si mode == 'real_only' :                                  │
│          └── Retrain IF + RF + Ridge (réel uniquement)            │
│                                                                   │
│  Tous les jours à 5h00 (config.RETRAIN_HOUR)                     │
│     ├── Réévaluer get_retrain_mode() (J_seuil peut changer)       │
│     ├── Retrain Ridge obligatoire                                 │
│     └── Génération des graphiques de validation (PNG)             │
│                                                                   │
│  Toutes les ~10 min (model health loop)                            │
│     └── Évaluer IF + RF sur fenêtre glissante de 30 min          │
│         └── Si FPR > 15% ou F1 < 0.75 pendant 3 cycles → retrain │
└──────────────────────────────────────────────────────────────────┘
```

### 8.4 Flag de forçage

Dans `backend/config.py` :

```python
RETRAIN_HOUR    = 5           # Retrain quotidien à 5h du matin
FORCE_REAL_ONLY = False       # Passer à True après le 20 juin
```

Quand `FORCE_REAL_ONLY = True`, le seuil J_seuil est ignoré et **tous les
retrains utilisent données réelles uniquement**, quelle que soit la quantité
disponible.

### 8.5 Fichiers impliqués

| Fichier | Rôle |
|---------|------|
| `ml/data_sufficiency.py` | Évalue le seuil J_seuil par courbe d'apprentissage |
| `ml/plots_evaluation.py` | Génère les 4 graphiques de validation + courbe d'apprentissage |
| `backend/main.py` | Boucle quotidienne + démarrage : utilise `get_retrain_mode()` |
| `backend/config.py` | `FORCE_REAL_ONLY` et `RETRAIN_HOUR` |
| `ml/train_models.py` | `--plots` flag pour générer les graphiques après entraînement |

### 8.6 Graphiques de validation (`ml/plots_evaluation.py`)

Quatre graphiques sont générés en PNG dans `models/plots/` après chaque
évaluation complète ou entraînement avec `--plots` :

| Graphique | Fichier | Modèle | Description |
|-----------|---------|--------|-------------|
| **Courbe d'apprentissage** | `learning_curve.png` | RF + Ridge | Performance (F1 / R²) en fonction des jours de données réelles |
| **Clusters t-SNE** | `rf_tsne_clusters.png` | Random Forest | Projection t-SNE des features 10D → 2D, colorée par classe de cause |
| **Courbe AUC-ROC** | `if_roc_curve.png` | Isolation Forest | TPR vs FPR à différents seuils de décision, avec score AUC |
| **Régression Ridge** | `ridge_regression_{gid}_{mid}.png` | Ridge | Données réelles + prédiction polynomiale + seuil critique |
| **Histogramme des scores** | `if_score_histogram.png` | Isolation Forest | Distribution des anomaly scores avec ligne de seuil à 5% |

**Génération :**

```bash
# Dans main.py (automatique après chaque retrain Ridge)
python backend/main.py          # génère les plots dans models/plots/

# Depuis train_models.py (avec le flag --plots)
python ml/train_models.py --eval --plots
```

### 8.7 Exemple de déroulement

```
J0  : Déploiement, données synthétiques uniquement
     → mode = 'mixed', J_seuil = 7 (minimum)

J7  : 7 jours de données réelles
     → RF F1-macro = 0.82 (< 0.85), Ridge R² = 0.76 (< 0.80)
     → mode = 'mixed', J_seuil = 10

J14 : 14 jours de données réelles
     → RF F1-macro = 0.88 (≥ 0.85), plateau atteint
     → Ridge R² = 0.83 (≥ 0.80), plateau atteint
     → mode = 'real_only', J_seuil = 14
     → Tous les retrains suivants : données réelles uniquement

J20+ : FORCE_REAL_ONLY = True (après le 20 juin)
      → mode = 'real_only' même si J_seuil non atteint
```
