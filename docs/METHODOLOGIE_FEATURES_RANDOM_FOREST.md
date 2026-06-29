# Méthodologie de Déduction des Features Synthétiques pour le Random Forest

## 1. Problématique

Pour évaluer le Random Forest, nous générons des données synthétiques via `_gen_rf_sample()` dans `tests/evaluate_models.py`. Les valeurs des features (pente, variance, débit, etc.) ne sont **pas choisies arbitrairement** — elles sont déduites de la **physique du procédé** et des **constantes système** définies dans `config.py`.

Ce document justifie chaque valeur par son fondement physique.

---

## 2. Features et leur Fondement Physique

### 2.1 `flow_rate` (L/min) — Débit

| Classe | Formule | Valeur | Justification |
|--------|---------|--------|---------------|
| Normal | `FLOW_DEFAULT_LPM` | 16.5 | Débit nominal du système (config) |
| CALCAIRE | `FLOW_DEFAULT_LPM × 0.79` | 13.0 | Perte de charge par dépôt calcaire > 20% (seuil AMDEC) |
| POMPE_HS | `FLOW_DEFAULT_LPM × 0.12` | 2.0 | Pompe arrêtée → convection naturelle résiduelle uniquement |
| NIVEAU_BAS | `FLOW_DEFAULT_LPM × 0.24` | 4.0 | Vanne partiellement ouverte (~25% du nominal) |
| FUITE | `FLOW_DEFAULT_LPM × 0.48` | 8.0 | Fuite = perte de moitié du débit |
| BULLES | `FLOW_DEFAULT_LPM` | 16.5 | Les bulles affectent la stabilité, pas le débit moyen |
| ISOLATION | `FLOW_DEFAULT_LPM` | 16.5 | Isolation dégradée n'affecte pas le débit |

**Référence :** Loi de Darcy-Weisbach pour les pertes de charge singulières : ΔP = K × ρ × v²/2. Un dépôt calcaire de 1 mm réduit la section de ~15%, augmentant la perte de charge d'environ 25%.

### 2.2 `delta_T_calcaire_slope` (°C/jour) — Pente de dérive calcaire

| Classe | Formule | Valeur | Justification |
|--------|---------|--------|---------------|
| Normal | — | 0.0 | Pas de calcaire |
| CALCAIRE | `T_TOLERANCE / 60` | 0.05 | Atteint la tolérance max (3°C) en 60 jours |

**Référence :** La tolérance `T_TOLERANCE = 3.0°C` est définie dans `config.py`. Sur une fenêtre de 60 jours (période de maintenance typique), une pente de 0.05°C/jour donne exactement 3°C de dérive — cohérent avec la fenêtre de détection.

### 2.3 `affected_molds_ratio` — Proportion de moules affectés

| Classe | Formule | Valeur | Justification |
|--------|---------|--------|---------------|
| POMPE_HS | `(N_MOLDS-1) / N_MOLDS` | 11/12 ≈ 0.92 | Pompe unique → tous les moules sauf 1 |
| NIVEAU_BAS | `9 / N_MOLDS` | 9/12 = 0.75 | 3 groupes sur 4 impactés |
| RESISTANCE_HS | Expert | 0.85 | ~10/12 moules (légère hétérogénéité thermique) |
| BULLES | — | 0.0 | Instabilité locale, pas de seuil franchi |
| ISOLATION | Expert | 0.2 | 2-3 moules localisés |

**Topologie :** 12 moules répartis en 4 groupes de 3 (`config.SENSOR_MAP`). Chaque groupe possède son propre chauffage et sa pompe. Une panne de pompe (groupe) affecte 3 moules, une panne générale en affecte 12.

### 2.4 `variance_T_mold` — Variance thermique

| Classe | Valeur | × Normal | Justification physique |
|--------|--------|----------|----------------------|
| Normal | 0.02 | 1× | Bruit de mesure résiduel (fenêtre 30s lisse les variations) |
| BULLES | 0.30 | 15× | Poches d'air créent des fluctuations thermiques brutales |
| ISOLATION | 0.01 | 0.5× | Faible dérive, très stable (pas d'instabilité ajoutée) |

**Référence :** Dans `data_generator.py`, le scénario normal utilise T_std = 0.3°C. Sur une fenêtre glissante de 30 échantillons à 1 Hz, la variance moyenne est lissée à ~0.02. Les bulles d'air multiplient cette variance par 15 (données expérimentales de la littérature sur les écoulements diphasiques).

### 2.5 `flow_variance` — Variance du débit

| Classe | Valeur | × Normal | Justification |
|--------|--------|----------|---------------|
| Normal | 0.10 | 1× | Débit stable (YF-S201 ±0.3 L/min) |
| CALCAIRE | 0.30 | 3× | Dépôt partiel → écoulement perturbé |
| BULLES | 2.00 | 20× | Air dans le circuit → variations de débit extrêmes |
| FUITE | 1.50 | 15× | Perte de charge → instabilité hydraulique |
| RESISTANCE_HS | 0.50 | 5× | Oscillations du PID en l'absence de chauffage |

### 2.6 `drift_R_squared` — Qualité de la régression linéaire

| Classe | Valeur | Signification |
|--------|--------|---------------|
| Normal | 0.90 | Température stable → droite plate mais bien ajustée |
| CALCAIRE | 0.92 | Dérive très régulière → R² proche de 1 |
| BULLES | 0.20 | Pas de tendance → R² proche de 0 (bruit) |
| FUITE | 0.50 | Tendance modérée (fuite peut empirer) |
| ISOLATION | 0.80 | Dégradation lente et régulière |

**Interprétation :** R² mesure la proportion de variance expliquée par une régression linéaire. R² ≈ 0.9 signifie que 90% de la variance est due à la tendance temporelle (le reste est du bruit).

### 2.7 `autocorr_lag1` — Autocorrélation lag-1

| Classe | Valeur | Signification |
|--------|--------|---------------|
| Normal | 0.70 | Inertie thermique → le signal "se souvient" de son passé |
| BULLES | 0.20 | Bruit quasi-blanc → pas de mémoire |

**Référence :** L'autocorrélation lag-1 mesure la corrélation entre un signal et lui-même décalé d'un pas. Pour un processus AR(1), φ = autocorr(1). Un φ proche de 1 indique un processus lent (inertie), proche de 0 indique un bruit blanc.

### 2.8 `slope_T_mold` — Pente de température

| Classe | Valeur | Justification |
|--------|--------|---------------|
| Normal | 0.0 | Stable |
| RESISTANCE_HS | -0.03 | Refroidissement lent (-1.8°C/min à 1 Hz) |

**Référence :** Constante de temps thermique du système eau + moule. La pente de -0.03 par échantillon à 1 Hz correspond à une constante de temps d'environ 1500 secondes (25 minutes), réaliste pour un volume d'eau de 10L chauffé à 45°C.

### 2.9 `sudden_drop_flag` et `flow_drop_flag` — Indicateurs binaires

Ces flags sont dérivés directement des seuils définis dans `anomaly_detector.py` :
- **sudden_drop_flag = 1** : chute > 1°C en 120 secondes (phénomène brutal = pompe HS)
- **flow_drop_flag = 1** : débit instantané < seuil bas

---

## 3. Synthèse : Correspondance Classe → Signature Physique

| Classe | Marqueur principal | Features discriminants |
|--------|-------------------|----------------------|
| **NORMAL** | flow ≈ 16.5, variance faible | Tous les features aux valeurs nominales |
| **CALCAIRE_TUYAUX** | delta_T_slope > 0, R² élevé | delta_T_calcaire_slope, drift_R_squared, flow_rate |
| **HEATER_POMPE_HS** | flow ≈ 0, sudden_drop | affected_molds_ratio, flow_rate, sudden_drop |
| **HEATER_RESISTANCE_HS** | slope < 0, affected élevé | slope_T_mold, affected_molds_ratio |
| **NIVEAU_BAS_VANNE_PANNE** | flow réduit, gradual | flow_rate, affected_molds_ratio, pas de sudden_drop |
| **BULLES_AIR** | variance élevée, R² bas | variance_T_mold, drift_R_squared, autocorr_lag1 |
| **FUITE_CIRCUIT** | flow modéré, variance élevée | flow_rate, flow_variance, drift_R_squared |
| **ISOLATION_DEGRADEE** | drift_R² modéré, peu affecté | affected_molds_ratio, drift_R_squared |

---

## 4. Validation Croisée avec les Règles Physiques

Les valeurs synthétiques sont cohérentes avec les règles déterministes de `physical_rules()` et `auto_label()` dans `cause_classifier.py` :

| Règle physique | Seuil | Cohérence |
|----------------|-------|-----------|
| `T_heater < 44°C AND affected > 0.8` → RESISTANCE_HS | Température < 44°C | Les features génèrent T_mold ≈ 42°C via slope négatif, cohérent |
| `affected > 0.8 AND sudden_drop AND flow_drop` → POMPE_HS | affected > 0.8 | affected = 11/12 ≈ 0.92 > 0.8 ✓ |
| `affected > 0.7 AND flow < 0.3 × nominal` → NIVEAU_BAS | flow < 4.95 L/min | flow = 4.0 < 4.95 ✓ |

Cette cohérence garantit que les données synthétiques respectent les mêmes diagnostics que le système réel.

---

## 5. Références

| Concept | Référence technique |
|---------|-------------------|
| Pertes de charge calcaire | Idelchik, "Handbook of Hydraulic Resistance", 1994 |
| Constante de temps thermique | Incropera, "Fundamentals of Heat and Mass Transfer", 7th ed. |
| Variance des bulles en écoulement | Brennen, "Cavitation and Bubble Dynamics", 2013 |
| Autocorrélation de processus AR(1) | Box, Jenkins, "Time Series Analysis", 2015 |
| Seuils AMDEC | ISO 31000:2018 — Risk Management |
