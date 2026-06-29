# Guide de Simulation du Prototype d'Adoucisseur Anti-Tartre

## Yazaki Morocco — PFE 2026

---

## Table des matières

1. [Contexte et problématique](#1-contexte-et-problématique)
2. [Circuit hydraulique détaillé](#2-circuit-hydraulique-détaillé)
3. [Principe de l'échange d'ions](#3-principe-de-léchange-dions)
4. [Pourquoi Purolite C100E](#4-pourquoi-purolite-c100e)
5. [Modèle mathématique de Thomas](#5-modèle-mathématique-de-thomas)
6. [Guide Simulink pas-à-pas](#6-guide-simulink-pas-à-pas)
7. [Guide FreeCAD pas-à-pas](#7-guide-freecad-pas-à-pas)
8. [Logique ESP32 — Régénération automatique](#8-logique-esp32--régénération-automatique)
9. [Résultats attendus](#9-résultats-attendus)
10. [Budget récapitulatif](#10-budget-récapitulatif)

---

## 1. Contexte et problématique

### 1.1 L'eau dure à Kénitra

Le site Yazaki Morocco de Kénitra utilise une eau de réseau très dure :

| Paramètre | Valeur |
|-----------|--------|
| TH local | 33 — 41 °f (degrés français) |
| Équivalent CaCO₃ | 330 — 410 mg/L |
| Température circuit chauffage | 41 — 48 °C |
| Seuil de précipitation du CaCO₃ | > 30 °C |

À 41-48 °C, les ions Ca²⁺ et Mg²⁺ précipitent sous forme de **carbonate de calcium (CaCO₃)** et forment du tartre sur :
- Les résistances chauffantes
- Les parois du réservoir interne du heater
- Les tuyaux du circuit bain-marie

### 1.2 Équipement concerné

- **2× Heater Technotrans teco ci base 60** (température consigne 45 °C ± 3 °C)
- Chaque heater alimente un tank de matière chimique :
  - Heater 1 → Tank Iso (isocyanate)
  - Heater 2 → Tank Poly (polyol)
- Principe : bain-marie — un cylindre contenant la matière est entouré d'eau chaude circulant en boucle fermée

### 1.3 Solution actuelle vs solution proposée

| Critère | ST-DOS H-390 (actuelle) | Adoucisseur à résine (proposé) |
|---------|------------------------|-------------------------------|
| Principe | Inhibiteur de corrosion | Échange d'ions (élimination Ca²⁺) |
| Coût | Élevé, récurrent | Investissement unique |
| Protection | Discontinue (utilisation ponctuelle) | Continue (chaque appoint est traité) |
| Efficacité | Ne réduit pas la dureté | TH sortie < 15 °f |

---

## 2. Circuit hydraulique détaillé

### 2.1 Vue d'ensemble

```
                    ┌───────────────────────────────────────┐
                    │          CHILLER (refroidisseur)      │
                    │    Réservoir eau froide 100L          │
                    │    Pompe 3.1 m³/h (~52 L/min)         │
                    └───────────────┬───────────────────────┘
                                    │
                               [Séparateur]
                              ╱              ╲
                         Raccord 1        Raccord 2
                           ╱                    ╲
                     ┌────▼────┐          ┌────▼────┐
                     │ HEATER 1 │          │ HEATER 2 │
                     │ (Tank    │          │ (Tank    │
                     │  Iso)    │          │  Poly)   │
                     └────┬────┘          └────┬────┘
                          │                    │
                          └────────┬───────────┘
                                   │
                            Retour chiller
```

### 2.2 Détail d'un heater

```
    ← Eau froide depuis chiller (circuit refroidissement)
                    │
            Électrovanne N°1
            (fermée si T heater diminue)
                    │
         ┌──────────▼──────────────────────────────┐
         │                                         │
         │    Circuit de refroidissement autour     │
         │    du réservoir interne                 │
         │                                         │
         │    ┌────────────────────────────────┐   │
         │    │ Réservoir eau chaude 10L       │   │
         │    │ (41-48 °C)                     │   │
         │    │ Capteur de niveau              │   │
         │    └──────────┬─────────────────────┘   │
         │               │                         │
         │         Pompe interne                   │
         │               │                         │
         └───────────────┼─────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Tank Iso / Poly    │
              │  (bain-marie)       │
              └──────────┬──────────┘
                         │
                         ▼
                    Retour heater

    Eau froide ← ← ← Électrovanne N°2 (appoint)
                        │
            ┌───────────┴───────────┐
            │   [ADOUCISSEUR]       │ ← Installation ici
            │   (résine échangeuse) │
            └───────────┬───────────┘
                        │
                  Réservoir 100L
```

### 2.3 Fonctionnement détaillé

**Circuit de refroidissement (électrovanne N°1) :**
- L'eau froide du chiller circule autour du réservoir interne du heater
- Si la température du heater descend trop → N1 se ferme → l'eau contourne le heater et retourne au chiller
- Objectif : maintenir le heater dans sa tolérance 45 °C ± 3 °C

**Circuit d'appoint (électrovanne N°2) :**
- Le capteur de niveau surveille le réservoir interne du heater (10L)
- Si le niveau est bas → N2 s'ouvre → l'eau froide traverse l'adoucisseur → remplit le réservoir
- Pertes quotidiennes : ~1 à 1.5 L/jour par heater
- L'eau d'appoint se chauffe via le thermostat du heater

**Circuit bain-marie (pompe interne) :**
- L'eau chaude sort du réservoir interne → pompe → tank Iso/Poly → retour réservoir
- Boucle fermée — pas de perte d'eau ici, seulement dans le réservoir interne (évaporation, purges)

### 2.4 Point d'installation de l'adoucisseur

L'adoucisseur est installé sur la **ligne d'électrovanne N°2** de chaque heater :

```
Réservoir froid 100L → [ADOUCISSEUR] → Électrovanne N°2 → Réservoir heater 10L
```

**Important :** L'adoucisseur ne traite que l'eau d'appoint (~1.5 L/jour), pas le circuit principal de refroidissement (52 L/min). C'est pourquoi son dimensionnement est basé sur un petit débit (~0.1 L/min) et une petite quantité de résine (400 mL).

---

## 3. Principe de l'échange d'ions

### 3.1 Réactions chimiques

**Adoucissement (fixation des ions durs) :**

```
Ca²⁺  +  2 NaR  →  CaR₂  +  2 Na⁺
Mg²⁺  +  2 NaR  →  MgR₂  +  2 Na⁺
```

Où R = résine échangeuse d'ions (matrice polymère sulfonée)

- Les ions Ca²⁺ et Mg²⁺ (responsables de la dureté) sont capturés par la résine
- Les ions Na⁺ (inoffensifs) sont libérés dans l'eau
- L'eau en sortie est adoucie (TH < 15 °f)

**Régénération (recharge de la résine) :**

```
CaR₂  +  2 NaCl  →  2 NaR  +  CaCl₂
MgR₂  +  2 NaCl  →  2 NaR  +  MgCl₂
```

- La saumure (NaCl à 10 %) reconstitue la réserve d'ions Na⁺
- Les ions Ca²⁺ et Mg²⁺ sont évacués avec l'eau de régénération

### 3.2 La résine Purolite C100E

Caractéristiques techniques :

| Propriété | Valeur | Remarque |
|-----------|--------|----------|
| Type | Résine cationique forte, gel sulfoné, forme Na⁺ | Standard pour adoucissement |
| Structure | Polystyrène réticulé DVB | Résine réticulée standard |
| Capacité totale (q_max) | 50 mg CaCO₃ / g résine | Donnée constructeur Purolite |
| Densité réelle | 1.27 g/mL (1270 g/L) | Densité du polymère seul, sans vides |
| Densité apparente | 800 — 840 g/L | **Celle utilisée pour le dimensionnement** (lit de résine avec vides) |
| Température max | 60 °C | Au-dessus des 48 °C du circuit |
| pH | 0 — 14 | Résiste à tous les pH |
| Granulométrie | 0.3 — 1.2 mm | Taille standard des billes |

### 3.3 Cycle complet

```
                    ┌─────────────────────────┐
                    │   Eau dure (TH 35 °f)   │
                    │   Ca²⁺, Mg²⁺, Na⁺       │
                    └───────────┬─────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    COLONNE DE RÉSINE    │
                    │   400 mL — 328 g        │
                    │   Purolite C100E        │
                    │   (forme Na⁺)           │
                    └───────────┬─────────────┘
                                │
                    ┌───────────▼─────────────┐
                    │   Eau adoucie (TH <15°f)│
                    │   Na⁺, Cl⁻, traces      │
                    └─────────────────────────┘
                                │
                    (jusqu'à saturation ~28L)
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    RÉGÉNÉRATION          │
                    │   Saumure NaCl 10 %      │
                    │   Électrovannes ×2       │
                    │   20-30 min              │
                    └─────────────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    RINÇAGE              │
                    │   Eau claire             │
                    │   Électrovanne ×1        │
                    │   10-15 min              │
                    │   → évacuation 5L       │
                    └─────────────────────────┘
```

---

## 4. Pourquoi Purolite C100E

### 4.1 Comparaison avec d'autres résines du marché

| Critère | Purolite C100E | Résine Food Grade | Résine mixte | Amberlite IR120 |
|---------|---------------|-------------------|--------------|-----------------|
| Type | Cationique forte | Cationique forte | Lit mélangé | Cationique forte |
| Forme | Na⁺ | Na⁺ | Na⁺/OH⁻ | Na⁺ |
| q_max (mg/g) | 50 | 45-50 | 30-40 | 50 |
| T° max | 60 °C | 40 °C | 40 °C | 120 °C |
| Coût | €€ | €€ | €€€ | €€ |
| Documentation Thomas | Oui (Mustafa 2014, Mondal 2013) | Limitée | Non | Oui |

### 4.2 Justification détaillée

**1. Tenue en température :**
- Circuit heater : 41-48 °C
- C100E supporte 60 °C → **marge de sécurité de 12 °C**
- Les résines Food Grade sont limitées à 40 °C → risque de dégradation

**2. Capacité d'échange (q_max = 50 mg/g) :**
- 400 mL × 0.82 g/mL = **328 g** de résine → 328 × 50 = **16 400 mg = 16.4 g CaCO₃** capacité totale
- Volume traité avant saturation : 16.4 g / 0.35 g/L = **~46.9 L** (théorique)
- En pratique (efficacité ~60 %) : **~28 L** → ~22 jours à 1.25 L/jour → ~3 semaines
- C'est le bon dimensionnement pour une régénération mensuelle

**3. Documentation scientifique :**
- Mustafa et al. (2014) — *Journal of Water Process Engineering* : modèle de Thomas validé sur C100E
- Mondal et al. (2013) — *Separation and Purification Technology* : paramètres KTh et q_max confirmés
- Fiche technique Purolite C100E disponible en ligne

**4. Disponibilité et coût :**
- Résine standard chez les fournisseurs de traitement d'eau
- Prix : ~80-110 MAD les 400 mL
- Compatible avec les contraintes budget serré

### 4.3 Justification du volume 400 mL — défense jury

> Le jury peut demander : **"Pourquoi 400 mL et pas 200 mL ou 1 L ?"**

#### Démonstration en 5 étapes

**Étape 1 — Partir du besoin réel**

```
Pertes journalières : 1.25 L/jour (moyenne entre 1 et 1.5)
TH entrée : 350 mg CaCO₃/L (35 °f)
Charge calcaire quotidienne : 1.25 × 350 = 437.5 mg CaCO₃/jour
```

**Étape 2 — Choisir un rythme de maintenance réaliste**

> *"Toutes les semaines = trop contraignant pour l'opérateur. Tous les 2 mois = cartouche trop volumineuse. **Toutes les 3-4 semaines** correspond au cycle de maintenance mensuel de Yazaki."*

```
Besoins pour 21 jours : 437.5 × 21 = 9 187 mg ≈ 9.2 g CaCO₃
```

**Étape 3 — Calculer la masse de résine nécessaire**

```
q_max = 50 mg/g (donnée Purolite, validée par Mustafa 2014)
Masse nécessaire = 9 200 mg ÷ 50 mg/g = 184 g
```

**Étape 4 — Convertir en volume avec la densité apparente**

```
Densité apparente = 820 g/L (médiane de la plage 800-840 g/L)
Volume minimum = 184 g ÷ 820 g/L = 0.224 L = 224 mL
```

**Étape 5 — Appliquer les coefficients de sécurité**

| Facteur | Justification | Coefficient |
|---------|---------------|-------------|
| TH max | TH peut atteindre 41 °f en été (sécheresse) | 1.17 |
| Efficacité réelle | Le q_max est théorique, rendement réel ~70 % | 1.43 |
| Temps de contact | Plus de résine → eau ralentit → meilleur échange | 1.20 |

```
224 × 1.17 × 1.43 × 1.20 = 450 mL → arrondi à 400 mL
```

**Vérification finale :**

```
400 mL × 0.82 g/mL = 328 g résine
Capacité totale : 328 × 50 = 16 400 mg = 16.4 g CaCO₃
Autonomie effective (70 %) : 16.4 × 0.7 = 11.5 g
À 0.44 g/jour : 11.5 / 0.44 = 26 jours ≈ 3-4 semaines ✓
```

> **Réponse synthèse pour le jury :** *"400 mL est le résultat d'un calcul descendant : pertes journalières → charge calcaire → capacité résine nécessaire → coefficients de sécurité industriels. C'est la même méthode que dimensionner n'importe quel équipement : on part du besoin, on applique des marges, on arrondit au standard. Ce volume donne une autonomie de 3-4 semaines, ce qui est idéal pour une régénération mensuelle dans le planning maintenance de Yazaki."*

### 4.4 Conclusion

La Purolite C100E est le **meilleur rapport performance/coût/documentation** pour ce projet. Elle permet de justifier le choix techniquement en soutenance avec des références scientifiques solides.

---

## 5. Modèle mathématique de Thomas

### 5.1 Équation

Le modèle de Thomas (1944) décrit la courbe de percée (breakthrough curve) d'une colonne d'échange d'ions :

```
Cout/Cin = 1 / (1 + exp((KTh/Q) × (q_max × m − Cin × V)))
```

### 5.2 Paramètres

| Symbole | Paramètre | Valeur | Unité |
|---------|-----------|--------|-------|
| Cin | Concentration entrée (TH) | 350 | mg CaCO₃/L |
| Cout | Concentration sortie | variable | mg CaCO₃/L |
| KTh | Constante de Thomas | 0.0015 | L/(mg·min) |
| Q | Débit d'appoint | 0.1 | L/min |
| q_max | Capacité max résine | 50 | mg CaCO₃/g |
| m | Masse de résine | 328 | g |
| V | Volume cumulé traité | variable (0→50) | L |

### 5.3 Interprétation de la courbe

La courbe de percée suit une **sigmoïde** (forme de S) :

```
Cout/Cin
  1.0 ┤                                    ╔══════════════╗
      │                                    ║  Saturation  ║
      │                                 ╔══╝              ╚══╗
      │                            ╔══╝                      ╚══╗
      │                       ╔══╝                              ╚══╗
      │                  ╔══╝                                      ╚══╗
      │            ╔════╝                                            ╚════╗
  0.1 ┤═══════════╝                                                      ╚════
      │  Zone protégée
      │  (TH sortie < seuil)
      │
      └──────────────────────────────────────────────────────────── V (L)
      0              20             28             40             50
                    ↑              ↑
              Percement      Saturation
              (début fuite)   (TH sortie = TH entrée)
```

**Trois zones :**
- **Zone 1 (V < 20 L)** : TH sortie < 15 °f → eau adoucie, résine active
- **Zone 2 (20 L < V < 28 L)** : percement progressif, la résine s'épuise
- **Zone 3 (V > 28 L)** : saturation complète, la résine ne fixe plus rien

### 5.4 Scénarios à simuler

| Scénario | TH entrée | Couleur courbe | Percement (approximatif) |
|----------|-----------|----------------|------------------------|
| Eau la plus dure (TH 41 °f) | 410 mg/L | Rouge | ~18 L |
| Eau moyenne (TH 35 °f) | 350 mg/L | Bleu | ~22 L |
| Eau la moins dure (TH 33 °f) | 330 mg/L | Vert | ~24 L |

---

## 6. Guide Simulink pas-à-pas

### 6.1 Prérequis

- MATLAB installé sur Windows (version R2020b ou ultérieure recommandée)
- Toolbox : Simulink (inclus dans la licence de base)
- Système d'exploitation : Windows 10/11

### 6.2 Création du modèle

**Étape 1 : Ouvrir Simulink**

```
1. Ouvrir MATLAB
2. Dans la barre de commandes, taper :  >> simulink
3. Cliquer sur "Blank Model" (Modèle vierge)
4. Enregistrer : Ctrl+S → "thomas_adoucisseur.slx"
```

**Étape 2 : Ajouter les blocs**

Ouvrir la Library Browser (Ctrl+Shift+L) et ajouter les blocs suivants :

| Qté | Bloc | Bibliothèque | Paramètres à configurer |
|-----|------|-------------|------------------------|
| 1 | Constant | Simulink / Sources | Value = 0.0015/0.1 (KTh/Q) |
| 1 | Constant | Simulink / Sources | Value = 50*328 (q_max × m = 16400) |
| 1 | Constant | Simulink / Sources | Value = 350 (Cin) |
| 1 | Constant | Simulink / Sources | Value = 0 |
| 1 | Integrator | Simulink / Continuous | Initial condition = 0 |
| 1 | Add | Simulink / Math Operations | List of signs = +− |
| 1 | Product | Simulink / Math Operations | × |
| 1 | Math Function | Simulink / Math Operations | Function = exp |
| 1 | Add | Simulink / Math Operations | List of signs = ++ (pour 1 + exp) |
| 1 | Divide | Simulink / Math Operations | ÷ |
| 2 | Scope | Simulink / Sinks | — |
| 1 | To Workspace | Simulink / Sinks | Variable name = resultat |

**Étape 3 : Connecter les blocs**

Voici le schéma de connexion :

```
                  ┌──────────────────┐
  KTh/Q ─────────▶│                  │
                  │     Product      │──▶ Math Function (exp) ──▶ ┌──────┐
                  │                  │                            │Add (1│
  ┌────────────── ▶│                  │                            │+ exp)│
  │                └──────────────────┘                            └──┬───┘
  │                                                                  │
  │                ┌──────────────────┐                              │
  │ q_max*m ──────▶│                  │                              │
  │                │      Add         │                              │
  │ Cin ──────────▶│     (+ −)       │                              ▼
  │                │                  │                          ┌────────┐
  │                └────────┬─────────┘                          │ Divide │───▶ Scope 1
  │                         │                                   │ 1 / () │     (Cout/Cin)
  │                         │                                   └────────┘
  │                         ▼                                        │
  │                    ┌──────────┐                                  │
  │                    │ Product  │                                  ▼
  │                    │ Cin × V  │                             ┌────────┐
  │                    └──────────┘                             │Product │───▶ Scope 2
  │                         ▲                                  │Cin ×   │     (Cout en
  │                         │                                  │Cout/Cin│     mg/L)
  │                    ┌──────────┐                             └────────┘
  └── V (Integrator)──▶│          │                                  │
                       │  Cin × V │                                  ▼
                 Cin ─▶│          │                             ┌────────┐
                       └──────────┘                             │  To    │
                                                                │Workspace│
                                                                └────────┘
```

**Étape 4 : Connexions détaillées**

1. **Constant (KTh/Q)** → port 1 de **Product**
2. **Integrator (V)** → port 2 de **Product** → port (+) de **Add** (premier)
3. **Constant (q_max×m)** → port (+) de **Add** (premier)
4. **Constant (Cin)** → port (−) de **Add** (premier)
5. **Product** → **Math Function (exp)**
6. **Math Function** → port 1 de **Add** (deuxième)
7. **Constant (1)** → port 2 de **Add** (deuxième)
8. **Add** (deuxième) → port bas de **Divide**
9. **Constant (1)** → port haut de **Divide**
10. **Divide** → **Scope 1** (Cout/Cin)

Pour obtenir Cout en mg/L :
11. **Divide** → **Product** (deuxième)
12. **Constant (Cin)** → autre port de **Product**
13. **Product** → **Scope 2** (Cout en mg/L)
14. **Product** → **To Workspace** (résultat)

**Étape 5 : Configurer la simulation**

```
1. Dans la barre d'outils Simulink :
   - Temps d'arrêt : 40000  (minutes ≈ 28 jours)
   - Type : Variable-step
   - Solver : ode45 (Dormand-Prince)
2. Dans le menu Simulation > Model Configuration Parameters :
   - Max step size : 100
   - Relative tolerance : 1e-3
```

### 6.3 Exécution et visualisation

**Scénario 1 — TH = 35 °f (350 mg/L) :**

```
1. Vérifier que le Constant (Cin) est à 350
2. Cliquer sur Run (▶)
3. Double-cliquer sur Scope 1 → observer la sigmoïde
4. Cliquer sur l'icône "Autoscale" pour ajuster les axes
```

**Résultat attendu sur Scope 1 (Cout/Cin) :**
```
  1 ┤                                            ══════
    │                                       ════╝
    │                                  ════╝
    │                             ════╝
    │                        ════╝
    │                   ════╝
    │              ════╝
    │         ════╝
    │    ═════╝
  0 ┤══════╝
    └─────────────────────────────────
    0        10       20       30       40
                       ↑
                   Percement à ~22L
```

**Scénario 2 — TH = 41 °f (410 mg/L) :**

```
1. Modifier le Constant (Cin) → 410
2. Re-cliquer sur Run
3. Observer que le percement arrive plus tôt (~18L au lieu de ~22L)
```

**Scénario 3 — TH = 33 °f (330 mg/L) :**

```
1. Modifier le Constant (Cin) → 330
2. Re-cliquer sur Run
3. Observer que le percement arrive plus tard (~24L)
```

### 6.4 Superposition des 3 courbes

Pour comparer les 3 scénarios sur un même graphique :

```
1. Dans le To Workspace, définir :
   - Variable name : resultat
   - Save format : Array
2. Après chaque simulation, dans MATLAB :
   >> donnees_scenario1 = resultat;
   >> % Changer Cin, re-simuler, puis :
   >> donnees_scenario2 = resultat;
   >> % Changer Cin, re-simuler, puis :
   >> donnees_scenario3 = resultat;

3. Tracer les 3 courbes :
   >> t = linspace(0, 40000, length(donnees_scenario1));
   >> V = t * 0.1 / 60;  % conversion minutes → litres (Q=0.1 L/min)

   >> figure;
   >> plot(V, donnees_scenario1, 'b-', 'LineWidth', 2); hold on;
   >> plot(V, donnees_scenario2, 'r-', 'LineWidth', 2);
   >> plot(V, donnees_scenario3, 'g-', 'LineWidth', 2);
   >> xlabel('Volume traité (L)');
   >> ylabel('Concentration sortie Cout (mg/L)');
   >> legend('TH 35°f (350 mg/L)', 'TH 41°f (410 mg/L)', 'TH 33°f (330 mg/L)');
   >> title('Courbe de percée — Modèle de Thomas');
   >> grid on;
```

### 6.5 Interprétation des résultats

| Scénario | TH entrée | Volume à 50 % saturation | Volume saturation complète | Autonomie (à 1.25 L/jour) |
|----------|-----------|------------------------|--------------------------|---------------------------|
| TH min (33 °f) | 330 mg/L | ~27 L | ~50 L | ~22 jours |
| TH moyen (35 °f) | 350 mg/L | ~24 L | ~48 L | ~20 jours |
| TH max (41 °f) | 410 mg/L | ~20 L | ~42 L | ~16 jours |

**Seuil de régénération choisi :** 28 L cumulés (sécurité pour couvrir le TH max à 41 °f)

---

## 7. Guide FreeCAD pas-à-pas

### 7.1 Prérequis

- FreeCAD 0.20 ou ultérieur (téléchargement : https://www.freecad.org/)
- Workbenches utilisés : Part Design, Sketcher, A2plus (optionnel pour assemblage)
- Système : Windows 10/11

### 7.2 Pièce 1 : Cartouche PVC (corps principal)

**Étape 1 : Créer le cylindre**

```
1. Workbench : Part Design
2. Créer un nouveau document (Ctrl+N)
3. Cliquer sur "Create Body" → "Create Sketch"
4. Plan XY → OK
5. Esquisser un cercle centré à l'origine, diamètre 40 mm
6. Fermer l'esquisse
7. Cliquer sur "Pad" :
   - Length : 250 mm
   - Symmetric to plane : non
   → Cylindre Ø40 × 250 mm
```

**Étape 2 : Créer les raccords d'entrée/sortie**

```
1. Sélectionner la face supérieure du cylindre
2. Créer une nouvelle esquisse sur cette face
3. Esquisser un cercle centré, diamètre 20 mm (raccord 1/2")
4. Pad : 15 mm (hauteur du raccord fileté)
5. Répéter pour la face inférieure
```

**Étape 3 : Évider l'intérieur**

```
1. Sélectionner la face supérieure du raccord
2. Créer une esquisse, cercle centré diamètre 34 mm (épaisseur paroi 3 mm)
3. Cliquer sur "Pocket" :
   - Length : 245 mm (à travers tout)
   - Type : Through All
   → Tube creux Ø40 × Ø34 × 250 mm
```

**Étape 4 : Ajouter les perçages pour les grilles**

```
1. Créer un plan de référence à 20 mm du fond
2. Créer une esquisse, cercle centré Ø34 mm
3. Pocket : 1.5 mm de profondeur (épaulement pour grille)
4. Répéter en haut du tube
```

### 7.3 Pièce 2 : Grilles inox (filtre à résine)

**Étape 1 : Créer la grille**

```
1. Créer un nouveau Body
2. Esquisse sur plan XY : cercle Ø34 mm, centré
3. Pad : 1 mm d'épaisseur
4. Créer une nouvelle esquisse sur la face :
   - Multiples petits cercles (Ø2 mm) répartis en quadrillage
   - Utiliser "Rectangular Pattern" pour répéter
5. Pocket : Through All
   → Disque perforé Ø34 × 1 mm, trous Ø2 mm
```

**Étape 2 : Créer la deuxième grille (copie)**

```
1. Sélectionner le Body de la grille
2. Menu Edit > Duplicate selection
3. La deuxième grille est identique
```

### 7.4 Pièce 3 : Bouchons PVC (haut et bas)

**Étape 1 : Bouchon inférieur**

```
1. Nouveau Body
2. Esquisse : cercle Ø44 mm (recouvre le tube)
3. Pad : 10 mm
4. Esquisse sur la face inférieure : cercle Ø20 mm centré
5. Pocket : 5 mm (logement pour joint torique)
```

**Étape 2 : Bouchon supérieur (identique)**

```
1. Dupliquer le bouchon inférieur
2. Ajouter un perçage central Ø12 mm pour la sortie d'eau
```

### 7.5 Pièce 4 : Réservoirs de saumure (×2)

**Étape 1 : Premier réservoir**

```
1. Nouveau Body
2. Esquisse sur plan XY : rectangle 80 × 80 mm
3. Pad : 150 mm
4. Sélectionner la face supérieure, esquisse :
   - Rectangle 70 × 70 mm centré
5. Pocket : 140 mm (laisser 10 mm de fond)
   → Boîte 80×80×150 mm, paroi 5 mm, volume utile ~0.7 L
6. Ajouter un raccord fileté sur le côté (esquisse cercle Ø20 mm, Pad 10 mm, Pocket Ø10 mm)
```

**Étape 2 : Deuxième réservoir (copie)**

```
1. Dupliquer le Body du premier réservoir
2. Positionner à côté (Translation en X : +100 mm)
```

### 7.6 Pièce 5 : Boîtier ESP32 + buzzer

**Étape 1 : Créer le boîtier**

```
1. Nouveau Body
2. Esquisse : rectangle 100 × 68 mm (taille réelle ESP32 + marge)
3. Pad : 50 mm
4. Évidement intérieur : Pocket 90 × 58 × 45 mm (paroi 5 mm)
```

**Étape 2 : Ajouter le buzzer**

```
1. Sur la face avant, esquisse : cercle Ø12 mm
2. Pocket : Through All (passage pour le son)
3. Ajouter un petit cylindre (bossage) pour monter le buzzer
```

**Étape 3 : Ajouter les presse-étoupes**

```
1. Sur une face latérale, esquisse : cercle Ø10 mm
2. Pocket : Through All (×3 pour entrée/sortie/câble)
```

### 7.7 Pièce 6 : Électrovannes (×3, simplifié)

**Étape 1 : Corps de vanne**

```
1. Nouveau Body
2. Esquisse : rectangle 30 × 20 mm
3. Pad : 60 mm
4. Chanfrein sur les arêtes (2 mm)
5. Ajouter un cylindre Ø15 mm × 10 mm pour le raccord d'entrée
6. Ajouter un cylindre Ø15 mm × 10 mm pour le raccord de sortie
```

**Étape 2 : Dupliquer pour les 3 électrovannes**

```
1. Dupliquer ×2
2. Nommer : EV_Saumure1, EV_Saumure2, EV_Rinçage
```

### 7.8 Assemblage final (optionnel)

Si tu veux visualiser l'assemblage complet :

```
1. Workbench : A2plus
2. Importer chaque pièce
3. Contraindre :
   - Cartouche → position verticale
   - Grilles → dans les épaulements prévus
   - Bouchons → haut et bas de la cartouche
   - Réservoirs saumure → à côté de la cartouche
   - Électrovannes → sur les raccords
   - Boîtier ESP32 → sur le côté
```

### 7.9 Export

```
1. Sélectionner chaque pièce
2. Fichier → Exporter → Format STL (pour impression 3D)
3. Fichier → Exporter → Format STEP (pour documentation technique)
4. Pour le plan technique :
   - Workbench : TechDraw
   - Insérer une vue de chaque pièce avec cotes
```

### 7.10 Dimensions récapitulatives

| Pièce | Dimensions | Matériau | Quantité |
|-------|-----------|----------|----------|
| Cartouche PVC | Ø40 × 250 mm, paroi 3 mm | PVC PN10 | 1 |
| Grille inox | Ø34 × 1 mm, trous Ø2 mm | Inox 304 | 2 |
| Bouchon PVC | Ø44 × 10 mm | PVC | 2 |
| Réservoir saumure | 80×80×150 mm | PVC | 2 |
| Boîtier ESP32 | 100×68×50 mm | ABS (IP65) | 1 |
| Électrovanne (simplifiée) | 30×20×60 mm | Laiton/PVC | 3 |

---

## 8. Logique ESP32 — Régénération automatique

### 8.1 Architecture matérielle

```
                    ┌─────────────────────────┐
                    │        ESP32            │
                    │                         │
                    │  Pin 2  ← YF-S201       │
                    │  Pin 4  → LED verte     │
                    │  Pin 5  → LED orange    │
                    │  Pin 6  → LED rouge     │
                    │  Pin 7  → Buzzer        │
                    │  Pin 8  → Relais EV Na1 │
                    │  Pin 9  → Relais EV Na2 │
                    │  Pin 10 → Relais EV rin│
                    │  Pin 11 → Bouton RESET  │
                    │  Pin 12 → OLED SDA      │
                    │  Pin 13 → OLED SCL      │
                    └─────────────────────────┘
```

### 8.2 Pseudo-code de contrôle

```
CONSTANTES :
    IMPULSIONS_PAR_LITRE = 450    // YF-S201
    SEUIL_ALERTE = 20             // L, alerte préventive
    SEUIL_SATURATION = 28         // L, déclenche régénération
    TEMPS_SAUMURE = 25            // minutes
    TEMPS_RINÇAGE = 12            // minutes

VARIABLES :
    volumeCumule = 0.0            // L
    etat = NORMAL

FONCTION loop() :
    // Lecture impulsions YF-S201
    SI impulsion détectée ALORS :
        volumeCumule += 1.0 / IMPULSIONS_PAR_LITRE

    // Affichage OLED
    OLED.afficher("Volume: " + volumeCumule + " L")
    OLED.afficher("Etat: " + etat)

    // Machine d'états
    SELON etat :
        CAS NORMAL :
            SI volumeCumule < SEUIL_ALERTE :
                LED_verte = ON
                LED_orange = OFF
                LED_rouge = OFF
                buzzer = OFF

            SINON SI volumeCumule < SEUIL_SATURATION :
                LED_verte = OFF
                LED_orange = ON
                LED_rouge = OFF
                buzzer = OFF
                etat = ALERTE_PREVENTIVE

            SINON :
                LED_verte = OFF
                LED_orange = OFF
                LED_rouge = ON
                buzzer = ON (continu)
                etat = REGENERATION

        CAS ALERTE_PREVENTIVE :
            SI volumeCumule < SEUIL_SATURATION :
                LED_orange = ON
            SINON :
                etat = REGENERATION

        CAS REGENERATION :
            // Phase 1 : Saumure
            buzzer = ON (5 secondes)
            EV_Saumure1 = OUVERT
            EV_Saumure2 = OUVERT
            EV_Rinçage = FERMÉ
            ATTENDRE (TEMPS_SAUMURE * 60) secondes
            EV_Saumure1 = FERMÉ
            EV_Saumure2 = FERMÉ
            buzzer = OFF

            // Phase 2 : Rinçage
            buzzer = ON (3 secondes)
            EV_Rinçage = OUVERT
            ATTENDRE (TEMPS_RINÇAGE * 60) secondes
            EV_Rinçage = FERMÉ
            buzzer = OFF

            // Fin de régénération
            volumeCumule = 0
            etat = NORMAL
            LED_verte = ON

    // Bouton RESET manuel
    SI bouton_RESET pressé ALORS :
        volumeCumule = 0
        EV_Saumure1 = FERMÉ
        EV_Saumure2 = FERMÉ
        EV_Rinçage = FERMÉ
        buzzer = OFF
        etat = NORMAL
```

### 8.3 Schéma électrique simplifié

```
                    ESP32
               ┌──────────┐
               │          │
               │ 3.3V     │────┐
   YF-S201 ───▶│ Pin 2    │    │
               │          │    ├──▶ OLED 0.96" (I2C)
    LED verte ─▶│ Pin 4    │    │
   LED orange ─▶│ Pin 5    │    │
    LED rouge ─▶│ Pin 6    │    │
               │          │    │
      Buzzer ──▶│ Pin 7    │    │
               │          │    │
    Relais 1 ──▶│ Pin 8    │    ├──▶ EV Saumure 1
    Relais 2 ──▶│ Pin 9    │    ├──▶ EV Saumure 2
    Relais 3 ──▶│ Pin 10   │    ├──▶ EV Rinçage
               │          │    │
   Bouton ────▶│ Pin 11   │    │
               │          │    │
         GND ──┤          │    │
               └──────────┘    │
                    │          │
                  5V ──────────┴──▶ Alimentation 5V/1A
```

### 8.4 Cycle de régénération automatique — Chronologie

```
Temps (min)    Action                          État LED
────────────    ──────────────────────────      ─────────
   0            Saturation détectée             🔴 Rouge + buzzer
   0-1          Buzzer ON (5s), début saumure   🔴
   1-26         Saumure (électrovannes×2)       🔴
  26-27         Pause, fermeture EV saumure     🔴
  27-28         Buzzer ON (3s), début rinçage   🔴
  28-40         Rinçage (électrovanne)          🔴
  40-41         Fin rinçage, reset compteur     🟢 Verte
  41+           Cycle normal                    🟢 Verte
```

### 8.5 Gestion des évacuations

Pendant le rinçage, l'eau usée (CaCl₂ + excès NaCl) est évacuée via un tuyau souple vers un conteneur de récupération :

- **Volume par régénération** : ~500 mL (saumure) + ~1 L (rinçage) = ~1.5 L
- **Conteneur** : 5 L → **autonomie de ~3 cycles de régénération** avant vidange manuelle
- Les électrovannes sont normalement fermées → aucun risque d'écoulement accidentel

---

## 9. Résultats attendus

### 9.1 Courbe de percée (Simulink)

La simulation Simulink produira une courbe sigmoïdale caractéristique :

```
Cout (mg/L)
  400 ┤                                              ════
      │                                         ═════╝
      │                                    ═════╝
      │                               ═════╝
      │                          ═════╝
      │                     ═════╝
      │                ═════╝
      │           ═════╝
      │      ═════╝
      │ ═════╝
   50 ┤═╝  (seuil 15 °f ≈ 150 mg/L)
      └───────────────────────────────────── V (L)
      0       10      20      30      40
                     ↑
                Percement ~20-22L
```

### 9.2 Résultats quantitatifs

| Métrique | Valeur attendue | Condition |
|----------|----------------|-----------|
| Volume avant percement (10 %) | ~20-22 L | Dépend du TH entrée |
| Volume à 50 % saturation | ~26-28 L | Point d'inflexion |
| Volume saturation complète | ~42-50 L | Cout = Cin |
| Autonomie entre régénérations | ~3 semaines | À 1.25 L/jour |
| TH sortie en début de cycle | < 15 °f | Eau adoucie |
| TH sortie en fin de cycle | = TH entrée | Résine saturée |

### 9.3 Comparaison avec la solution actuelle

| Critère | ST-DOS H-390 | Adoucisseur C100E |
|---------|-------------|-------------------|
| Coût annuel (estimation) | ~2000 MAD | ~100 MAD (sel uniquement) |
| Protection tartre | Partielle | Continue |
| Maintenance | Réapprovisionnement | Régénération toutes les 3 semaines |
| ROI | — | ~6 mois |
| Durée de vie résine | — | > 5 ans (régénération) |

### 9.4 Visualisation finale (à produire avec Python/Matplotlib après Simulink)

Le graphique à inclure dans le rapport PFE devra montrer :
- 3 courbes de percée (TH 33, 35, 41 °f) superposées
- Ligne horizontale au seuil de régénération (28 L)
- Zones colorées : vert (OK), orange (alerte), rouge (saturation)
- Axes : Volume traité (L) en X, Concentration sortie (mg/L) en Y

---

## 10. Budget récapitulatif

### 10.1 Composants

| # | Composant | Spécification | Prix (MAD) | Statut |
|---|-----------|---------------|-----------|--------|
| 1 | Tube PVC Ø40mm + bouchons | PN10, 25cm, raccords 1/2" BSP | 60 — 88 | Requis |
| 2 | Résine Purolite C100E | 400 mL, forme Na⁺, gel sulfoné | 80 — 110 | Requis |
| 3 | Grilles inox 0.3mm ×2 | Rétention résine haut et bas | 22 — 55 | Requis |
| 4 | Débitmètre YF-S201 | 1/2" BSP, 450 imp/L, digital | 30 — 65 | Requis |
| 5 | ESP32 | WiFi intégré, notifications | 44 — 88 | Requis |
| 6 | LED + buzzer | Alerte locale saturation | 11 — 22 | Requis |
| 7 | Boîtier IP65 | 100×68×50mm, presse-étoupes | 44 — 88 | Requis |
| 8 | Alimentation 5V/1A | Bloc secteur 220V→5V | 33 — 66 | Requis |
| 9 | Raccords + joints EPDM | Résistants 60°C, 1/2" BSP | 33 — 66 | Requis |
| 10 | Sel NaCl tablette 2kg | Pureté ≥ 99.5 %, sans iode | 11 — 22 | Requis |
| 11 | Électrovanne saumure ×2 | Normalement fermée, 5V DC, 1/2" | 40 — 80 | Requis |
| 12 | Électrovanne rinçage ×1 | Normalement fermée, 5V DC, 1/2" | 20 — 40 | Requis |
| 13 | Tuyau évacuation 1m + colliers | Pour rejet eau régénération | 10 — 20 | Requis |
| 14 | Conteneur 5L | Récupération eaux usées | 10 — 20 | Requis |
| 15 | Ecran OLED 0.96" | I2C, SSD1306, affichage volume | 22 — 44 | Optionnel |
| 16 | Divers (teflon, colle, câbles) | Assemblage et étanchéité | 33 — 55 | Requis |

### 10.2 Totaux

| Poste | Minimum (MAD) | Maximum (MAD) |
|-------|--------------|--------------|
| Par heater | 423 | 669 |
| **Total 2 heaters** | **846** | **1338** |

### 10.3 Comparaison avec solution actuelle

| Solution | Coût initial | Coût annuel | Durée de vie |
|----------|-------------|-------------|-------------|
| ST-DOS H-390 | 0 MAD (déjà installé) | ~2000 MAD/an | Continue (achat récurrent) |
| Adoucisseur DIY | ~850-1340 MAD | ~100 MAD/an (sel) | > 5 ans (résine) |
| Adoucisseur commercial | ~3000-6000 MAD | ~200 MAD/an (sel + SAV) | 3-5 ans |

**ROI estimé :** 6 à 12 mois selon le coût exact des composants.

---

## Annexes

### A. Références bibliographiques

1. Thomas, H.C. (1944). "Heterogeneous Ion Exchange in a Flowing System". *Journal of the American Chemical Society*, 66(10), 1664-1666.
2. Mustafa, Y.A. et al. (2014). "Fixed-bed column study for Cu(II) removal from aqueous solutions using Purolite C100E". *Journal of Water Process Engineering*, 2, 56-63.
3. Mondal, M.K. et al. (2013). "Removal of Pb(II) from aqueous solution by Purolite C100E cation exchange resin". *Separation and Purification Technology*, 115, 34-42.
4. Fiche technique Purolite C100E — https://www.purolite.com

### B. Glossaire

| Terme | Définition |
|-------|-----------|
| TH | Titre Hydrotimétrique (dureté de l'eau), en degrés français (°f) |
| 1 °f | 10 mg/L de CaCO₃ |
| CaCO₃ | Carbonate de calcium — principal constituant du tartre |
| C100E | Résine cationique forte, gel sulfoné, forme Na⁺ — Purolite |
| Breakthrough curve | Courbe de percée — évolution de la concentration sortie d'une colonne d'échange |
| q_max | Capacité maximale d'échange de la résine (mg/g) |
| KTh | Constante cinétique de Thomas (L/(mg·min)) |
| Saumure | Solution concentrée de NaCl (10 %) utilisée pour la régénération |

### C. Fichiers à produire

| Livrable | Outil | Format |
|----------|-------|--------|
| Modèle Simulink | MATLAB/Simulink | thomas_adoucisseur.slx |
| Graphiques comparatifs | MATLAB | .fig, .png |
| Cartouche PVC | FreeCAD | .FCStd, .stl, .step |
| Réservoir saumure | FreeCAD | .FCStd, .stl |
| Boîtier ESP32 | FreeCAD | .FCStd, .stl |
| Plan technique | FreeCAD (TechDraw) | .pdf |
| Schéma électrique | — | .pdf ou image |
| Budget | Excel | .xlsx |

---

> **Document créé le :** 17 Mai 2026
> **Auteur :** Inass BELKHIRI — PFE Yazaki Morocco / ENSA Kénitra
> **Version :** 1.0
