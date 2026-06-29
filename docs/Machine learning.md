# Guide Complet — Machine Learning pour la Supervision Thermique

> Document de référence pour le rapport PFE.  
> Justifie le choix des modèles, explique leur fonctionnement, les métriques, l'entraînement, et l'intégration.

---

## Table des matières

1. [Architecture ML globale](#1-architecture-ml-globale)
2. [Choix des modèles](#2-choix-des-modèles)
3. [Feature Engineering](#3-feature-engineering)
4. [Modèle 1 : Isolation Forest (Détection d'anomalies)](#4-modèle-1--isolation-forest-détection-danomalies)
5. [Modèle 2 : Random Forest (Classification des causes)](#5-modèle-2--random-forest-classification-des-causes)
6. [Modèle 3 : Ridge Regression (Maintenance prédictive)](#6-modèle-3--ridge-regression-maintenance-prédictive)
7. [Modèle 4 : Grey-Box (Estimation physique calcaire)](#7-modèle-4--grey-box-estimation-physique-calcaire)
8. [Règles physiques déterministes (Niveau 1)](#8-règles-physiques-déterministes-niveau-1)
9. [Modèles pré-entraînés (.pkl)](#9-modèles-pré-entraînés-pkl)
10. [Métriques d'évaluation](#10-métriques-dévaluation)
11. [Entraînement sur données réelles](#11-entraînement-sur-données-réelles)
12. [Pièges et limites](#12-pièges-et-limites)
13. [Annexe : Organigramme décisionnel complet](#13-annexe--organigramme-décisionnel-complet)

---

## 1. Architecture ML globale

### 1.1 Les 4 modèles en un coup d'œil

```
┌──────────────────────────────────────────────────────────────────────┐
│                       PIPELINE ML COMPLET                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Données brutes (1 Hz)                                               │
│    ├── 12 températures moules  (Modbus)                              │
│    └── 4 débits de groupe      (YF-S201)                             │
│           │                                                          │
│           ▼                                                          │
│  ┌──────────────────────┐                                            │
│  │  Fenêtrage 30s       │  ← rolling window (deques)                 │
│  │  Feature extraction  │  ← 8D pour IF, 10D pour RF                │
│  └──────┬───────────────┘                                            │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │  NIVEAU 1            │  ← physical_rules() déterministes          │
│  │  Règles physiques    │  ← 3 causes avec confiance = 1.0           │
│  └──────┬───────────────┘                                            │
│         │ (si None → ambigu)                                         │
│         ▼                                                            │
│  ┌──────────────────────┐                                            │
│  │  NIVEAU 2            │  ← Random Forest (10 features)             │
│  │  ML supervisé        │  ← 7 classes de défaillance                │
│  └──────┬───────────────┘                                            │
│         │                                                            │
│         ▼                                                            │
│  ┌──────────────────────┐  ┌──────────────────────┐                  │
│  │  Isolation Forest    │  │  Grey-Box Model      │                  │
│  │  (anomalie ? Oui/Non)│  │  (épaisseur calcaire)│                  │
│  └──────────┬───────────┘  └──────────┬───────────┘                  │
│             │                         │                              │
│             ▼                         ▼                              │
│  ┌──────────────────────┐  ┌──────────────────────┐                  │
│  │  Enrichissement      │  │  Ridge Regression    │                  │
│  │  AMDEC + Alertes     │  │  (prédiction date    │                  │
│  │  Telegram + Email    │  │   maintenance)        │                  │
│  └──────────────────────┘  └──────────────────────┘                  │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Flux de décision par cycle (1 Hz)

```
Pour chaque seconde t :
  1. Lire 12 températures Modbus + 4 débits YF-S201
  2. Mettre à jour les historiques (deques de 3600 samples)
  3. Calculer Grey-Box → delta_T_calcaire, épaisseur_mm, urgence
  4. Extraire features (8D) via AnomalyDetector.extract_features()
  5. Isolation Forest → anomalie ? 
     │
     ├── NON → état normal, pas d'alerte
     │
     └── OUI → 
           a. Règles physiques (physical_rules) → cause certaine ?
              │
              ├── OUI → cause = physique (confiance = 1.0)
              │
              └── NON → Random Forest (10D) → cause + probabilités
              
           b. Enrichir avec infos AMDEC (criticité, priorité, actions)
           c. Envoyer alerte Telegram + Email
  6. Écrire dans InfluxDB
  7. Broadcast WebSocket → Frontend React
```

---

## 2. Choix des modèles

### 2.1 Pourquoi 4 modèles et pas un seul ?

| Problème | Solution | Type de modèle |
|----------|----------|----------------|
| "Y a-t-il une anomalie ?" | Isolation Forest | Non supervisé |
| "Quelle est la cause ?" | Random Forest + Règles physiques | Supervisé + déterministe |
| "Quand faudra-t-il intervenir ?" | Ridge Regression | Supervisé (régression) |
| "Quelle est l'épaisseur de calcaire ?" | Grey-Box Model | Déterministe (physique) |

Un seul modèle ne peut pas répondre à ces 4 questions de nature différente (classification binaire, classification multi-classes, régression temporelle, estimation physique).

### 2.2 Pourquoi Isolation Forest (et pas One-Class SVM ou LSTM) ?

| Critère | Isolation Forest | One-Class SVM | LSTM / Deep Learning |
|---------|-----------------|---------------|---------------------|
| Données d'entraînement | ~1000 échantillons normaux | ~5000 | Nécessite > 100 000 |
| Temps d'inférence | < 1 ms | < 5 ms | > 50 ms (GPU requis) |
| Interprétabilité | Haute (score d'anomalie) | Moyenne | Faible (boîte noire) |
| Passage à l'échelle | Linéaire O(n) | Quadratique O(n²) | Linéaire mais lourd |
| Robustesse au bruit | Très bonne (partition aléatoire) | Sensible aux outliers | Bonne mais lent |

**Conclusion :** L'Isolation Forest est le meilleur compromis pour un Raspberry Pi. Il ne nécessite pas de GPU, s'entraîne en quelques secondes, et donne un score d'anomalie interprétable.

### 2.3 Pourquoi Random Forest (et pas XGBoost ou Neural Network) ?

| Critère | Random Forest | XGBoost | MLP (Neural Network) |
|---------|---------------|---------|---------------------|
| Nombre d'hyperparamètres | 3-4 (n_estimators, max_depth, etc.) | 10+ | 15+ (architecture, learning rate, etc.) |
| Risque d'overfitting | Faible (bagging + max_depth) | Élevé sans pruning | Très élevé sans régularisation |
| Interprétabilité | Haute (feature_importances_) | Haute (SHAP values) | Faible |
| Données nécessaires | ~500 par classe | ~2000 par classe | ~10 000 par classe |
| Inférence sur Raspberry Pi | < 1 ms | < 2 ms | > 10 ms |

**Conclusion :** Le Random Forest avec 100 arbres et max_depth=10 est le choix le plus robuste pour un problème de classification avec peu de données et une contrainte d'inférence temps réel.

### 2.4 Pourquoi Ridge Regression (et pas ARIMA ou Prophet) ?

| Critère | Ridge Polynomial | ARIMA | Prophet |
|---------|-----------------|-------|---------|
| Données minimales | 7 points | 30 points | 365 points |
| Interprétation | Coefficients explicites | Ordres (p,d,q) obscurs | Tendance + saisonnalité |
| Intervalles de confiance | Bootstrap (1000 simulations) | Formule analytique | MCMC (lent) |
| Extrapolation | Polynôme degré 2 | Stationnarité requise | Bonne |

**Conclusion :** La Ridge régression polynomiale (degré 2, régularisation L2) est la plus adaptée pour des séries courtes (7 à 90 jours) avec une tendance monotone (dépôt calcaire). Le bootstrap compense l'absence d'intervalle de confiance analytique.

### 2.5 Pourquoi Grey-Box (et pas un modèle black-box) ?

Le Grey-Box utilise la **loi de Fourier** de conduction thermique :

```
Q = flow × ρ × Cp × ΔT          → flux thermique transporté par l'eau
R_calcaire = ΔT_calcaire / Q    → résistance thermique de la couche de calcaire
épaisseur = R × λ × A           → épaisseur = résistance × conductivité × surface
```

**Avantages :**
- Aucune donnée d'entraînement nécessaire
- Physiquement interprétable (chaque paramètre a un sens : ρ, Cp, λ, A)
- Robuste aux changements de conditions (fonctionne même sans calibration préalable)
- Permet de définir des seuils d'urgence physiquement fondés (OK > 43.5°C → URGENT < 42°C)

---

## 3. Feature Engineering

### 3.1 Les 10 features du système

Tous les features sont calculés sur une **fenêtre glissante de 30 secondes** (config.FEATURE_WINDOW_SECONDS).

| # | Feature | Unité | Description | Formule / Méthode | Rôle discriminant |
|---|---------|-------|-------------|-------------------|-------------------|
| 1 | `slope_T_mold` | °C/s | Pente moyenne de la régression linéaire des T | `np.polyfit(x, arr, 1)[0]` moyenné sur tous les moules | Pompe HS → pente négative forte ; Normal → ~0 |
| 2 | `variance_T_mold` | (°C)² | Variance moyenne des T | `np.var(arr)` moyenné sur tous les moules | Bulles d'air → variance ×15 ; Normal → 0.02 |
| 3 | `affected_molds_ratio` | — | Proportion de moules sous 42°C | `∑(T_mold < T_CRITICAL) / N_MOLDS` | Panne globale → ~1.0 ; Localisée → ~0.2 |
| 4 | `sudden_drop_flag` | bool | Chute brutale > 1°C en 2 min | `T[-1] - T[-120] < -1.0` pour un moule | Pompe HS → 1 ; Calcaire → 0 |
| 5 | `flow_rate` | L/min | Débit moyen | `mean(flow_history[gid])` sur tous les groupes | Pompe HS → ~2.0 ; Normal → 16.5 |
| 6 | `flow_drop_flag` | bool | Chute de débit | `flow_rate < 0.5 × FLOW_DEFAULT_LPM` | Pompe/vanne → 1 ; Normal → 0 |
| 7 | `flow_variance` | (L/min)² | Variance du débit | `np.var(flow_history[gid])` moyenné | Bulles d'air → 2.0 ; Normal → 0.1 |
| 8 | `delta_T_calcaire_slope` | °C/jour | Pente du delta_T_calcaire sur 7 jours | `mean(delta_T_calcaires) / 7.0` | Calcaire → 0.05 ; Normal → 0 |
| 9 | `drift_R_squared` | — | R² de la régression linéaire des T | `1 - SS_res / SS_tot` sur la fenêtre | Calcaire → 0.92 (dérive régulière) ; Bulles → 0.2 (bruit) |
| 10 | `autocorr_lag1` | — | Autocorrélation lag-1 des T | `np.corrcoef(arr[:-1], arr[1:])[0,1]` | Normal → 0.7 (inertie) ; Bulles → 0.2 (bruit blanc) |

### 3.2 Pourquoi 10 features et pas plus ?

1. **Malédiction de la dimension :** Plus on ajoute de features, plus il faut de données d'entraînement. Avec ~7 classes et ~500 échantillons/classe, 10 features est le bon équilibre.
2. **Interprétabilité :** Chaque feature a un sens physique clair — on peut expliquer pourquoi une feature augmente ou diminue pour une défaillance donnée.
3. **Importance des features :** Les 3 features les plus importantes (flow_rate, flow_variance, affected_molds_ratio) expliquent ~60% de la décision.

### 3.3 Alignement avec l'AMDEC

Chaque feature a été choisie pour discriminer des modes de défaillance spécifiques identifiés dans l'AMDEC :

| Mode AMDEC | Features discriminantes | Pourquoi |
|------------|------------------------|----------|
| CALCAIRE_TUYAUX | delta_T_calcaire_slope ↑, drift_R² ↑, flow_rate ↓ | Dépôt régulier, débit réduit |
| HEATER_POMPE_HS | flow_rate ↓↓, sudden_drop, affected ↑↑ | Pompe arrêtée → tout s'effondre |
| HEATER_RESISTANCE_HS | slope_T_mold ↓, affected ↑ | Perte de puissance chauffage |
| NIVEAU_BAS_VANNE_PANNE | flow_rate ↓, affected ↑, pas de sudden_drop | Manque d'eau progressif |
| BULLES_AIR | variance ↑↑, drift_R² ↓↓, autocorr ↓↓, flow_variance ↑↑ | Instabilité aléatoire |
| FUITE_CIRCUIT | flow_rate ↓, flow_variance ↑, drift_R² ↓ | Perte de charge, modéré |
| ISOLATION_DEGRADEE | affected ↓, drift_R² ↑, variance ↓ | Très localisé, lent |

---

## 4. Modèle 1 : Isolation Forest (Détection d'anomalies)

### 4.1 Principe

L'Isolation Forest est un algorithme non supervisé basé sur des **arbres de partition aléatoire**. Son idée est simple :

> Une anomalie est un point facile à isoler du reste des données.

Alors qu'un point normal nécessite plusieurs partitions aléatoires pour être isolé (il est au cœur de la distribution), une anomalie est isolée en très peu de partitions (elle est en périphérie).

### 4.2 Algorithme

```
Pour chaque arbre (n_estimators = 200) :
  1. Choisir un échantillon aléatoire de la taille du dataset
  2. Choisir une feature aléatoire parmi les 8
  3. Choisir un seuil aléatoire entre min et max de cette feature
  4. Partitionner les données (comme un arbre de décision)
  5. Répéter jusqu'à isoler chaque point (1 feuille par point)

Score d'anomalie :
  s(x) = 2^(-E[h(x)] / c(n))
  où E[h(x)] = profondeur moyenne du point x dans tous les arbres
      c(n)    = facteur de normalisation

  s(x) → 1 : fortement anormal
  s(x) → 0 : normal
```

### 4.3 Paramètres

```python
self.model = IsolationForest(
    n_estimators  = 200,      # 200 arbres
    contamination = 0.05,     # 5% d'anomalies attendues
    random_state  = 42,
    n_jobs        = -1,       # parallélisation
)
```

- `contamination=0.05` signifie qu'on s'attend à ce que ~5% des fenêtres soient des anomalies. C'est un choix cohérent avec un process industriel stable (95% de fonctionnement normal).
- Si le FPR (faux positifs) est trop élevé, on peut baisser `contamination` à 0.02 ou 0.03.

### 4.4 Sortie

```python
{
    'anomaly_detected': True/False,
    'anomaly_score': -0.15,   # négatif = anomalie, positif = normal
}
```

### 4.5 Pourquoi 8 features (pas 10) ?

L'Isolation Forest utilise **8 features** (pas les 10 du Random Forest) car :
- `flow_drop_flag` est redondant avec `flow_rate` pour la détection d'anomalies
- `delta_T_calcaire_slope` n'est pas pertinent pour une détection temps réel (nécessite 7 jours d'historique)
- `drift_R_squared` est plus utile pour classifier la cause que pour détecter l'anomalie

---

## 5. Modèle 2 : Random Forest (Classification des causes)

### 5.1 Principe

Le Random Forest est un ensemble d'**arbres de décision** entraînés sur des sous-échantillons aléatoires des données (bagging) avec des sous-ensembles aléatoires de features.

> Chaque arbre vote pour une classe → la classe majoritaire est retenue.

### 5.2 Algorithme

```
Pour chaque arbre (n_estimators = 100) :
  1. Bootstrapping : tirer N échantillons avec remplacement
  2. Pour chaque nœud :
     a. Choisir sqrt(n_features) features aléatoirement
     b. Trouver le meilleur split (Gini impurity)
     c. Partitionner
  3. Arrêter quand max_depth = 10 ou feuille pure

Prédiction :
  proba = mean(votes de chaque arbre)
  classe = argmax(proba)
```

### 5.3 Paramètres

```python
self.model = RandomForestClassifier(
    n_estimators  = 100,       # 100 arbres
    class_weight  = 'balanced', # compense le déséquilibre des classes
    max_depth     = 10,        # éviter l'overfitting
    random_state  = 42,
    n_jobs        = -1,
)
```

- `max_depth=10` limite la profondeur des arbres pour éviter le surapprentissage
- `class_weight='balanced'` donne plus de poids aux classes minoritaires (BULLES_AIR, ISOLATION_DEGRADEE)

### 5.4 Les 7 classes de sortie

| Classe | Description | Priorité AMDEC | Occurrence estimée |
|--------|-------------|----------------|-------------------|
| `NORMAL` | Fonctionnement nominal | — | ~80% |
| `CALCAIRE_TUYAUX` | Dépôt de calcaire dans les tuyaux | 3 | ~5% |
| `HEATER_RESISTANCE_HS` | Résistance chauffante grillée | 2 | ~2% |
| `BULLES_AIR` | Air dans le circuit hydraulique | 5 | ~4% |
| `HEATER_POMPE_HS` | Pompe de circulation HS | 4 | ~2% |
| `NIVEAU_BAS_VANNE_PANNE` | Niveau d'eau bas / vanne défectueuse | 1 | ~3% |
| `FUITE_CIRCUIT` | Fuite dans le circuit | 6 | ~2% |
| `ISOLATION_DEGRADEE` | Isolation thermique dégradée | 7 | ~2% |

### 5.5 Feature importances (exemple)

```
Feature                          Importance
───────────────────────────────────────────
flow_rate                        0.2304
flow_variance                     0.2121
affected_molds_ratio             0.1688
drift_R_squared                   0.1297
sudden_drop_flag                 0.0727
flow_drop_flag                   0.0727
variance_T_mold                  0.0564
autocorr_lag1                    0.0362
delta_T_calcaire_slope            0.0131
slope_T_mold                     0.0079
```

Les 3 features les plus importantes (flow_rate, flow_variance, affected_molds_ratio) représentent ~61% de la décision.

---

## 6. Modèle 3 : Ridge Regression (Maintenance prédictive)

### 6.1 Principe

La Ridge Regression est une régression linéaire avec une **régularisation L2** qui pénalise les coefficients trop grands :

```
Minimiser : MSE(y, y_pred) + α × ||w||²
  où α = 1.0 (paramètre de régularisation)
```

On utilise une **transformation polynomiale degré 2** pour capturer la non-linéarité :

```
y = w₀ + w₁ × x + w₂ × x²
  où x = nombre de jours depuis le début
      y = delta_T_calcaire du jour
```

### 6.2 Objectif

Prédire le nombre de jours restants avant que `delta_T_calcaire` n'atteigne le seuil critique `delta_T_max` (config.T_TOLERANCE = 3.0°C).

```
delta_T_max = T_heater - T_mold_critical - delta_T_normal
            = 45.0 - 42.0 - (45.0 - T_calibration)
            = 3.0 - delta_T_normal

Quand delta_T_calcaire >= delta_T_max → maintenance requise
```

### 6.3 Bootstrap pour intervalles de confiance

Pour chaque prédiction, on effectue **1000 simulations bootstrap** :

```
Pour i = 1 à 1000 :
  1. Tirer N échantillons avec remplacement depuis les données d'entraînement
  2. Ré-entraîner le modèle Ridge
  3. Prédire le jour de dépassement du seuil

Résultat :
  borne_basse  = percentile 5%   (pessimiste : maintenance plus tôt)
  médiane      = percentile 50%  (scénario le plus probable)
  borne_haute  = percentile 95%  (optimiste : plus de temps)
```

### 6.4 Paramètres

```python
self.model = Ridge(alpha=1.0)
self.poly  = PolynomialFeatures(degree=2, include_bias=True)
```

- `alpha=1.0` : régularisation L2 modérée
- `degree=2` : suffisant pour capturer l'accélération du dépôt calcaire
- `include_bias=True` : ajoute le terme constant w₀

### 6.5 Sortie

```python
{
    'jours_maintenance': 45,      # jours restants
    'borne_basse':       32,      # percentile 5%
    'borne_haute':       58,      # percentile 95%
    'predicted_date':    '15/07/2026',
    'n_bootstrap':       1000,
}
```

---

## 7. Modèle 4 : Grey-Box (Estimation physique calcaire)

### 7.1 Principe

Le Grey-Box est un **modèle physique déterministe** basé sur la **loi de Fourier** de conduction thermique. Il combine :

- **Grey** : paramètres physiques connus (ρ, Cp, λ, dimensions des tuyaux)
- **Box** : mesures en temps réel (T_mold, flow_rate)

### 7.2 Équations

```
1. Flux thermique par moule :
   Q = (flow_rate / N_molds) × ρ × Cp × ΔT_mesuré
   
   où flow_rate = débit total (L/min converti en m³/s)
       N_molds  = 12 moules en parallèle
       ρ        = 1000 kg/m³ (masse volumique de l'eau)
       Cp       = 4186 J/(kg·K) (capacité thermique de l'eau)
       ΔT_mesuré = T_heater - T_mold

2. Perte thermique due au calcaire uniquement :
   ΔT_calcaire = max(0, ΔT_mesuré - ΔT_normal)
   
   où ΔT_normal = T_heater - T_mold_jour1 (perte normale sans calcaire)

3. Résistance thermique du calcaire :
   R_calcaire = ΔT_calcaire / Q   (en °C/W)

4. Épaisseur estimée :
   épaisseur = R_calcaire × λ × A   (en mètres, converti en mm)
   
   où λ = 1.0 W/(m·K) (conductivité thermique du calcaire)
       A = π × L × D = π × 3.0 × 0.013 = 0.1225 m² (surface latérale du tuyau)
```

### 7.3 Calibration

Le premier jour de fonctionnement, on mesure la température de chaque moule `T_mold_jour1`. Cette valeur sert de référence "tuyau propre". Plus tard, tout écart supplémentaire est attribué au calcaire.

```python
grey_box.set_calibration(group_id=1, mold_id=1, T_mold_jour1=44.0)
# → delta_T_normal = 45.0 - 44.0 = 1.0°C
```

### 7.4 Niveaux d'urgence

| T_mold | Urgence | Dégradation | Action recommandée |
|--------|---------|-------------|-------------------|
| ≥ 43.5°C | OK | 0-20% | Aucune |
| 43.0 - 43.5°C | FAIBLE | 20-40% | Surveiller |
| 42.5 - 43.0°C | MOYEN | 40-60% | Planifier inspection |
| 42.0 - 42.5°C | HAUTE | 60-80% | Intervention rapide |
| < 42.0°C | URGENT | 80-100% | Arrêt production |

### 7.5 Sortie par moule

```python
{
    'delta_T_measured':  1.5,       # °C
    'delta_T_calcaire':  0.5,       # °C
    'Q':                 35.2,      # W
    'R_calcaire':        0.0142,    # °C/W
    'epaisseur_mm':      0.174,     # mm
    'urgence':           'FAIBLE',
    'degradation_pct':   33.3,      # %
}
```

---

## 8. Règles physiques déterministes (Niveau 1)

### 8.1 Principe

Les règles physiques constituent le **Niveau 1** du diagnostic. Avant d'appeler le Random Forest, on vérifie des conditions physiques simples mais **totalement certaines** (confiance = 1.0). C'est une architecture **hybride** : règles + ML.

### 8.2 Les 3 règles

```python
@staticmethod
def physical_rules(...):

    # Règle 1 : Résistance chauffante HS
    if temp_heater < 44.0 and affected_ratio > 0.8:
        return HEATER_RESISTANCE_HS

    # Règle 2 : Pompe HS
    if affected_ratio > 0.8 and sudden_drop and flow_drop:
        return HEATER_POMPE_HS

    # Règle 3 : Niveau bas / Vanne défectueuse
    if affected_ratio > 0.7 and flow_rate < 0.3 * 16.5 and not sudden_drop:
        return NIVEAU_BAS_VANNE_PANNE
```

### 8.3 Justification physique des seuils

| Règle | Seuil | Pourquoi ce seuil ? |
|-------|-------|---------------------|
| Résistance HS | T_heater < 44°C | Consigne = 45°C, tolérance ±1°C → en dessous de 44°C = anomalie certaine |
| Résistance HS | affected > 80% | Si un seul moule est froid, la cause peut être locale (bulle d'air, isolation). Si > 80% des moules, la cause est générale. |
| Pompe HS | affected > 80% + sudden_drop | Pompe = circulation générale. Si elle tombe, tous les moules chutent brutalement. |
| Pompe HS | flow_drop | Pompe arrêtée → débit effondré (< 50% du nominal) |
| Niveau bas | affected > 70% | La baisse de niveau affecte progressivement tous les groupes |
| Niveau bas | flow < 0.3 × nominal | Vanne partiellement ouverte → flow réduit mais pas nul |
| Niveau bas | NOT sudden_drop | La baisse de niveau est lente (gravité), pas brutale |

### 8.4 Les 4 classes restantes (ambiguës → ML)

Les classes `BULLES_AIR`, `CALCAIRE_TUYAUX`, `FUITE_CIRCUIT`, `ISOLATION_DEGRADEE` sont trop ambiguës pour des règles simples :

- **BULLES_AIR** : peut ressembler à un capteur défaillant (bruit, instabilité)
- **CALCAIRE_TUYAUX** : progression lente, difficile à détecter en temps réel
- **FUITE_CIRCUIT** : symptômes similaires à un niveau bas (débit réduit)
- **ISOLATION_DEGRADEE** : très localisée, peut passer inaperçue

Le Random Forest, avec ses 10 features, peut distinguer ces cas plus subtils.

---

## 9. Modèles pré-entraînés (.pkl)

### 9.1 Pourquoi des fichiers .pkl ?

Les modèles ML sont **sauvegardés sur le disque** après entraînement pour :
1. **Éviter de ré-entraîner** à chaque démarrage du backend
2. **Garantir la reproductibilité** (mêmes poids, mêmes prédictions)
3. **Permettre l'entraînement différé** (sur PC puissant, export vers Raspberry Pi)

### 9.2 Où sont-ils stockés ?

```
backend/models/
├── isolation_forest.pkl     # Isolation Forest
├── scaler_if.pkl            # StandardScaler (normalisation IF)
├── random_forest.pkl        # Random Forest
├── label_encoder.pkl        # LabelEncoder (classes → indices)
├── ridge/
│   ├── ridge_1_1.pkl        # Ridge (groupe 1, moule 1)
│   ├── ridge_1_2.pkl        # Ridge (groupe 1, moule 2)
│   ├── ...
│   └── ridge_4_3.pkl        # Ridge (groupe 4, moule 3)
└── training_report.json     # Rapport d'entraînement (date, métriques)
```

### 9.3 Comment sont-ils chargés ?

```python
# Au démarrage du backend (cause_classifier.py:201-209)
def _load(self):
    if os.path.exists(MODEL_PATH):
        self.model   = pickle.load(open(MODEL_PATH, 'rb'))
        self.encoder = pickle.load(open(ENCODER_PATH, 'rb'))
        self.trained = True
```

### 9.4 Comment sont-ils créés ?

**Méthode 1 : Entraînement synthétique** (pour tester)
```bash
python tests/evaluate_models.py
# → génère des .pkl avec des données simulées
```

**Méthode 2 : Entraînement sur données réelles** (production)
```bash
python scripts/train_models.py --days 21
# → entraîne sur 3 dernières semaines depuis InfluxDB
# → écrase les .pkl synthétiques
```

### 9.5 Cohérence des versions

**Problème potentiel :** Les `.pkl` peuvent avoir été entraînés avec une version différente de scikit-learn. Au chargement, un warning apparaît :

```
InconsistentVersionWarning: Trying to unpickle estimator RandomForestClassifier
from version 1.5.2 when using version 1.4.0
```

**Solution :** Ré-entraîner les modèles avec la version actuelle de scikit-learn :
```bash
python scripts/train_models.py
```

---

## 10. Métriques d'évaluation

### 10.1 Isolation Forest

| Métrique | Formule | Objectif | Interprétation |
|----------|---------|----------|----------------|
| **FPR** (False Positive Rate) | FP / (FP + TN) | < 5% | Taux de fausses alertes (normal détecté comme anomalie) |
| **TPR** / Recall | TP / (TP + FN) | > 90% | Taux de vraies anomalies détectées |
| **FPR OK ?** | FPR < 0.08 | OUI/NON | Seuil de tolérance pour les fausses alertes |

**Protocole :**
1. Générer 1800 échantillons normaux + 200 anormaux
2. Entraîner sur 900 normaux
3. Tester sur 900 normaux + 200 anormaux
4. Compter les FP et TP

### 10.2 Random Forest

| Métrique | Formule | Objectif | Interprétation |
|----------|---------|----------|----------------|
| **Precision** | TP / (TP + FP) | > 0.85 | Parmi les causes prédites X, combien sont vraiment X |
| **Recall** | TP / (TP + FN) | > 0.85 | Parmi les vraies causes X, combien ont été détectées |
| **F1-score** | 2 × P × R / (P + R) | > 0.85 | Moyenne harmonique précision/rappel |
| **F1 macro** | mean(F1 de chaque classe) | > 0.85 | F1 moyen, poids égal par classe |
| **F1 weighted** | mean(F1 pondéré par support) | > 0.85 | F1 moyen, pondéré par le nombre d'échantillons |
| **Accuracy** | (TP + TN) / Total | > 0.85 | Proportion de bonnes prédictions |
| **Matrice de confusion** | Diagonale = bonnes prédictions | — | Visualiser les confusions entre classes |

**Protocole :**
1. Générer ~1500 échantillons (214 par classe)
2. Split 80% train / 20% test (stratifié)
3. Entraîner sur X_train
4. Prédire sur X_test
5. Calculer les métriques

### 10.3 Ridge Regression

| Métrique | Formule | Objectif | Interprétation |
|----------|---------|----------|----------------|
| **RMSE** | √(MSE(y_test, y_pred)) | < 3 jours | Erreur de prédiction de la date de maintenance |
| **R²** | 1 - SS_res / SS_tot | > 0.80 | Qualité d'ajustement (1 = parfait) |
| **MAE** | mean(|y_test - y_pred|) | < 2 jours | Erreur absolue moyenne |

**Protocole :**
1. Générer 90 jours de delta_T_calcaire (tendance linéaire + bruit)
2. Split chronologique : 72 jours train, 18 jours test
3. Entraîner, prédire, calculer les erreurs

### 10.4 Grey-Box

| Métrique | Formule | Objectif | Interprétation |
|----------|---------|----------|----------------|
| **Erreur relative** | |actual - expected| / |expected| × 100 | < 10% | Erreur sur delta_T_calcaire |

**Protocole :**
1. Définir 4 cas théoriques (tuyau propre, dépôt léger, dépôt épais, faible débit)
2. Calculer delta_T_calcaire attendu par la formule physique
3. Comparer avec la sortie du modèle

---

## 11. Entraînement sur données réelles

### 11.1 Le script `scripts/train_models.py`

Ce script remplace les modèles synthétiques par des modèles entraînés sur les **vraies données** stockées dans InfluxDB.

```
python scripts/train_models.py --days 21 --eval
```

Ce qu'il fait :
1. **Charge** les données InfluxDB (températures, delta_T_calcaires, débits)
2. **Découpe** en fenêtres glissantes de 30s
3. **Extrait** les features (8D pour IF, 10D pour RF)
4. **Auto-label** chaque fenêtre via `CauseClassifier.auto_label()`
5. **Entraîne** l'Isolation Forest sur toutes les fenêtres
6. **Entraîne** le Random Forest sur les fenêtres étiquetées
7. **Évalue** (option --eval) : split 80/20 temporel + métriques
8. **Sauvegarde** les modèles dans `backend/models/`

### 11.2 Pourquoi l'auto-labeling ?

Dans un système de supervision industrielle, on n'a pas de base de données étiquetée (chaque fenêtre avec sa cause). L'auto-labeling permet d'**étiqueter automatiquement** les données historiques en utilisant les mêmes règles expertes que `physical_rules()` et `auto_label()`.

```python
label = CauseClassifier.auto_label(
    affected_ratio=0.75,
    sudden_drop=False,
    flow_drop=True,
    flow_rate=4.0,
    variance=0.02,
    R_squared=0.9,
    delta_T_calcaire_slope=0.0,
)
# → 'NIVEAU_BAS_VANNE_PANNE'
```

**Limite :** L'auto-labeling n'est pas parfait pour les cas ambigus. Mais il permet de bootstrap le Random Forest, qui peut ensuite être amélioré avec des labels vérifiés manuellement.

### 11.3 Split temporel (pas de shuffle !)

Pour les séries temporelles, le split train/test doit être **chronologique** :

```python
split = int(len(fenetres) * 0.8)
train = fenetres[:split]   # 80% les plus anciennes
test  = fenetres[split:]   # 20% les plus récentes
```

On ne mélange jamais les séries temporelles (data leakage : le modèle verrait des données futures pendant l'entraînement).

### 11.4 Comparaison : données synthétiques vs réelles

| Aspect | Synthétique | Réel |
|--------|-------------|------|
| Source | `_gen_rf_sample()` dans `tests/evaluate_models.py` | InfluxDB (capteurs réels) |
| Bruit | Gaussien propre (σ=0.02) | Réel (trous, dérive, oscillations PID) |
| Distribution classes | Parfaitement équilibrée | Déséquilibrée (NORMAL ≈ 80%) |
| Volume | 1500 échantillons | ~60 000 fenêtres pour 21 jours |
| Qualité | Parfaite (signatures "textbook") | Réelle (cas limites, superposition de défauts) |

---

## 12. Pièges et limites

### 12.1 Décalage de versions sklearn

Les `.pkl` sauvegardés avec sklearn 1.5.2 ne se chargent pas forcément avec sklearn 1.4.0. **Solution :** ré-entraîner avec la version installée.

### 12.2 Déséquilibre des classes

En production, NORMAL représente ~80-90% des fenêtres. Les classes de défaillance sont rares. Le `class_weight='balanced'` du Random Forest compense ce déséquilibre.

### 12.3 Confusion entre NIVEAU_BAS et FUITE_CIRCUIT

Ces deux modes de défaillance ont des signatures proches (débit réduit, affected_molds_ratio modéré). La distinction repose sur `flow_variance` (plus élevée pour une fuite) et `drift_R_squared`. Surveiller la matrice de confusion.

### 12.4 Grey-Box : calibration initiale

Le Grey-Box nécessite une température de calibration (jour 1, tuyau propre). Si la calibration est mal faite (T_mold_jour1 erronée), toutes les estimations d'épaisseur seront fausses.

### 12.5 Ridge : données insuffisantes

Le Ridge nécessite au moins `RIDGE_MIN_DAYS` (7 jours) de données. Avec moins de 7 jours, le modèle ne s'entraîne pas et retourne `None`.

### 12.6 8 features vs 10 features (bug connu)

L'`AnomalyDetector.extract_features()` retourne 8 features, mais le `RandomForestClassifier` en attend 10. La correction a été faite dans `main.py` en calculant les 3 features manquantes. Si ce bug réapparaît, vérifier le mapping des features.

---

## 13. Annexe : Organigramme décisionnel complet

```
DÉBUT DU CYCLE (1 Hz)
│
├─ Lire capteurs Modbus (12 températures)
├─ Lire débitmètres YF-S201 (4 débits)
│
├─ Mettre à jour TEMP_HISTORY (deques)
├─ Mettre à jour FLOW_HISTORY (deques)
│
├─ Grey-Box : compute() pour chaque moule
│   → delta_T_calcaire, épaisseur_mm, urgence
│
├─ extraire features 8D (AnomalyDetector)
│   → [slope, variance, affected_ratio, sudden_drop,
│      flow_rate, flow_variance, dT_mean, autocorr]
│
├─ Isolation Forest : predict(features_8d)
│   │
│   ├─ anomaly_detected = False
│   │   → diagnostic = { cause: NORMAL, confidence: 1.0 }
│   │   → pas d'alerte
│   │
│   └─ anomaly_detected = True
│       │
│       ├─ Calculer : affected_ratio, sudden_drop, flow_drop
│       │
│       ├─ Règles physiques (NIVEAU 1)
│       │   │
│       │   ├─ T_heater < 44°C & affected > 0.8
│       │   │   → HEATER_RESISTANCE_HS (confiance = 1.0)
│       │   │
│       │   ├─ affected > 0.8 & sudden_drop & flow_drop
│       │   │   → HEATER_POMPE_HS (confiance = 1.0)
│       │   │
│       │   ├─ affected > 0.7 & flow < 0.3*nominal & !sudden_drop
│       │   │   → NIVEAU_BAS_VANNE_PANNE (confiance = 1.0)
│       │   │
│       │   └─ Aucune règle → None (ambigu)
│       │       │
│       │       └─ Random Forest (NIVEAU 2)
│       │           ├─ Calculer features manquantes (10D)
│       │           │   → flow_drop_flag, dT_slope, drift_R²
│       │           │
│       │           └─ predict(rf_features_10d)
│       │               → CALCAIRE / BULLES / FUITE / ISOLATION
│       │               → + probabilités par classe
│       │
│       ├─ Enrichir avec AMDEC (config.py)
│       │   → criticité, priorité, actions
│       │
│       └─ Envoyer alerte Telegram + Email
│
├─ Écrire dans InfluxDB (températures + débits)
│
└─ Broadcast WebSocket → Frontend React
    → mise à jour des jauges, graphiques, alertes
```

---

## Références

| Concept | Référence |
|---------|-----------|
| Isolation Forest | Liu, Ting, Zhou. "Isolation Forest", ICDM 2008 |
| Random Forest | Breiman. "Random Forests", Machine Learning 2001 |
| Ridge Regression | Hoerl, Kennard. "Ridge Regression: Biased Estimation", Technometrics 1970 |
| Loi de Fourier conduction | Incropera. "Fundamentals of Heat and Mass Transfer", 7th ed. |
| AMDEC | ISO 31000:2018 — Risk Management |
| Bootstrap | Efron. "Bootstrap Methods: Another Look at the Jackknife", 1979 |
| Pertes de charge calcaire | Idelchik. "Handbook of Hydraulic Resistance", 1994 |
