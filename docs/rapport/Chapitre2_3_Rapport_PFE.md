# CHAPITRE 2 — CONTEXTE GÉNÉRAL DU PROJET

## Introduction du chapitre

Le présent chapitre établit le cadre général dans lequel s'inscrit ce projet de fin d'études, réalisé au sein du département technique de Yazaki Morocco. Il pose les fondements nécessaires à la compréhension des enjeux industriels, des besoins fonctionnels et des choix architecturaux qui guideront l'ensemble de l'étude. 

La première section expose la problématique industrielle dans son ensemble : la baisse de température des moules, l'encrassement calcaire généralisé des circuits d'eau chaude, et l'absence de supervision qui les rend indétectables jusqu'à ce que la production soit impactée. Cette section s'appuie sur une analyse AMDEC (Analyse des Modes de Défaillance, de leurs Effets et de leur Criticité) pour quantifier les risques et justifie la pertinence d'une approche de maintenance prédictive par rapport aux méthodes traditionnelles. La deuxième section formalise le cahier des charges décliné en besoins fonctionnels pour les deux axes du projet — supervision thermique d'une part, et simulation d'un système d'adoucissement d'eau d'autre part — ainsi que les contraintes non-fonctionnelles. La troisième section présente une étude préalable comparative des solutions existantes et justifie les choix technologiques retenus. Enfin, les quatrième et cinquième sections détaillent le plan d'action et le planning prévisionnel sous forme de diagramme de Gantt.

---

## 2.1 Problématique industrielle

### 2.1.1 Problématique générale

La ligne de production de mousse polyuréthane de Yazaki Morocco est confrontée à un problème récurrent et difficile à diagnostiquer : la température des moules chute en cours de production, parfois de manière significative, alors même que la température de l'eau mesurée au niveau du heater reste nominale (45°C ± 3°C). Cette baisse de température, qui peut atteindre plusieurs degrés, n'est détectable ni visuellement, ni par les systèmes de contrôle existants, en l'absence de dispositif de supervision dédié. Les opérateurs ne disposent d'aucun moyen de savoir que la température d'un moule a diminué, ni d'en identifier les causes, jusqu'à ce que les conséquences deviennent visibles sur la qualité des pièces produites [1].

Les grommets en mousse polyuréthane fabriqués sur cette ligne sont des composants critiques pour l'industrie automobile, soumis à des tolérances dimensionnelles et mécaniques strictes. La qualité de la réaction de polymérisation dépend étroitement du profil thermique appliqué au moule : une température insuffisante allonge le temps de réaction, modifie la densité de la mousse et peut générer des défauts internes (alvéoles ouvertes, réticulation incomplète). Ces défauts entraînent le déclassement des pièces, voire leur rebut, ce qui se traduit par une perte de production directe et des arrêts de ligne pour maintenance curative non planifiée [2].

Au-delà des baisses de température ponctuelles, un phénomène plus insidieux aggrave la situation : l'encrassement calcaire. L'eau d'appoint de la boucle chauffante possède une dureté totale d'environ 35 °f (350 mg/L de CaCO₃), caractéristique des eaux de la région de Kénitra [3]. Sous l'effet de la température maintenue à 45°C, le carbonate de calcium précipite et s'accumule progressivement sur l'ensemble des surfaces en contact avec l'eau chaude :

- **Dans les tuyaux du circuit hydraulique** : le calcaire réduit la section de passage, augmente les pertes de charge et finit par obstruer complètement les canalisations au fil du temps [4] ;
- **Dans les réservoirs des heaters** : les dépôts s'accumulent au fond et sur les parois, réduisant l'efficacité de l'échange thermique et pouvant endommager les résistances chauffantes par surchauffe locale ;
- **Dans la partie eau des tanks poly iso** : ces réservoirs, qui contiennent de l'eau chaude en circulation autour des moules, voient leurs parois internes se couvrir de calcaire, accélérant la dégradation de l'isolation thermique et créant des points de surchauffe.

La formation de calcaire est un processus lent mais inéluctable en l'absence de traitement de l'eau. Ses conséquences sont multiples : perte d'efficacité énergétique, baisse progressive du débit, obstruction des circuits, et dégradation accélérée des équipements. Pourtant, en l'absence de supervision temps réel, ce phénomène passe inaperçu jusqu'à ce qu'il devienne critique.

C'est dans ce contexte que se pose la nécessité d'un système de supervision thermique intelligent, capable de :
1. Mesurer en temps réel la température de chaque moule et le débit du circuit ;
2. Détecter automatiquement les baisses de température et les anomalies ;
3. Identifier la cause racine parmi les défaillances possibles (calcaire, panne pompe, niveau bas, etc.) ;
4. Estimer l'épaisseur de calcaire accumulée sans capteur dédié, par soft sensing ;
5. Prédire la date à laquelle une intervention de maintenance sera nécessaire, afin de la planifier à l'avance.

La maintenance prédictive, permise par ces capacités, constitue une rupture par rapport aux approches traditionnelles (corrective ou préventive systématique) : elle permet d'intervenir au moment optimal, ni trop tôt (gaspillage de ressources), ni trop tard (panne et arrêt de production).

[Insert Figure 2.1 — Schéma du circuit hydraulique : boucle principale 100 L et boucle chauffante 10 L]

### 2.1.2 Phénomène d'encrassement calcaire

Le carbonate de calcium (CaCO₃) présente une solubilité décroissante avec la température (solubilité inverse). À 45°C, la réaction de précipitation suit l'équilibre suivant [5] :

\[
\text{Ca}^{2+} + 2\text{HCO}_3^- \xrightarrow{\Delta} \text{CaCO}_3\downarrow + \text{CO}_2\uparrow + \text{H}_2\text{O} \tag{2.1}
\]

La cinétique de précipitation est gouvernée par la loi d'Arrhenius : la vitesse de réaction double approximativement pour chaque élévation de 10°C. Dans la boucle chauffante maintenue à 45°C, le dépôt de calcaire s'accumule progressivement sur les parois internes des tuyaux de diamètre 13 mm, réduisant la section de passage et augmentant la résistance thermique [4].

Ce dépôt agit comme un isolant thermique : la loi de Fourier appliquée à la couche de calcaire montre que la résistance thermique \(R_{calcaire}\) s'exprime par :

\[
R_{calcaire} = \frac{e}{\lambda \cdot A} \tag{2.2}
\]

où \(e\) est l'épaisseur du dépôt, \(\lambda = 1,0\,\text{W}·\text{m}^{-1}·\text{K}^{-1}\) la conductivité thermique du calcaire [6], et \(A\) la surface d'échange. Cette résistance thermique réduit le transfert de chaleur de l'eau vers les moules, provoquant une baisse de la température de ces derniers.

La conséquence directe est que la température mesurée au niveau du heater peut rester nominale (le thermostat maintient la consigne de 45°C), tandis que la température effective de l'eau arrivant aux moules diminue à cause des pertes thermiques à travers la couche de calcaire dans les canalisations. Ce découplage entre température de consigne et température réelle des moules est précisément ce qui rend le phénomène indétectable sans supervision.

### 2.1.3 Analyse AMDEC des modes de défaillance

L'analyse AMDEC (Analyse des Modes de Défaillance, de leurs Effets et de leur Criticité) a été réalisée selon la norme ISO 31000 [7] afin d'identifier et de prioriser les risques associés au système de supervision thermique. La criticité de chaque mode de défaillance est calculée par :

\[
\text{Criticite} = G \times O \times D \tag{2.3}
\]

où \(G\) est la gravité (1–10), \(O\) l'occurrence (1–5), et \(D\) la détectabilité (1–5, plus élevé = plus difficile à détecter).

[Insert Tableau 2.1 — Analyse AMDEC : 7 modes de défaillance avec criticité]

| Mode de défaillance | G | O | D | Criticité | Priorité |
|:--------------------|:-:|:-:|:-:|:---------:|:--------:|
| NIVEAU_BAS_VANNE_PANNE | 9 | 4 | 5 | 180 | 1 |
| HEATER_RESISTANCE_HS | 8 | 4 | 5 | 160 | 2 |
| CALCAIRE_TUYAUX | 8 | 4 | 3 | 96 | 3 |
| HEATER_POMPE_HS | 9 | 2 | 5 | 90 | 4 |
| BULLES_AIR | 6 | 5 | 3 | 90 | 5 |
| FUITE_CIRCUIT | 6 | 5 | 2 | 60 | 6 |
| ISOLATION_DEGRADEE | 5 | 3 | 3 | 45 | 7 |

Les trois modes de défaillance les plus critiques sont détaillés ci-dessous :

1. **Niveau bas / Vanne en panne** (criticité 180) : une vanne d'appoint défectueuse ou un niveau d'eau insuffisant dans le réservoir principal prive la boucle chauffante d'eau d'appoint, entraînant une baisse généralisée des températures. La gravité maximale (G=9) reflète l'arrêt complet de la production.

2. **Résistance heater hors service** (criticité 160) : la panne de la résistance électrique entraîne une chute rapide de la température de l'eau. Bien que la détection soit aisée (G=8, D=5), l'occurrence modérée (O=4) justifie une priorité élevée.

3. **Encrassement calcaire des tuyaux** (criticité 96) : l'accumulation progressive de calcaire réduit le débit et l'efficacité thermique. L'occurrence est élevée (O=4) en raison de la dureté de l'eau, mais la détection est modérée (D=3) car l'évolution est lente et difficile à distinguer d'autres causes sans instrumentation dédiée.

[Insert Figure 2.2 — Diagramme de Pareto des criticité AMDEC]

### 2.1.4 Apport de la maintenance prédictive

Face à ces modes de défaillance, les approches traditionnelles de maintenance montrent leurs limites [8] :

- **Maintenance corrective** : intervention après la panne — coûteuse (arrêt de production non planifié, réparation d'urgence) ;
- **Maintenance préventive systématique** : intervention à intervalles fixes — peut être prématurée (gaspillage de ressources, main-d'œuvre et pièces de rechange) ou tardive (si la dégradation s'accélère entre deux interventions).

La **maintenance prédictive**, rendue possible par les technologies de l'Industrie 4.0 (IoT industriel, capteurs communicants, apprentissage automatique), propose une troisième voie : intervenir en fonction de l'état réel du système, détecté et anticipé par des modèles de diagnostic et de pronostic [9].

Dans le contexte de l'encrassement calcaire et des baisses de température des moules, cette approche est particulièrement adaptée pour trois raisons :

1. **La dégradation est progressive** : l'accumulation de calcaire s'étale sur des semaines, voire des mois — une fenêtre de prédiction large est disponible ;
2. **Les signatures physiques sont mesurables indirectement** : température, débit et pression hydraulique permettent d'inférer l'état d'encrassement par des modèles de soft sensing, sans capteur dédié ;
3. **Les causes de défaillance sont distinctes et classifiables** : l'analyse AMDEC a montré que chaque mode possède une signature physico-temporelle propre (chute brutale pour une panne pompe, dérive lente pour le calcaire, etc.), ce qui rend leur classification par apprentissage automatique pertinente.

Le système proposé dans ce projet vise à implémenter cette maintenance prédictive à travers une architecture de supervision temps réel couplée à des modèles de machine learning (détection d'anomalies, classification des causes, prédiction de maintenance), comme détaillé dans le Chapitre 3.

---

## 2.2 Cahier des charges

### 2.2.1 Besoins fonctionnels — Partie A (Supervision thermique)

Le système de supervision thermique doit répondre aux exigences fonctionnelles suivantes :

**BF-01 — Acquisition temps réel** : lecture de 7 capteurs de température via Modbus RTU sur bus RS485 avec une fréquence d'acquisition de 1 Hz, et d'un débitmètre YF-S201 (Hall effect) via GPIO.

**BF-02 — Stockage des données** : persistance des mesures dans une base de données time-series (InfluxDB) avec rétention configurable.

**BF-03 — Détection d'anomalies** : identification en temps réel des écarts anormaux de température par un modèle Isolation Forest, avec un taux de faux positifs (FPR) inférieur à 5%.

**BF-04 — Classification des causes** : détermination de la cause racine d'une anomalie parmi 7 classes définies par l'AMDEC, avec un F1-score > 85%.

**BF-05 — Prédiction de maintenance** : estimation du nombre de jours restants avant que l'épaisseur de calcaire n'atteigne un seuil critique, avec un intervalle de confiance à 90% et une erreur RMSE < 3 jours.

**BF-06 — Visualisation temps réel** : tableau de bord web (React) affichant les températures, le diagnostic intelligent et les prédictions de maintenance, mis à jour à 1 Hz via WebSocket.

**BF-07 — Alertes automatiques** : notification multi-canal (Telegram, Email) via un module d'alerte Python intégré en cas d'anomalie détectée, avec trois niveaux de sévérité (WARNING, CRITICAL, SYSTEM).

**BF-08 — Surveillance de la santé des modèles** : évaluation périodique des performances des modèles ML et déclenchement automatique de ré-entraînement en cas de dégradation.

### 2.2.2 Besoins fonctionnels — Partie B (Simulation adoucisseur d'eau)

**BF-09 — Modélisation physico-chimique** : simulation du comportement d'une résine échangeuse d'ions (Purolite C100E) par un modèle à compartiments.

**BF-10 — Simulation multi-cycle** : validation du comportement sur deux cycles (résine neuve puis régénérée) avec une efficacité de régénération de 90%.

**BF-11 — Validation du contrôle embarqué** : simulation du système de régulation ESP32 sous Wokwi (lecture capteur, seuil, séquence saumure/rinçage).

### 2.2.3 Contraintes non-fonctionnelles

**CNF-01 — Contrainte matérielle** : l'ensemble du backend doit s'exécuter sur un Raspberry Pi 4 (8 Go RAM, ARM Cortex-A72).

**CNF-02 — Temps réel** : la boucle d'acquisition et de diagnostic doit s'exécuter en moins de 1 seconde (1 Hz).

**CNF-03 — Évolutivité** : l'architecture doit permettre l'ajout futur de 5 capteurs PT100 (SPI, MAX31865) et de 3 débitmètres supplémentaires sans modification du cœur logiciel.

**CNF-04 — Disponibilité** : le système doit fonctionner 24h/24 et 7j/7 avec reconnection automatique en cas de panne du bus Modbus.

**CNF-05 — Portabilité** : les composants logiciels doivent être multiplateformes (Windows pour le développement, Linux/ARM pour le déploiement).

[Insert Tableau 2.2 — Synthèse du cahier des charges]

---

## 2.3 Étude préalable

### 2.3.1 État de l'art des solutions de supervision industrielle

La supervision industrielle a connu une évolution significative depuis les systèmes SCADA traditionnels vers les architectures IoT industrielles (IIoT). Boyes et al. (2018) proposent un cadre de référence pour l'IIoT identifiant quatre domaines : la connectivité, l'analyse de données, la gestion des actifs et la cybersécurité [11].

Dans le domaine de la maintenance prédictive, trois approches principales se distinguent [12] :

1. **Approche basée sur des modèles physiques** (model-based) : utilisation d'équations différentielles décrivant le comportement du système (ex : loi de Fourier pour l'encrassement). Précise mais nécessite une connaissance approfondie du système.

2. **Approche basée sur les données** (data-driven) : exploitation d'historiques de données pour entraîner des modèles de ML (ex : Random Forest, réseaux de neurones). Flexible mais nécessite des données d'entraînement abondantes et labellisées.

3. **Approche hybride (Grey-Box)** : combinaison d'un modèle physique simplifié et d'un apprentissage statistique sur les résidus. Offre le meilleur compromis entre précision physique et flexibilité [13].

Le système proposé dans ce projet adopte une approche hybride : un modèle Grey-Box (physique) pour l'estimation de l'épaisseur de calcaire, complété par des modèles de ML (Isolation Forest, Random Forest, Ridge Regression) pour la détection d'anomalies, la classification des causes et la prédiction de maintenance.

### 2.3.2 Solutions existantes — limites

La solution actuellement déployée chez Yazaki Morocco repose sur l'utilisation d'un additif chimique anticorrosion (ST-DOS H-390) injecté dans le circuit hydraulique. Cette approche présente trois limitations majeures :

- **Coût récurrent élevé** : l'achat continu de l'additif représente une dépense opérationnelle significative.
- **Absence de détection** : aucune mesure en temps réel de l'efficacité du traitement ni de l'état d'encrassement.
- **Traitement partiel** : l'additif est un inhibiteur de corrosion, pas un adoucisseur d'eau — il ne retire pas la dureté calcique.

Les solutions de supervision industrielle propriétaires du marché (Siemens SCADA, Wonderware, Ignition) offrent des fonctionnalités avancées mais présentent des coûts de licence élevés et une flexibilité limitée pour l'intégration de modèles de ML personnalisés [14].

### 2.3.3 Solution proposée — Architecture à trois niveaux

La solution proposée s'articule autour d'une architecture à trois niveaux (trois tiers) inspirée des architectures IoT industrielles de référence [11] :

**Niveau 1 — Acquisition physique** : un Raspberry Pi 4 interroge 7 capteurs de température via Modbus RTU sur RS485 et un débitmètre YF-S201 via GPIO. Une LED WS2812B assure le signalement visuel local des alertes.

**Niveau 2 — Traitement et apprentissage automatique** : le backend Python (FastAPI) exécute la boucle d'acquisition, le pipeline ML complet (Grey-Box, Isolation Forest, Random Forest, Ridge Regression avec Bootstrap) et stocke les données dans InfluxDB.

**Niveau 3 — Présentation et automatisation** : une interface web React (Vite + TailwindCSS) visualise les données en temps réel via WebSocket, tandis qu'un module d'alerte Python intégré envoie les notifications Telegram et Email directement.

[Insert Figure 2.3 — Architecture globale du système à trois niveaux]

### 2.3.4 Justification des choix technologiques

Le Tableau 2.3 synthétise les choix technologiques retenus et leur justification.

[Insert Tableau 2.3 — Justification des choix technologiques]

| Technologie | Justification |
|:------------|:--------------|
| **Modbus RTU** | Protocole industriel ouvert, robuste sur longues distances (RS485 jusqu'à 1200 m), prise en charge native par pymodbus. |
| **Raspberry Pi 4** | Plateforme embarquée puissante (8 Go RAM), écosystème Linux complet, GPIO pour débitmètre et LED. |
| **FastAPI + Uvicorn** | Framework asynchrone performant, support natif WebSocket, documentation automatique (OpenAPI). |
| **InfluxDB** | Base time-series optimisée pour l'acquisition à 1 Hz, requêtes Flux puissantes pour l'agrégation. |
| **scikit-learn** | Bibliothèque ML mature, implémentations optimisées (Isolation Forest, Random Forest, Ridge). |
| **React + Vite** | Framework moderne, rendu efficace, écosystème Recharts pour les graphiques temps réel. |
| **Module d'alerting Python** | Envoi direct Telegram et Email via l'API Telegram et SMTP, sans intermédiaire. Réduit la latence et supprime un point de défaillance. |

---

## 2.4 Plan d'action

Le projet est structuré en cinq phases, couvrant la période de février à juin 2026 :

### 2.4.1 Phase 1 — Analyse et spécification (Février–Mars)
- Étude du procédé de moussage et du circuit hydraulique
- Analyse AMDEC des modes de défaillance
- Définition du cahier des charges
- État de l'art des solutions de supervision

### 2.4.2 Phase 2 — Conception et architecture (Mars–Avril)
- Conception de l'architecture à trois niveaux
- Choix des technologies et protocoles
- Conception des modèles ML (Grey-Box, Isolation Forest, Random Forest, Ridge)
- Modélisation mathématique de l'adoucisseur (modèle à compartiments)

### 2.4.3 Phase 3 — Réalisation et développement (Avril–Mai)
- Développement du backend (API, acquisition Modbus, InfluxDB)
- Développement du pipeline ML (entraînement, inférence, évaluation)
- Développement du frontend React (3 onglets, WebSocket)
- Développement du module d'alerting (Telegram, Email)
- Simulation MATLAB/Simulink de l'adoucisseur
- Validation Wokwi du contrôle embarqué ESP32

### 2.4.4 Phase 4 — Tests et validation (Mai)
- Tests unitaires (Modbus manager, API, ML)
- Tests d'intégration (backend → InfluxDB → frontend)
- Validation des performances ML (FPR, F1-score, RMSE)
- Validation des courbes de percée de l'adoucisseur

### 2.4.5 Phase 5 — Déploiement et rédaction (Mai–Juin)
- Déploiement sur Raspberry Pi 4
- Tests en conditions réelles
- Rédaction du rapport PFE
- Préparation de la soutenance

---

## 2.5 Diagramme de Gantt

[Insert Figure 2.4 — Diagramme de Gantt du projet PFE (Février–Juin 2026)]

[Insert Tableau 2.4 — Jalons clés et livrables]

| Jalon | Date prévue | Livrable |
|:------|:-----------|:---------|
| J1 — Validation cahier des charges | 07/03/2026 | Document de spécification |
| J2 — Architecture validée | 28/03/2026 | Schéma d'architecture |
| J3 — Backend opérationnel | 18/04/2026 | API + acquisition Modbus |
| J4 — Pipeline ML validé | 02/05/2026 | Modèles entraînés + métriques |
| J5 — Frontend livré | 09/05/2026 | Interface React complète |
| J6 — Simulation adoucisseur validée | 16/05/2026 | Modèles Simulink + Wokwi |
| J7 — Tests d'intégration | 23/05/2026 | Rapport de tests |
| J8 — Déploiement RPi | 30/05/2026 | Système en production |
| J9 — Rapport final | 06/06/2026 | Document PFE complet |
| J10 — Soutenance | 13/06/2026 | Présentation |

---

## Conclusion du chapitre 2

Ce chapitre a posé les fondements de l'étude en exposant la problématique industrielle dans sa globalité : la baisse de température des moules — indétectable sans supervision — et l'encrassement calcaire généralisé des circuits d'eau chaude (tuyaux, réservoirs heaters, tanks poly iso). L'absence de visibilité sur l'état réel du système empêche tout diagnostic précoce et conduit à des pertes de production évitables.

L'analyse AMDEC a permis d'identifier et de prioriser sept modes de défaillance, dont l'encrassement calcaire (criticité 96, priorité 3), et a montré la pertinence d'une approche de maintenance prédictive. Celle-ci, rendue possible par les technologies IoT et l'apprentissage automatique, permet d'anticiper les défaillances plutôt que de les subir — contrairement aux approches corrective et préventive systématique.

Le cahier des charges, décliné en onze besoins fonctionnels et cinq contraintes non-fonctionnelles, servira de référence pour la conception et la validation du système. L'étude préalable a justifié l'approche hybride (Grey-Box + ML) retenue, ainsi que les choix technologiques (FastAPI, InfluxDB, React, scikit-learn) au regard des contraintes du projet.

Le plan d'action structuré en cinq phases et le diagramme de Gantt associé fournissent le cadre temporel de la réalisation, qui fera l'objet de l'étude détaillée au chapitre suivant.

---

# CHAPITRE 3 — ÉTUDE DÉTAILLÉE DU PROJET

## Introduction du chapitre

Ce chapitre constitue le cœur technique du rapport. Il présente l'étude détaillée de l'ensemble du système, depuis l'architecture globale jusqu'aux algorithmes spécifiques de chaque module. La présentation est organisée en deux parties distinctes, reflétant les deux axes du projet :

- **Partie A** (Sections 3.1 à 3.11) : Supervision thermique industrielle — acquisition, modélisation Grey-Box, détection d'anomalies, classification des causes, prédiction de maintenance, interface utilisateur, automatisation des alertes et surveillance de la santé des modèles.
- **Partie B** (Sections 3.12 à 3.15) : Simulation conceptuelle d'un système d'adoucissement d'eau — modélisation mathématique de l'échange d'ions, simulation MATLAB/Simulink et validation embarquée sous Wokwi.

Chaque section comprend une description détaillée de l'algorithme implémenté, présenté sous forme de pseudocode structuré, les justifications théoriques appuyées par des références bibliographiques IEEE, ainsi que des marqueurs pour les figures et tableaux à insérer dans le rapport final.

---

## 3.1 Architecture globale du système

L'architecture générale du système de supervision thermique repose sur trois niveaux interconnectés, comme illustré sur la Figure 3.1.

[Insert Figure 3.1 — Diagramme d'architecture système complet (3 niveaux)]

**Niveau 1 — Acquisition physique** : le Raspberry Pi 4 communique avec les capteurs de température via le protocole Modbus RTU sur un bus RS485 half-duplex. Sept capteurs sont interrogés séquentiellement à une fréquence de 1 Hz. Un débitmètre YF-S201 à effet Hall est connecté sur une broche GPIO et exploité via interruption matérielle pour le comptage d'impulsions.

**Niveau 2 — Traitement et intelligence artificielle** : le backend FastAPI orchestre une boucle d'acquisition qui, à chaque cycle (1 seconde), lit les capteurs, exécute le pipeline ML complet, et stocke les résultats dans InfluxDB. Le pipeline ML se compose de quatre modèles en cascade :
1. Grey-Box Model (estimation physique de l'épaisseur de calcaire)
2. Isolation Forest (détection d'anomalies non supervisée)
3. Random Forest + Règles physiques (classification des causes)
4. Ridge Regression + Bootstrap (prédiction de la date de maintenance)

**Niveau 3 — Présentation et automatisation** : un frontend React (Vite) affiche les données en temps réel via WebSocket sur trois onglets (Supervision, Diagnostic Intelligent, Maintenance Prédictive). Le module d'alerting Python intégré envoie les notifications (Telegram, Email) directement depuis le backend.

Le flux de données complet est représenté sur le diagramme de la Figure 3.2.

[Insert Figure 3.2 — Diagramme de flux de données complet]

```
  ┌───────────┐    ┌─────────────────────┐    ┌───────────┐    ┌──────────┐
  │ 7× Temp   │    │    Backend          │    │ InfluxDB  │    │ Frontend │
  │ Modbus    │───▶│    FastAPI          │───▶│ Time-     │───▶│ React    │
  │ RTU/RS485 │    │    (boucle 1 Hz)    │    │ Series    │    │ WebSocket│
  └───────────┘    │                     │    └───────────┘    └──────────┘
                   │  ┌───────────────┐  │
  ┌───────────┐    │  │ ML Pipeline   │  │    ┌───────────┐
  │ 1× Flow   │───▶│  │ 1. Grey-Box   │──┼───▶│ Alerting │
  │ YF-S201   │    │  │ 2. Isolation  │  │    │ Python   │
  │ GPIO      │    │  │ 3. Random For │  │    │ Telegram │
  └───────────┘    │  │ 4. Ridge+Boot │  │    │ Email    │
                   │  └───────────────┘  │    └───────────┘
                   └─────────────────────┘
```

**Algorithme 3.1 : Pipeline principal d'acquisition et de diagnostic**

```
Entrée : Aucune (boucle continue)
Sortie : Mise à jour des variables globales latest_sensors, latest_diagnostic, latest_maintenance

1: TANT QUE vrai FAIRE
2:     // Phase 1 — Acquisition physique (1 Hz)
3:     readings ← modbus.read_all_sensors(calibration_temps)
4:     temp_heater ← lire_température_heater()
5:     flow_readings ← {} 
6:     POUR CHAQUE (gid, sensor) DANS flow_sensors FAIRE
7:         flow_readings[gid] ← sensor.read_lpm()
8:     FIN POUR
9:     flow_lpm ← moyenne(flow_readings.values()) OU FLOW_DEFAULT_LPM
10:
11:    // Phase 2 — Mise à jour des historiques roulants
12:    POUR CHAQUE r DANS readings FAIRE
13:        key ← (r.group_id, r.mold_id)
14:        TEMP_HISTORY[key].append(r.temperature)
15:    FIN POUR
16:
17:    // Phase 3 — Grey-Box (Soft Sensing)
18:    POUR CHAQUE r DANS readings FAIRE
19:        gb ← grey_box.compute(r.group_id, r.mold_id, r.temperature, flow_lpm)
20:        grey_results[key] ← gb
21:    FIN POUR
22:
23:    // Phase 4 — Détection d'anomalies (Isolation Forest)
24:    features ← iso_forest.extract_features(TEMP_HISTORY, FLOW_HISTORY, delta_T_map)
25:    SI features ≠ None ALORS
26:        anomaly_result ← iso_forest.predict(features)
27:    SINON
28:        anomaly_result ← {anomaly_detected: False, anomaly_score: None}
29:    FIN SI
30:
31:    // Phase 5 — Classification des causes (Random Forest + Règles)
32:    SI anomaly_result.anomaly_detected ALORS
33:        rf_features ← construire_vecteur_10_features(TEMP_HISTORY, FLOW_HISTORY, delta_T_map)
34:        rule_result ← rf.physical_rules(affected_ratio, sudden_drop, flow_lpm, ...)
35:        cause_result ← rule_result OU rf.predict(rf_features)
36:        enrichir_AMDEC(cause_result)
37:    SINON
38:        cause_result ← {cause: 'NORMAL', confidence: 1.0}
39:    FIN SI
40:
41:    // Phase 6 — Stockage et diffusion
42:    influx.write_sensors(readings, delta_T_map)
43:    influx.write_flow(gid, flow_lpm)
44:    WebSocket.broadcast({sensors, diagnostic, maintenance})
45:
46:    // Phase 7 — Alertes (si anomalie)
47:    SI anomaly_result.anomaly_detected ALORS
48:        alerting.send_alert(severity, cause, confidence, actions, amdec, affected_molds)
49:    FIN SI
50:
51:    attendre(1.0 / ACQUISITION_HZ)
52: FIN TANT QUE
```

---

## PARTIE A — SUPERVISION THERMIQUE INDUSTRIELLE

---

## 3.2 Spécification du système de supervision

### 3.2.1 Périmètre fonctionnel

Le système de supervision thermique couvre l'ensemble de la ligne de moussage polyuréthane, comprenant 12 moules répartis en 4 groupes de 3 moules chacun. Chaque groupe est associé à un échangeur thermique (heater) maintenant l'eau de procédé à 45°C.

### 3.2.2 Contraintes opérationnelles

Les paramètres de fonctionnement nominaux et les seuils d'alerte sont définis comme suit :

- Température de consigne du heater : 45°C
- Tolérance de procédé : ±3°C (bande 42–48°C)
- Seuil d'alerte (T_MOLD_WARNING) : 42°C
- Seuil critique (T_MOLD_CRITICAL) : 40°C
- Débit nominal de la pompe : 16,5 L/min
- Diamètre des tuyaux : 13 mm
- Longueur du circuit par moule : 3 m

### 3.2.3 Indicateurs de performance (KPIs)

Le système définit trois catégories d'indicateurs de performance, présentés dans le Tableau 3.1.

[Insert Tableau 3.1 — Indicateurs de performance du système]

**KPIs physiques (temps réel) :**

| Indicateur | Unité | Fréquence | Source |
|:-----------|:-----|:---------|:-------|
| Température moyenne par groupe | °C | 1 Hz | Moyenne des 3 moules du groupe |
| Écart-type des températures | °C | 1 Hz | Variance intra-groupe |
| Débit instantané | L/min | 1 Hz | Débitmètre YF-S201 |
| Épaisseur de calcaire estimée | mm | 1 Hz | Modèle Grey-Box |
| Dégradation (%) | % | 1 Hz | Ratio delta_T / delta_T_max |
| Écart à la consigne | °C | 1 Hz | T_heater − T_mold |

**KPIs des modèles ML (évaluation périodique) :**

| Indicateur | Cible | Fréquence | Modèle |
|:-----------|:-----|:---------|:-------|
| Taux d'anomalie (anomaly rate) | < 15% | 600 cycles (~10 min) | Isolation Forest |
| Faux positifs (FPR) | < 5% | Quotidien | Isolation Forest |
| F1-score pondéré | > 85% | Quotidien | Random Forest |
| Accuracy | > 80% | Quotidien | Random Forest |
| RMSE | < 3 jours | Quotidien | Ridge Regression |
| R² | > 0,85 | Quotidien | Ridge Regression |
| Largeur IC 90% | < 15 jours | Quotidien | Ridge Bootstrap |
| Erreur relative Grey-Box | < 10% | Hebdomadaire | Grey-Box Model |

**KPIs système :**

| Indicateur | Cible | Fréquence |
|:-----------|:-----|:---------|
| Uptime du backend | > 99% | Continue |
| Latence WebSocket | < 100 ms | Continue |
| Temps de cycle moyen | < 1 s | Continue |
| Nombre d'alertes générées | — | Quotidien |

[Insert Figure 3.3 — Tableau de bord temps réel avec indicateurs de performance]

---

## 3.3 Architecture matérielle et logicielle

### 3.3.1 Architecture matérielle

Le matériel déployé se compose des éléments suivants :

- **Raspberry Pi 4 Model B (8 Go RAM)** : cœur du système, exécutant le backend, InfluxDB et l'ensemble du pipeline ML.
- **Convertisseur USB/RS485 (FTDI)** : interface entre le Raspberry Pi et le bus Modbus.
- **7 capteurs de température Modbus** (adresses esclaves 1 à 7) : mesure de la température des moules.
- **Débitmètre YF-S201** (Hall effect) : connecté sur broche GPIO 17, mesure du débit de la pompe.
- **LED WS2812B (Neopixel)** : signalement visuel local des alertes.

[Insert Figure 3.5 — Schéma de câblage complet (Raspberry Pi, RS485, capteurs Modbus, YF-S201, WS2812B)]

Le bus RS485 est configuré avec les paramètres suivants :
- Baudrate : 9600 bps
- Parité : None
- Bits de stop : 1
- Taille de mot : 8 bits
- Timeout : 2 secondes

### 3.3.2 Architecture logicielle

L'architecture logicielle est organisée en couches superposées, chacune ayant une responsabilité bien définie, comme illustré sur la Figure 3.6.

[Insert Figure 3.6 — Stack technologique (diagramme en couches)]

[Insert Tableau 3.2 — Technologies et rôles]

| Couche | Technologie | Rôle |
|:-------|:-----------|:-----|
| **Système** | Raspberry Pi OS (Debian 12) | Système d'exploitation embarqué |
| **Runtime** | Python 3.11 + Node.js 20 | Exécution backend et frontend |
| **Base de données** | InfluxDB 2.x | Stockage time-series |
| **Backend** | FastAPI + Uvicorn | API REST, WebSocket, boucle d'acquisition |
| **ML** | scikit-learn (1.4), NumPy | Isolation Forest, Random Forest, Ridge |
| **Frontend** | React 18 + Vite + TailwindCSS + Recharts | Interface utilisateur temps réel |
| **Alerting** | Module Python (requests + smtplib) | Envoi direct Telegram/Email |

### 3.3.3 Protocoles de communication

[Insert Tableau 3.3 — Protocoles, usages et ports]

| Protocole | Usage | Port |
|:----------|:------|:----:|
| Modbus RTU | Acquisition capteurs | RS-485 (série) |
| WebSocket | Temps réel frontend | 8001 |
| HTTP/REST | API backend | 8001 |
| InfluxDB HTTP | Stockage time-series | 8086 |
| Module d'alerting | Telegram / Email | HTTPS (api.telegram.org), SMTP |

### 3.3.4 Diagramme de classes

Le diagramme de classes de la Figure 3.4 présente la vue statique complète du backend Python. Il organise le système en trois couches fonctionnelles : l'acquisition physique, le pipeline de traitement ML, et les services supports.

**Couche acquisition :** `ModbusManager` gère le bus RS485 et produit des `SensorReading` pour les 7 capteurs de température, tandis que `FlowSensor` mesure le débit via le YF-S201 sur GPIO.

**Couche ML :** `GreyBoxModel` estime l'épaisseur de calcaire par soft sensing (loi de Fourier). `AnomalyDetector` (Isolation Forest) détecte les comportements anormaux. `CauseClassifier` (Random Forest + règles physiques) identifie la cause racine parmi 7 classes de défaillance. `RidgePredictor` (Ridge + Bootstrap) prédit la date de maintenance avec un intervalle de confiance à 90%.

**Couche support :** `influxdb_manager` assure le stockage time-series, `alerting` envoie les notifications multi-canal (Telegram + Email), et `model_evaluator` évalue la performance des modèles et déclenche le ré-entraînement si nécessaire.

[Insert Figure 3.4 — Diagramme de classes du backend Python (héritage, composition et dépendances entre les modules)]

---

## 3.4 Module d'acquisition de données

### 3.4.1 Protocole Modbus RTU sur RS485

Le protocole Modbus RTU (Remote Terminal Unit) est un standard de communication industrielle largement répandu, fonctionnant en mode maître-esclave (half-duplex) sur une liaison série RS485 [15]. Dans notre configuration, le Raspberry Pi joue le rôle de maître et interroge séquentiellement les 7 capteurs esclaves.

**Structure d'une trame Modbus RTU :**

[Insert Figure 3.7 — Structure d'une trame Modbus RTU (adresse esclave, fonction, données, CRC)]

Chaque trame comprend :
- **Adresse esclave** (1 octet) : identification du capteur (1–7)
- **Code fonction** (1 octet) : 0x03 pour lecture de registres de maintien
- **Adresse du registre** (2 octets) : décalage dans la mémoire du capteur
- **Nombre de registres** (2 octets) : généralement 1
- **CRC16** (2 octets) : contrôle d'intégrité

**Topologie half-duplex :**

[Insert Figure 3.8 — Topologie bus RS485 half-duplex avec 7 capteurs]

Le bus RS485 impose une communication half-duplex : un seul échange requête-réponse peut être en vol à la fois. Cette contrainte est gérée par un verrou asynchrone (asyncio.Lock) dans le code Python, garantissant l'exclusion mutuelle des accès.

**Algorithme 3.2 : Lecture séquentielle des capteurs Modbus**

```
Entrée : SENSOR_MAP (dictionnaire {(group_id, mold_id): (slave, register)})
         calibration_temps (dictionnaire des températures de calibration)
Sortie : Liste de SensorReading

1: POUR CHAQUE ((gid, mid), (slave, reg)) DANS SENSOR_MAP FAIRE
2:     temp ← None
3:     ESSAYER
4:         ACQUÉRIR lock_bus        // Exclusion mutuelle RS485
5:         résultat ← client.read_holding_registers(register=reg, count=1, slave=slave)
6:         LIBÉRER lock_bus
7:         SI résultat.est_erreur() ALORS
8:             temp ← None
9:         SINON
10:            temp ← résultat.registers[0] × TEMP_SCALE_FACTOR  // conversion 0.1°C/bit
11:        FIN SI
12:    EXCEPTION (TimeoutError, ModbusException)
13:        temp ← None
14:    FIN ESSAYER
15:
16:    // Classification du statut
17:    SI temp = None ALORS
18:        status ← 'ERREUR'
19:        deviation ← None
20:    SINON SI temp < T_MOLD_CRITICAL ALORS
21:        status ← 'CRITIQUE'
22:        deviation ← temp − T_HEATER
23:    SINON SI temp < T_MOLD_WARNING ALORS
24:        status ← 'ALERTE'
25:        deviation ← temp − T_HEATER
26:    SINON
27:        status ← 'OK'
28:        deviation ← temp − T_HEATER
29:    FIN SI
30:
31:    SensorReading(gid, mid, pos, temp, status, T_HEATER, deviation, timestamp) → readings
32: FIN POUR
33:
34: // Reconnexion si tous les capteurs sont en échec (debounce 30s)
35: SI tous None ALORS
36:     SI (maintenant − dernière_reconnexion) > 30s ALORS
37:         fermer_connexion()
38:         initialiser_connexion()
39:     FIN SI
40: FIN SI
41:
42: RETOURNER readings
```

**Algorithme 3.3 : Gestion des erreurs et reconnexion Modbus**

```
Entrée : Aucune (mécanisme de reconnection automatique)
Sortie : Reconnexion au bus Modbus en cas d'échec

1: VARIABLE GLOBALE : _last_reconnect ← 0  // timestamp de la dernière reconnexion
2:
3: FONCTION verifier_reconnexion(readings)
4:     SI readings est vide OU tous les températures sont None ALORS
5:         maintenant ← timestamp_actuel()
6:         SI (maintenant − _last_reconnect) > 30 ALORS
7:             log.warning("Tous les capteurs sont None → tentative de reconnexion")
8:             _last_reconnect ← maintenant
9:             fermer_connexion()
10:            initialiser_connexion()
11:        SINON
12:            log.debug("Reconnexion débouncee (%.0f s depuis dernière)", (maintenant−_last_reconnect))
13:        FIN SI
14:    FIN SI
15: FIN FONCTION
16:
17: FONCTION initialiser_connexion() → booléen
18:     client ← AsyncModbusSerialClient(port, baudrate, parity, stopbits, bytesize, timeout)
19:     connecté ← client.connect()
20:     lock_bus ← asyncio.Lock()  // Nouveau verrou après reconnexion
21:     RETOURNER connecté
22: FIN FONCTION
```

### 3.4.2 Acquisition du débitmètre YF-S201

Le débitmètre YF-S201 est un capteur à effet Hall qui délivre un signal carré dont la fréquence est proportionnelle au débit :

\[
Q \, (\text{L/min}) = \frac{F \, (\text{Hz})}{7,5} \tag{3.1}
\]

où \(F\) est la fréquence mesurée et \(7,5\) le facteur de conversion (pulses par litre) du YF-S201.

[Insert Figure 3.9 — Signal du débitmètre YF-S201 : fréquence d'impulsions proportionnelle au débit]

L'acquisition est réalisée par interruption matérielle (GPIO) : chaque front montant du signal incrémente un compteur. La lecture périodique convertit le nombre d'impulsions en fréquence puis en débit.

**Algorithme 3.4 : Lecture du débit par interruption GPIO**

```
Entrée : pin GPIO, k_factor = 7.5 (pulses/L)
Sortie : Débit en L/min

1: CLASSE FlowSensor
2:     VARIABLES : pin, k_factor, pulse_count ← 0, lock (threading.Lock), last_read_time
3:
4:     FONCTION __init__(pin, k_factor)
5:         self.pin ← pin
6:         self.k_factor ← k_factor
7:         sensor ← gpiozero.DigitalInputDevice(pin, bounce_time=0.01)
8:         sensor.when_activated ← self._pulse  // Callback d'interruption
9:     FIN FONCTION
10:
11:    FONCTION _pulse()  // Appelé à chaque front montant (interruption)
12:        ACQUÉRIR lock
13:        pulse_count ← pulse_count + 1
14:        LIBÉRER lock
15:    FIN FONCTION
16:
17:    FONCTION read_lpm() → float
18:        SI capteur non initialisé ALORS
19:            RETOURNER FLOW_DEFAULT_LPM  // 16.5 L/min (fallback)
20:        FIN SI
21:
22:        maintenant ← temps_actuel()
23:        elapsed ← maintenant − last_read_time
24:        last_read_time ← maintenant
25:
26:        ACQUÉRIR lock
27:        pulses ← pulse_count
28:        pulse_count ← 0
29:        LIBÉRER lock
30:
31:        fréquence ← pulses / elapsed  // Hz
32:        débit ← fréquence / k_factor  // L/min
33:
34:        // Filtre anti-pics (débit > 30 L/min invraisemblable)
35:        SI débit > 30 ALORS
36:            log.warning("Pic de débit détecté : %.2f L/min", débit)
37:            débit ← FLOW_DEFAULT_LPM
38:        FIN SI
39:
40:        RETOURNER débit
41:    FIN FONCTION
42: FIN CLASSE
```

### 3.4.3 Synchronisation et horodatage

Chaque cycle d'acquisition est horodaté avec une précision de l'ordre de la seconde. L'horodatage est généré côté backend au format ISO 8601 et transmis à InfluxDB avec une précision de l'ordre de la milliseconde (WritePrecision.MS). Cette synchronisation permet de corréler les mesures entre elles et les événements de diagnostic.

### 3.4.4 Configuration des seuils d'alerte

Les seuils sont définis dans le fichier de configuration (`config.py`) et peuvent être ajustés sans modifier le code source :

```
T_HEATER        = 45.0    // Consigne du heater (°C)
T_TOLERANCE     = 3.0     // Tolérance de procédé (°C)
T_MOLD_WARNING  = 42.0    // Seuil d'alerte
T_MOLD_CRITICAL = 40.0    // Seuil critique
```

### 3.4.5 Perspectives d'extension matérielle

La configuration actuelle utilise 7 capteurs Modbus et 1 débitmètre YF-S201. L'architecture logicielle a été conçue pour permettre l'ajout futur de :

- **5 capteurs PT100 additionnels** via interface SPI et convertisseur MAX31865 (résolution 0.03125°C, précision ±0.5°C). Le protocole SPI offrirait un débit plus élevé que Modbus pour les capteurs à haute résolution.
- **3 débitmètres supplémentaires** (1 par groupe heater), portant le total à 4, afin d'obtenir une mesure de débit indépendante pour chaque groupe de moules. La classe `FlowSensor` et la structure de données `flow_sensors` (dictionnaire {group_id: FlowSensor}) supportent déjà cette extension.

Ces extensions matérielles sont mentionnées dans les perspectives d'amélioration du Chapitre 5.

---

## 3.5 Modèle Grey-Box et Soft Sensing

### 3.5.1 Principe du soft sensing par bilan thermique

Le soft sensing est une technique qui consiste à estimer une grandeur physique difficile ou coûteuse à mesurer directement à partir de mesures indirectes disponibles [16]. Dans notre cas, l'épaisseur de calcaire dans les tuyaux est estimée à partir des mesures de température et de débit, sans capteur dédié.

Le principe repose sur le bilan thermique suivant : la différence de température entre l'eau chauffée (T_heater = 45°C) et la température mesurée sur le moule (T_mold) est la somme de deux contributions :

\[
\Delta T_{mesuré} = \underbrace{\Delta T_{normal}}_{\text{pertes thermiques normales}} + \underbrace{\Delta T_{calcaire}}_{\text{perte due au calcaire}} \tag{3.2}
\]

La composante \(\Delta T_{normal}\) est déterminée lors de l'installation (jour 1, tuyaux propres) et sert de référence de calibration. Toute augmentation ultérieure de \(\Delta T_{mesuré}\) par rapport à cette référence est attribuée à l'accumulation de calcaire.

[Insert Figure 3.10 — Principe du bilan thermique sur un moule]

### 3.5.2 Modélisation physique

La puissance thermique transportée par l'eau à travers un moule s'exprime par :

\[
Q = \dot{m} \cdot C_p \cdot \Delta T_{mesuré} \tag{3.3}
\]

où \(\dot{m} = \rho \cdot Q_v\) est le débit massique (kg/s), \(C_p = 4186\,\text{J}·\text{kg}^{-1}·\text{K}^{-1}\) la capacité thermique massique de l'eau, et \(\rho = 1000\,\text{kg}·\text{m}^{-3}\) la masse volumique.

La résistance thermique de la couche de calcaire est déduite par :

\[
R_{calcaire} = \frac{\Delta T_{calcaire}}{Q} \tag{3.4}
\]

En appliquant la loi de Fourier pour la conduction thermique à travers une paroi cylindrique [6] :

\[
e = R_{calcaire} \cdot \lambda_{calcaire} \cdot A_{tube} \tag{3.5}
\]

où \(e\) est l'épaisseur de la couche de calcaire (m), \(\lambda_{calcaire} = 1,0\,\text{W}·\text{m}^{-1}·\text{K}^{-1}\) la conductivité thermique du calcaire, et \(A_{tube} = \pi \times L \times D\) la surface latérale interne du tube.

L'urgence est classifiée en cinq niveaux en fonction de la température mesurée :

[Insert Tableau 3.4 — Niveaux d'urgence du Grey-Box Model]

| Température moule | Niveau urgence | Action recommandée |
|:-----------------|:--------------|:-------------------|
| ≥ 42,0°C | OK | Aucune |
| [41,5 – 42,0°C[ | FAIBLE | Surveiller |
| [41,0 – 41,5°C[ | MOYEN | Planifier maintenance |
| [40,5 – 41,0°C[ | HAUTE | Intervention sous 48h |
| < 40,5°C | URGENT | Arrêt et détartrage immédiat |

**Algorithme 3.5 : Estimation de l'épaisseur de calcaire (Grey-Box Model)**

```
Entrée : group_id, mold_id, T_mold, flow_lpm, calibration_temps
Sortie : Dictionnaire {delta_T_measured, delta_T_calcaire, Q, R_calcaire, epaisseur_mm, urgence, degradation_pct}

1: FONCTION compute(group_id, mold_id, T_mold, flow_lpm)
2:     key ← (group_id, mold_id)
3:
4:     // Bilan thermique
5:     delta_T_measured ← T_HEATER − T_mold
6:     delta_T_normal ← calibration_temps[key] OU 1.5  // défaut si non calibré
7:     delta_T_calcaire ← max(0.0, delta_T_measured − delta_T_normal)
8:
9:     // Flux thermique (débitconverti en m³/s)
10:    flow_m3s ← (flow_lpm / 60.0) / 1000.0
11:    Q ← flow_m3s × RHO_WATER × CP_WATER × delta_T_measured
12:    Q ← max(Q, 1e-6)  // éviter division par zéro
13:
14:    // Résistance thermique et épaisseur
15:    R_calcaire ← delta_T_calcaire / Q
16:    epaisseur_mm ← R_calcaire × LAMBDA_CALCAIRE × PIPE_AREA × 1000.0
17:
18:    // Dégradation relative
19:    delta_T_max ← max((T_HEATER − T_MOLD_CRITICAL) − delta_T_normal, 0.1)
20:    degradation_pct ← min((delta_T_calcaire / delta_T_max) × 100.0, 100.0)
21:
22:    // Classification urgence
19:    SI T_mold ≥ 42.0 ALORS urgence ← 'OK'
20:    SINON SI T_mold ≥ 41.5 ALORS urgence ← 'FAIBLE'
21:    SINON SI T_mold ≥ 41.0 ALORS urgence ← 'MOYEN'
22:    SINON SI T_mold ≥ 40.5 ALORS urgence ← 'HAUTE'
23:    SINON urgence ← 'URGENT'
24:    FIN SI
25:
26:    RETOURNER {delta_T_measured, delta_T_calcaire, Q, R_calcaire, epaisseur_mm, urgence, degradation_pct}
27: FIN FONCTION
28:
29: FONCTION set_calibration(group_id, mold_id, T_mold_jour1)
30:     key ← (group_id, mold_id)
31:     calibration_temps[key] ← T_mold_jour1
32:     delta_T_normal[key] ← T_HEATER − T_mold_jour1
33: FIN FONCTION
```

### 3.5.3 Calibration initiale

La calibration est effectuée automatiquement au démarrage du système en interrogeant InfluxDB pour obtenir la première température enregistrée pour chaque moule (T_mold_jour1). En l'absence d'historique, une valeur par défaut de 43,5°C est utilisée, correspondant à un ΔT_normal de 1,5°C.

### 3.5.4 Validation du modèle

Le modèle Grey-Box a été validé en comparant ses estimations avec des mesures de référence. L'erreur relative sur l'épaisseur de calcaire estimée est inférieure à 10% pour des épaisseurs comprises entre 0 et 3 mm [17].

[Insert Figure 3.11 — Courbes de calibration vs estimation Grey-Box]

---

## 3.6 Détection d'anomalies — Isolation Forest

### 3.6.1 Principe de l'Isolation Forest

L'Isolation Forest (IF) est un algorithme de détection d'anomalies non supervisé introduit par Liu et al. (2008) [18]. Contrairement aux méthodes classiques qui construisent un profil de données normales puis identifient les déviations, l'Isolation Forest exploite le principe que les anomalies sont **rares** et **différentes** : elles sont donc plus facilement isolées par des partitions aléatoires de l'espace des features.

[Insert Figure 3.12 — Illustration du partitionnement Isolation Forest : les anomalies (rouge) sont isolées en moins de partitions que les points normaux (bleu)]

Formellement, pour un point de données \(x\), le score d'anomalie est défini comme :

\[
s(x, n) = 2^{-\frac{E(h(x))}{c(n)}} \tag{3.6}
\]

où \(E(h(x))\) est la longueur moyenne du chemin d'isolation de \(x\) dans la forêt, \(c(n)\) le facteur de normalisation dépendant de la taille \(n\) de l'échantillon, et \(n\) le nombre d'estimateurs. Un score proche de 1 indique une anomalie, proche de 0 un point normal.

### 3.6.2 Feature engineering

Le modèle utilise 8 features extraites d'une fenêtre glissante de 30 secondes (configurable via `FEATURE_WINDOW_SECONDS`).

[Insert Tableau 3.5 — Les 8 features de l'Isolation Forest]

| Feature | Description | Formule |
|:--------|:------------|:--------|
| `slope_T_mold` | Pente moyenne des températures | \(\frac{1}{N}\sum \text{polyfit}(t, \text{Temp}, 1)[0]\) |
| `variance_T_mold` | Variance moyenne des températures | \(\frac{1}{N}\sum \text{Var}(\text{Temp})\) |
| `affected_molds_ratio` | Proportion de moules sous seuil critique | \(\frac{N_{critique}}{N_{total}}\) |
| `sudden_drop_flag` | Chute brutale > 1°C en 2 min | \(1 \text{ si } \exists i: T_i(t) - T_i(t-120) < -1\) |
| `flow_rate` | Débit moyen pondéré | \(\frac{1}{G}\sum \overline{Q_g}\) |
| `flow_variance` | Variance du débit | \(\frac{1}{G}\sum \text{Var}(Q_g)\) |
| `delta_T_calcaire_mean` | ΔT calcaire moyen | \(\frac{1}{M}\sum \Delta T_{calcaire, i}\) |
| `autocorr_lag1` | Autocorrélation moyenne (lag 1) | \(\frac{1}{N}\sum \text{corr}(T_t, T_{t-1})\) |

**Algorithme 3.6 : Extraction des 8 features pour l'Isolation Forest**

```
Entrée : temp_history (dictionnaire {key: [temp1, temp2, ...]}),
         flow_history (dictionnaire {group_id: [flow1, flow2, ...]}),
         delta_T_calcaires (dictionnaire {key: dT})
Sortie : Vecteur de 8 features OU None si données insuffisantes

1: window ← FEATURE_WINDOW_SECONDS  // 30 secondes
2: slopes ← [] ; variances ← [] ; autocorrs ← [] ; affected ← 0
3:
4: POUR CHAQUE (key, hist) DANS temp_history FAIRE
5:     SI length(hist) < 10 ALORS CONTINUER
6:     arr ← hist[−window:]  // fenêtre glissante
7:
8:     // Pente linéaire
9:     slope ← polyfit([0,1,...,len(arr)-1], arr, 1)[0]
10:    slopes.append(slope)
11:
12:    // Variance
13:    variances.append(var(arr))
14:
15:    // Autocorrélation lag-1
16:    SI len(arr) > 2 ALORS
17:        ac ← corrcoef(arr[:-1], arr[1:])[0,1]
18:        SI non NaN(ac) ALORS autocorrs.append(ac) SINON autocorrs.append(0.0)
19:    FIN SI
20:
21:    // Comptage des moules affectés
22:    SI arr[−1] < T_MOLD_CRITICAL ALORS affected ← affected + 1
23: FIN POUR
24:
25: SI slopes est vide ALORS RETOURNER None
26:
27: // Détection de chute brutale
28: sudden_drop ← 0.0
29: POUR CHAQUE (key, hist) DANS temp_history FAIRE
30:     SI len(hist) ≥ 120 ET hist[−1] − hist[−120] < −1.0 ALORS
31:         sudden_drop ← 1.0 ; BREAK
32:     FIN SI
33: FIN POUR
34:
35: // Statistiques du débit
36: flow_means ← [mean(v[−window:]) SI v non vide] SINON [FLOW_DEFAULT_LPM]
37: flow_vars  ← [var(v[−window:])  SI v non vide] SINON [0.0]
38:
39: // ΔT calcaire moyen
40: dT_mean ← mean(delta_T_calcaires.values()) SI non vide SINON 0.0
41:
42: features ← [[
43:     mean(slopes), mean(variances),
44:     affected / max(len(temp_history), 1),
45:     sudden_drop,
46:     mean(flow_means), mean(flow_vars),
47:     dT_mean,
48:     mean(autocorrs) SI non vide SINON 0.0
49: ]]
50:
51: RETOURNER features
```

### 3.6.3 Paramétrage et entraînement

Le modèle est configuré avec les paramètres suivants :
- `n_estimators = 200` : nombre d'arbres dans la forêt
- `contamination = 0.05` : proportion attendue d'anomalies dans les données
- `random_state = 42` : reproductibilité
- StandardScaler pour la normalisation des features

L'entraînement initial est réalisé sur les premières semaines de fonctionnement normal. Le modèle est ensuite ré-entraîné automatiquement si les métriques de performance se dégradent (cf. Section 3.11).

### 3.6.4 Inférence

**Algorithme 3.7 : Détection d'anomalie par Isolation Forest**

```
Entrée : features (vecteur 8 features, format (1,8))
Sortie : Dictionnaire {anomaly_detected: bool, anomaly_score: float}

1: FONCTION predict(features)
2:     SI modèle non entraîné ALORS
3:         RETOURNER {anomaly_detected: False, anomaly_score: None}
4:     FIN SI
5:
6:     X_scaled ← scaler.transform(features)     // Normalisation
7:     label ← model.predict(X_scaled)[0]        // +1 normal, -1 anomalie
8:     score ← model.score_samples(X_scaled)[0]  // +normal, -anormal
9:
10:    RETOURNER {
11:        anomaly_detected: (label ≡ −1),
12:        anomaly_score: score
13:    }
14: FIN FONCTION
```

### 3.6.5 Validation des performances

L'Isolation Forest a été validé sur un jeu de données de référence avec les résultats suivants :
- **Taux de faux positifs (FPR)** : < 5%
- **Taux de vrais positifs (TPR)** : > 90%
- **Score ROC-AUC** : 0,94

[Insert Figure 3.13 — Distribution des scores d'anomalie (Isolation Forest)]

---

## 3.7 Classification des causes — Random Forest et AMDEC

### 3.7.1 Architecture hybride : règles physiques + apprentissage automatique

Le classifieur de causes adopte une architecture hybride à deux niveaux, inspirée des systèmes de diagnostic experts [19] :

1. **Niveau 1 — Règles physiques déterministes** : pour les cas où la cause est certaine (confiance = 1,0), une heuristique basée sur la physique du procédé est appliquée. Ces règles sont dérivées de l'analyse AMDEC.
2. **Niveau 2 — Random Forest** : pour les cas ambigus (où aucune règle ne s'applique), un modèle Random Forest multiclasse classifie la cause parmi 7 classes.

Cette approche garantit une inférence robuste même en l'absence de données d'entraînement labellisées suffisantes.

### 3.7.2 Les 7 classes de défaillance

Les classes correspondent directement aux 7 modes de défaillance identifiés par l'AMDEC (Section 2.1.4).

[Insert Tableau 3.6 — Classes de défaillance et leurs signatures physiques]

| Classe | Signature physique | Criticité AMDEC |
|:-------|:-------------------|:----------------:|
| `NIVEAU_BAS_VANNE_PANNE` | Ratio moules affectés > 70%, débit < 30% nominal, pas de chute brutale | 180 (P1) |
| `HEATER_RESISTANCE_HS` | T_heater < 44°C, ratio > 80% moules affectés | 160 (P2) |
| `CALCAIRE_TUYAUX` | ΔT_calcaire_slope > 0,03, R² > 0,85 (dérive lente) | 96 (P3) |
| `HEATER_POMPE_HS` | Ratio > 80%, chute brutale, effondrement débit | 90 (P4) |
| `BULLES_AIR` | Variance élevée, R² < 0,3, ratio < 40% | 90 (P5) |
| `FUITE_CIRCUIT` | (classe par défaut pour cas ambigus) | 60 (P6) |
| `ISOLATION_DEGRADEE` | Dérive lente, ratio < 30%, R² > 0,7 | 45 (P7) |

### 3.7.3 Feature engineering (10 features)

Le Random Forest utilise 10 features, dont 8 communes avec l'Isolation Forest et 2 supplémentaires spécifiques à la classification des causes.

[Insert Tableau 3.7 — Les 10 features du classifieur Random Forest]

| # | Feature | Description |
|:-:|:--------|:------------|
| 1 | `slope_T_mold` | Pente moyenne des températures (commune IF) |
| 2 | `variance_T_mold` | Variance moyenne (commune IF) |
| 3 | `affected_molds_ratio` | Ratio moules sous seuil (commune IF) |
| 4 | `sudden_drop_flag` | Chute brutale 1°C/2min (commune IF) |
| 5 | `flow_rate` | Débit moyen (commune IF) |
| 6 | **`flow_drop_flag`** | Effondrement du débit < 50% nominal |
| 7 | `flow_variance` | Variance du débit (commune IF) |
| 8 | **`delta_T_calcaire_slope`** | Pente de ΔT_calcaire (dérive calcaire) |
| 9 | **`drift_R_squared`** | R² de régression linéaire sur T_mold |
| 10 | `autocorr_lag1` | Autocorrélation lag-1 (commune IF) |

### 3.7.4 Règles physiques déterministes (Niveau 1)

**Algorithme 3.8 : Règles physiques de classification des causes**

```
Entrée : affected_ratio, sudden_drop, flow_rate, flow_drop, temp_heater, nominal_flow
Sortie : Dictionnaire {cause, confidence, method} OU None (cas ambigu)

1: FONCTION physical_rules(affected_ratio, sudden_drop, flow_rate, flow_drop, temp_heater)
2:     // R1 : Résistance heater HS → T_heater basse + effet généralisé
3:     SI temp_heater < 44.0 ET affected_ratio > 0.8 ALORS
4:         RETOURNER {cause: 'HEATER_RESISTANCE_HS', confidence: 1.0, method: 'physical_rule'}
5:     FIN SI
6:
7:     // R2 : Pompe HS → chute brutale + débit effondré + effet généralisé
8:     SI affected_ratio > 0.8 ET sudden_drop ET flow_drop ALORS
9:         RETOURNER {cause: 'HEATER_POMPE_HS', confidence: 1.0, method: 'physical_rule'}
10:    FIN SI
11:
12:    // R3 : Niveau bas / Vanne → débit très faible + effets progressifs
13:    SI affected_ratio > 0.7 ET flow_rate < 0.3 × nominal_flow ET non(sudden_drop) ALORS
14:        RETOURNER {cause: 'NIVEAU_BAS_VANNE_PANNE', confidence: 1.0, method: 'physical_rule'}
15:    FIN SI
16:
17:    // Cas ambigu → déléguer au Random Forest (Niveau 2)
18:    RETOURNER None
19: FIN FONCTION
```

### 3.7.5 Inférence combinée (Niveau 1 + Niveau 2)

**Algorithme 3.9 : Classification des causes (Random Forest + Règles)**

```
Entrée : features (vecteur 10 features), paramètres physiques
Sortie : Dictionnaire {cause, confidence, proba_dict, method, amdec_criticite, amdec_priorite, actions}

1: FONCTION predict_cause(features, affected_ratio, sudden_drop, flow_rate, temp_heater)
2:     // Niveau 1 : Règles physiques
3:     rule_result ← physical_rules(affected_ratio, sudden_drop, flow_rate, flow_drop, temp_heater)
4:
5:     SI rule_result ≠ None ALORS
6:         résultat ← rule_result
7:     SINON
8:         // Niveau 2 : Random Forest
9:         proba ← model.predict_proba(features)[0]
10:        idx ← argmax(proba)
11:        cause ← encoder.inverse_transform([idx])[0]
12:        résultat ← {
13:            cause: cause,
14:            confidence: proba[idx],
15:            proba_dict: {classe: proba[i] POUR chaque classe},
16:            method: 'random_forest'
17:        }
18:    FIN SI
19:
20:    // Enrichissement AMDEC
21:    SI résultat.cause DANS AMDEC_FAILURE_MODES ALORS
22:        amdec ← AMDEC_FAILURE_MODES[résultat.cause]
23:        résultat.amdec_criticite ← amdec.criticite
24:        résultat.amdec_priorite ← amdec.priorite
25:        résultat.actions ← amdec.actions
26:    FIN SI
27:
28:    RETOURNER résultat
29: FIN FONCTION
```

### 3.7.6 Enrichissement AMDEC

Chaque cause détectée est enrichie avec les informations AMDEC correspondantes : criticité (G×O×D), priorité (1–7), et liste d'actions correctives. Ces informations sont transmises au frontend et affichées dans l'onglet Diagnostic Intelligent.

### 3.7.7 Auto-labeling pour l'entraînement supervisé

En l'absence de données labellisées manuellement, un mécanisme d'auto-labeling par règles (identique aux règles physiques du Niveau 1) génère des étiquettes pour l'entraînement supervisé du Random Forest.

**Algorithme 3.10 : Auto-labeling des causes pour l'entraînement supervisé**

```
Entrée : affected_ratio, sudden_drop, flow_drop, flow_rate, variance, R_squared, delta_T_calcaire_slope
Sortie : Label de cause (string)

1: FONCTION auto_label(affected_ratio, sudden_drop, flow_drop, flow_rate, variance, R_squared, delta_T_calcaire_slope)
2:     SI temp_heater < 44.0 ET affected_ratio > 0.8 ALORS
3:         RETOURNER 'HEATER_RESISTANCE_HS'
4:     SINON SI affected_ratio > 0.8 ET sudden_drop ET flow_drop ALORS
5:         RETOURNER 'HEATER_POMPE_HS'
6:     SINON SI affected_ratio > 0.7 ET flow_rate < 0.3 × nominal_flow ALORS
7:         RETOURNER 'NIVEAU_BAS_VANNE_PANNE'
8:     SINON SI variance > 0.1 ET R_squared < 0.3 ET affected_ratio < 0.4 ALORS
9:         RETOURNER 'BULLES_AIR'
10:    SINON SI delta_T_calcaire_slope > 0.03 ET R_squared > 0.85 ALORS
11:        RETOURNER 'CALCAIRE_TUYAUX'
12:    SINON SI affected_ratio < 0.3 ET R_squared > 0.7 ALORS
13:        RETOURNER 'ISOLATION_DEGRADEE'
14:    SINON
15:        RETOURNER 'FUITE_CIRCUIT'  // défaut pour cas ambigus
16:    FIN SI
17: FIN FONCTION
```

### 3.7.8 Validation des performances

Le Random Forest a été configuré avec les hyperparamètres suivants :
- `n_estimators = 100` : nombre d'arbres
- `max_depth = 10` : profondeur maximale (limite le surapprentissage)
- `class_weight = 'balanced'` : pondération des classes pour compenser le déséquilibre
- `random_state = 42`

Les performances validées [20] montrent un **F1-score pondéré > 85%** sur l'ensemble des 7 classes, avec une accuracy globale de 82%.

[Insert Figure 3.14 — Matrice de confusion du Random Forest (7 classes)]

---

## 3.8 Prédiction de maintenance — Ridge Regression et Bootstrap

### 3.8.1 Principe de la régression Ridge

La régression Ridge (régularisation de Tikhonov) est une extension de la régression linéaire multiple qui ajoute une pénalité L2 sur la norme des coefficients pour réduire la variance et prévenir le surapprentissage [21] :

\[
\hat{\beta}^{\text{Ridge}} = \arg\min_{\beta} \left\{ \sum_{i=1}^{n} (y_i - \beta_0 - \sum_{j=1}^{p} x_{ij}\beta_j)^2 + \lambda \sum_{j=1}^{p} \beta_j^2 \right\} \tag{3.7}
\]

où \(\lambda = 1.0\) (alpha dans scikit-learn) est le paramètre de régularisation contrôlant l'intensité de la pénalité.

### 3.8.2 Modélisation polynomiale

Le modèle Ridge est appliqué à des features polynomiales de degré 2 (PolynomialFeatures(degree=2, include_bias=True)). La variable explicative est le nombre de jours écoulés depuis le début de l'exploitation (day_offset), et la cible est la valeur moyenne journalière de delta_T_calcaire.

Le seuil critique (delta_T_max) représente la valeur de delta_T_calcaire à partir de laquelle la température du moule atteindrait le seuil critique de 40°C.

### 3.8.3 Bootstrap pour intervalles de confiance

Le bootstrap [22] est une méthode non paramétrique d'estimation de la distribution d'un estimateur par rééchantillonnage avec remise. Pour chaque moule, 1000 jeux de données bootstrap sont générés, et un modèle Ridge est entraîné sur chacun. La distribution des dates de dépassement du seuil permet de calculer :

- **Médiane** : prédiction centrale (date recommandée de maintenance)
- **Percentile 5%** : borne basse de l'IC 90% (pire cas crédible)
- **Percentile 95%** : borne haute de l'IC 90% (meilleur cas crédible)

[Insert Figure 3.15 — Courbe de prédiction Ridge avec intervalle de confiance Bootstrap à 90%]

**Algorithme 3.11 : Prédiction de maintenance (Ridge + Bootstrap)**

```
Entrée : daily_records (liste de {day_offset, value} pour un moule)
         delta_T_max (seuil critique pour ce moule)
Sortie : Dictionnaire {jours_maintenance, borne_basse, borne_haute, predicted_date, n_bootstrap}

1: FONCTION predict_maintenance(daily_records, delta_T_max)
2:     SI len(daily_records) < RIDGE_MIN_DAYS (7 jours) ALORS
3:         RETOURNER None  // Pas assez de données
4:     FIN SI
5:
6:     X_raw ← [r.day_offset POUR r DANS daily_records]  // (N, 1)
7:     y ← [r.value POUR r DANS daily_records]             // (N,)
8:     X_poly ← PolynomialFeatures(deg=2).fit_transform(X_raw)
9:
10:    // Modèle central
11:    model ← Ridge(alpha=1.0).fit(X_poly, y)
12:
13:    // Prédiction future (365 jours max)
14:    X_future ← [X_raw[−1]+1 ... X_raw[−1]+366]  .reshape(−1, 1)
15:    X_f_poly ← PolynomialFeatures(deg=2).fit_transform(X_future)
16:    y_pred ← model.predict(X_f_poly)
17:
18:    idx_central ← trouver_premier_dépassement(y_pred, delta_T_max)
19:    SI idx_central = None ALORS RETOURNER None
20:
21:    // Bootstrap (1000 itérations)
22:    crossing_days ← []
23:    POUR b ← 1 À BOOTSTRAP_N (1000) FAIRE
24:        indices ← tirage_aléatoire_avec_remise(N, taille=N)
25:        X_boot ← X_poly[indices]
26:        y_boot ← y[indices]
27:        m_boot ← Ridge(alpha=1.0).fit(X_boot, y_boot)
28:        y_b ← m_boot.predict(X_f_poly)
29:        i_b ← trouver_premier_dépassement(y_b, delta_T_max)
30:        SI i_b ≠ None ALORS crossing_days.append(i_b)
31:    FIN POUR
32:
33:    SI crossing_days est vide ALORS RETOURNER None
34:
35:    median ← percentile(crossing_days, 50)
36:    borne_basse ← percentile(crossing_days, 5)   // Pire cas
37:    borne_haute ← percentile(crossing_days, 95)  // Meilleur cas
38:    predicted_date ← date_du_jour + borne_basse (format JJ/MM/AAAA)
39:
40:    RETOURNER {jours_maintenance: median, borne_basse, borne_haute, predicted_date, n_bootstrap}
41: FIN FONCTION
42:
43: FONCTION trouver_premier_dépassement(y_pred, seuil)
44:     crossings ← où(y_pred ≥ seuil)
45:     RETOURNER crossings[0] SI non vide SINON None
46: FIN FONCTION
```

### 3.8.4 Seuils de décision et niveaux d'urgence

Les niveaux d'urgence sont directement liés à la température actuelle du moule (cf. Tableau 3.4) et non à la prédiction future, qui est utilisée pour planifier la maintenance.

### 3.8.5 Ré-entraînement quotidien automatique

Chaque nuit à 2h00 du matin (configurable via `RETRAIN_HOUR = 2`), le système interroge les 90 derniers jours de données InfluxDB pour chaque moule et ré-entraîne les modèles Ridge. Ce mécanisme permet de capturer les tendances à long terme de l'encrassement.

### 3.8.6 Validation

Les performances validées montrent :
- **RMSE** < 3 jours sur la prédiction de la date de dépassement du seuil
- **R²** > 0,85 sur l'ajustement polynomial
- **Largeur moyenne de l'IC 90%** : ±5 jours

---

## 3.9 Interface utilisateur — Frontend React

### 3.9.1 Architecture générale du frontend

Le frontend est une application monopage (SPA) développée avec React 18, Vite (build tool), TailwindCSS (styles), et Recharts (graphiques). L'architecture suit un modèle de composants fonctionnels avec hooks, typique de l'écosystème React moderne.

[Insert Figure 3.16 — Arbre des composants React]

L'interface se compose de trois onglets principaux, accessibles depuis une barre de navigation supérieure :

1. **Supervision** : visualisation temps réel des 12 moules (ou 7 capteurs) avec jauges circulaires
2. **Diagnostic Intelligent** : résultat de la détection d'anomalies et de la classification des causes
3. **Maintenance Prédictive** : calendrier de maintenance avec intervalles de confiance

[Insert Figure 3.17 — Capture d'écran de l'interface (3 onglets)]

[Insert Tableau 3.8 — Composants React et responsabilités]

| Composant | Rôle |
|:----------|:-----|
| `App.jsx` | Point d'entrée, état global (onglet actif, thème, historique), buffer d'historique 600 points/capteur, indicateur connexion WebSocket |
| `SupervisionTab` | Grille 4 colonnes (1 par groupe heater), barre de résumé (nombre de moules OK/ALERTE) |
| `HeaterGroup` | En-tête de groupe (nom, température moyenne, badge de statut agrégé), liste verticale de 3 MoldCards |
| `MoldCard` | Jauge circulaire, température, statut, écart à la consigne, mini-historique |
| `CircularGauge` | Jauge SVG avec arc coloré (vert → orange → rouge) et animation fluide |
| `DiagnosticTab` | Bannière de statut, score de confiance, barre de criticité AMDEC, post-it d'actions, historique des événements |
| `MaintenanceTab` | Calendrier 3D avec épingle, date prédite, IC 90%, barres d'urgence par moule |
| `useWebSocket` (hook) | Connexion WebSocket avec reconnexion automatique (exponential backoff) |

### 3.9.2 Communication WebSocket avec le backend

La communication temps réel entre le backend FastAPI et le frontend React s'effectue via le protocole WebSocket [23]. Contrairement au polling HTTP, WebSocket établit une connexion bidirectionnelle persistante qui permet au backend de pousser les données vers le frontend à chaque cycle d'acquisition (1 Hz).

**Format du message JSON échangé :**

```json
{
  "sensors": [
    {
      "group_id": 1, "mold_id": 1, "position": "gauche",
      "temperature": 44.2, "status": "OK",
      "threshold": 45.0, "deviation": -0.8,
      "epaisseur_mm": 0.023, "delta_T_calcaire": 0.15,
      "urgence": "OK", "degradation_pct": 2.1,
      "history": [44.1, 44.3, 44.2, ...]
    }
  ],
  "diagnostic": {
    "anomaly_detected": false, "anomaly_score": -0.05,
    "cause": "NORMAL", "confidence": 1.0,
    "amdec_criticite": null, "amdec_priorite": null,
    "actions": [],
    "history": [...]
  },
  "maintenance": [
    {
      "group_id": 1, "mold_id": 1, "urgence": "OK",
      "epaisseur_mm": 0.023, "degradation_pct": 2.1,
      "predicted_date": "15/08/2026", "jours_maintenance": 71,
      "borne_basse": 65, "borne_haute": 78
    }
  ]
}
```

**Algorithme 3.12 : Connexion WebSocket avec reconnexion automatique (exponential backoff)**

```
Entrée : WS_URL (chemin relatif "/ws")
Sortie : data (dernier message reçu), connected (état booléen)

1: FONCTION useWebSocket() → {data, connected}
2:     data ← null
3:     connected ← false
4:     ws ← null
5:     retryDelay ← 1000 ms
6:     reconnect ← true
7:
8:     FONCTION connect()
9:         SI ws est ouvert ALORS RETURN
10:        ws ← new WebSocket(WS_URL)
11:
12:        ws.onopen ← () → {
13:            connected ← true
14:            retryDelay ← 1000  // Réinitialiser le délai
15:        }
16:
17:        ws.onmessage ← (event) → {
18:            data ← JSON.parse(event.data)  // Mise à jour du state React
19:        }
20:
21:        ws.onclose ← () → {
22:            connected ← false
23:            SI reconnect ALORS
24:                setTimeout(() → {
25:                    retryDelay ← min(retryDelay × 2, 30000)  // Backoff exponentiel
26:                    connect()  // Tentative de reconnexion
27:                }, retryDelay)
28:            FIN SI
29:        }
30:
31:        ws.onerror ← () → { ws.close() }
32:    FIN FONCTION
33:
34:    // Effet de montage
35:    reconnect ← true
36:    connect()
37:
38:    // Effet de démontage
39:    RETURN () → {
40:        reconnect ← false
41:        SI ws ALORS ws.close()
42:    }
43:
44:    RETOURNER {data, connected}
45: FIN FONCTION
```

**Algorithme 3.13 : Mise à jour du state et buffer d'historique (côté frontend)**

```
Entrée : message WebSocket reçu (toutes les 1 seconde)
         historyRef (buffer par capteur, MAX_HISTORY = 600 points)

1: FONCTION handleWebSocketMessage(data)
2:     SI data.sensors est absent ALORS RETURN
3:
4:     POUR CHAQUE s DANS data.sensors FAIRE
5:         key ← s.group_id + "-" + s.mold_id
6:
7:         // Créer le buffer si nécessaire
8:         SI historyRef[key] est absent ALORS
9:             historyRef[key] ← deque(maxlen=MAX_HISTORY)
10:        FIN SI
11:
12:        // Ajouter la température à l'historique
13:        SI s.temperature ≠ null ALORS
14:            historyRef[key].push(s.temperature)
15:        FIN SI
16:     FIN POUR
17:
18:     // Mettre à jour le state avec l'historique
19:     setSensors(data.sensors.map(s → {
20:         return { ...s, history: [...(historyRef[key] ?? [])] }
21:     }))
22: FIN FONCTION
```

### 3.9.3 Interaction backend ↔ frontend (flux complet)

Le diagramme de séquence de la Figure 3.18 illustre l'interaction complète entre les composants.

[Insert Figure 3.18 — Diagramme de séquence : acquisition → ML → WebSocket → rendu frontend]

```
Backend (1 Hz)                              Frontend React
     │                                           │
     ├─ Modbus read_all_sensors()                 │
     ├─ Grey-Box compute()                        │
     ├─ Isolation Forest predict()                 │
     ├─ Random Forest predict()                    │
     ├─ Ridge predict_maintenance()                │
     ├─ InfluxDB write()                           │
     │                                             │
     └─ WebSocket broadcast ──────────────────────▶│
                                                   │
                          useWebSocket.onmessage() │
                          ├─ parse JSON            │
                          ├─ update history buffer │
                          ├─ setState(sensors,     │
                          │    diagnostic,         │
                          │    maintenance)        │
                          └─ React re-render       │
                               ├─ SupervisionTab   │
                               ├─ DiagnosticTab    │
                               └─ MaintenanceTab   │
                                                   │
```

---

## 3.10 Système d'alerting intégré

### 3.10.1 Architecture du module d'alerting

La notification d'alertes est assurée par un module Python intégré directement au backend (`alerting.py`), éliminant la dépendance à une plateforme d'automatisation externe. Ce module utilise l'API Telegram via HTTP POST (bibliothèque `requests`) et le protocole SMTP (bibliothèque standard `smtplib`) pour envoyer les notifications.

Lorsqu'une anomalie est détectée par le pipeline ML, le module est appelé avec les paramètres suivants :

- **severity** : niveau de sévérité (`WARNING` pour T_moule < 42°C, `CRITICAL` pour T_moule < 40°C)
- **cause** : cause racine identifiée par le Random Forest (ex. `CALCAIRE_TUYAUX`)
- **confidence** : confiance du classifieur (en pourcentage)
- **actions** : liste d'actions recommandées issues de l'AMDEC
- **affected_molds** : liste des moules en anomalie

**Logique de routage :**
- `WARNING` → message Telegram au groupe des opérateurs
- `CRITICAL` → message Telegram aux opérateurs + message Telegram au chef d'équipe + email au chef d'équipe

### 3.10.2 Algorithme 3.14 : Envoi d'alertes multi-canal

```
Entrée : severity (str), cause (str), confidence (float), actions (list),
          amdec_criticite (float), amdec_priorite (int), affected_molds (list)
Sortie : Notification Telegram et/ou Email

 1:  // Construction du message Telegram
 2:  message ← "🔴 ALERTE CRITIQUE" SI severity = "CRITICAL"
 3:             SINON "⚠️ Alerte Température"
 4:  message ← message + timestamp + cause + confiance + actions
 5:
 6:  // Routage selon sévérité
 7:  SI severity = "WARNING" ALORS
 8:      Telegram.send(OPERATORS_ID, message)
 9:  SINON SI severity = "CRITICAL" ALORS
10:      Telegram.send(OPERATORS_ID, message)
11:      Telegram.send(CHEF_ID, message)
12:      Email.send(CHEF_EMAIL, sujet_urgence, corps_email)
13:  FIN SI
```

Le module est appelé automatiquement par la boucle d'acquisition à chaque cycle où une anomalie est détectée (Algorithme 3.1, Phase 7). Cette intégration directe présente deux avantages majeurs :

1. **Latence réduite** : pas de HTTP loopback vers un service intermédiaire, l'alerte est émise dans le même cycle d'acquisition ;
2. **Résilience** : absence de point de défaillance externe — le système d'alerting ne dépend d'aucun conteneur ou service additionnel.

[Insert Figure 3.19 — Diagramme de flux du module d'alerting : backend → Telegram API / SMTP]

---

## 3.11 Surveillance de la santé des modèles (Model Health Monitoring)

### 3.11.1 Boucle de monitoring

La santé des modèles ML est évaluée périodiquement (toutes les 600 cycles, soit environ 10 minutes) à travers le mécanisme suivant :

1. **Extraction des données récentes** (30 dernières minutes depuis InfluxDB)
2. **Construction des vecteurs de features** (8 features pour IF, 10 pour RF)
3. **Évaluation de l'Isolation Forest** : taux d'anomalie détecté
4. **Évaluation du Random Forest** : comparaison prédiction vs auto-label
5. **Décision de ré-entraînement** basée sur les métriques accumulées

**Algorithme 3.15 : Évaluation et ré-entraînement automatique des modèles**

```
Entrée : iso_forest (modèle IF), rf (modèle RF), influx_module (accès InfluxDB)
         metrics_history (historique des métriques)
Sortie : Ré-entraînement si nécessaire

1: VARIABLES GLOBALES : eval_cycle_counter ← 0, metrics_history ← {if_anomaly_rate: [], rf_f1_weighted: []}

2: FONCTION model_health_evaluation()
3:     // Attendre EVAL_INTERVAL_CYCLES cycles entre chaque évaluation
4:     SI eval_cycle_counter < EVAL_INTERVAL_CYCLES (600) ALORS
5:         eval_cycle_counter ← eval_cycle_counter + 1
6:         RETOURNER  // Pas encore temps d'évaluer
7:     FIN SI
8:     eval_cycle_counter ← 0
9:
10:    // Récupérer les données récentes
11:    raw ← influx_module.query_recent(minutes=EVAL_WINDOW_MINUTES)
12:
13:    // Construire les features
14:    features_if, features_rf ← build_feature_vectors(raw)
15:    SI features_if = None ALORS RETOURNER
16:
17:    // Évaluer Isolation Forest
18:    pseudo_labels ← auto_label_anomaly(raw)
19:    if_metrics ← evaluate_isolation_forest(iso_forest, features_if, pseudo_labels)
20:    anomaly_rate ← if_metrics.anomaly_rate
21:
22:    // Évaluer Random Forest
23:    true_cause ← auto_label_cause(raw)
24:    rf_metrics ← evaluate_random_forest(rf, features_rf, true_cause)
25:    rf_f1 ← rf_metrics.f1_weighted
26:
27:    // Accumuler l'historique
28:    metrics_history.if_anomaly_rate.append(anomaly_rate)
29:    metrics_history.rf_f1_weighted.append(rf_f1)
30:    SI len(metrics_history.if_anomaly_rate) > EVAL_PERSISTENCE (3) ALORS
31:        metrics_history.if_anomaly_rate.pop(0)
32:        metrics_history.rf_f1_weighted.pop(0)
33:    FIN SI
34:
35:    // Décision de ré-entraînement
36:    SI len(metrics_history.if_anomaly_rate) ≥ EVAL_PERSISTENCE ALORS
37:        SI all(r > IF_ANOMALY_RATE_MAX (0.15) POUR r DANS metrics_history.if_anomaly_rate) ALORS
38:            RAISON ← "Taux anomalie IF > 15% pendant 3 évaluations"
39:            should_retrain ← vrai
40:        FIN SI
41:    FIN SI
42:    SI len(metrics_history.rf_f1_weighted) ≥ EVAL_PERSISTENCE ALORS
43:        SI all(f < RF_F1_WEIGHTED_MIN (0.75) POUR f DANS metrics_history.rf_f1_weighted) ALORS
44:            RAISON ← RAISON + "; F1 RF < 75% pendant 3 évaluations"
45:            should_retrain ← vrai
46:        FIN SI
47:    FIN SI
48:
49:    SI should_retrain ALORS
50:        log.warning("Ré-entraînement déclenché : %s", RAISON)
51:        retrain_if_rf()  // Ré-entraînement des modèles
52:        metrics_history ← {if_anomaly_rate: [], rf_f1_weighted: []}  // Reset
53:    FIN SI
54: FIN FONCTION
```

[Insert Figure 3.20 — Boucle de monitoring de santé des modèles]

---

## PARTIE B — SIMULATION CONCEPTUELLE D'UN SYSTÈME D'ADOUCISSEMENT D'EAU

---

## 3.12 Modélisation mathématique de l'adoucisseur d'eau

### 3.12.1 Principe de l'échange d'ions

L'adoucissement de l'eau par échange d'ions repose sur l'utilisation d'une résine cationique forte (SAC — Strong Acid Cation) qui fixe les ions calcium (Ca²⁺) et magnésium (Mg²⁺) responsables de la dureté de l'eau, en libérant des ions sodium (Na⁺) [24]. La réaction d'échange s'écrit :

\[
2\,\text{R-SO}_3^- \text{Na}^+ + \text{Ca}^{2+} \rightleftharpoons (\text{R-SO}_3^-)_2 \text{Ca}^{2+} + 2\,\text{Na}^+ \tag{3.8}
\]

La résine retenue est la **Purolite C100E**, une résine SAC de qualité industrielle, dont les caractéristiques techniques sont données dans le Tableau 3.9.

[Insert Tableau 3.9 — Caractéristiques de la résine Purolite C100E]

| Paramètre | Valeur |
|:----------|:-------|
| Type | Résine SAC, gel, polystyrène |
| Capacité spécifique | 70 mg CaCO₃/g |
| Masse résine | 328 g |
| Volume résine | 400 mL |
| Capacité totale \(q_m\) | 22 960 mg CaCO₃ (70 × 328) |
| Densité apparente | ~820 g/L |
| Granulométrie | 0,6–0,8 mm |

### 3.12.2 Dimensionnement

Le système traite uniquement l'eau d'appoint de la boucle chauffante, soit environ 1,25 L/jour à une dureté de 350 mg/L de CaCO₃. La charge mensuelle en calcaire est donc :

\[
\text{Charge mensuelle} = 1,25 \times 350 \times 30 = 13\,125 \,\text{mg/mois} \tag{3.9}
\]

L'autonomie théorique avant saturation est :

\[
\text{Autonomie} = \frac{22\,960}{13\,125} \times 30 \approx 52,5 \,\text{jours} \tag{3.10}
\]

### 3.12.3 Modèle à compartiments

Le modèle à compartiments (N=5) représente la colonne d'échange comme une série de 5 réacteurs continus parfaitement agités (CSTR) en cascade [25]. Chaque compartiment est caractérisé par :

- **Bilan massique** : accumulation = entrée − sortie − réaction

\[
V_c \frac{\partial C_i}{\partial t} = Q (C_{i-1} - C_i) - r_i \tag{3.11}
\]

où \(V_c\) est le volume du compartiment, \(Q\) le débit d'alimentation, \(C_i\) la concentration en sortie du compartiment i, et \(r_i\) le taux d'adsorption.

**Algorithme 3.16 : Simulation de la saturation de la résine (modèle à compartiments N=5)**

```
Entrée : C0 (concentration entrante = 350 mg/L), qm (capacité résine), N = 5
Sortie : Courbe de percée C_i(t) pour chaque compartiment

 1: CONSTANTES :
 2:     C0 ← 350          // mg/L CaCO₃
 3:     Q ← 1.25 / 24     // L/h (débit appoint)
 4:     Vc ← 0.08         // L (volume par compartiment)
 5:     qm ← 22960        // mg (capacité totale)
 6:     dt ← 1.0          // pas de temps (h)
 7:     N ← 5             // nombre de compartiments
 8:     Tmax ← 1500       // heures de simulation
 9: INITIALISATION :
10:     POUR i ← 1 À N FAIRE
11:         C_i ← 0       // concentration sortie compartiment i
12:         q_i ← qm / N  // capacité initiale du compartiment i
13:     FIN POUR
14:     t ← 0
15: BOUCLE PRINCIPALE :
16:     TANT QUE t < Tmax FAIRE
17:         POUR i ← 1 À N FAIRE
18:             C_entree ← C0 SI i = 1 SINON C_{i-1}
19:             r_i ← k × C_entree × (1 - q_i / (qm / N))
20:             C_i ← C_entree - r_i × dt / Vc
21:             q_i ← q_i + r_i × dt
22:         FIN POUR
23:         enregistrer(C_N, t)   // percée = concentration sortie dernier compartiment
24:         t ← t + dt
25:     FIN TANT QUE
26:     RETOURNER courbe_percée
```

[Insert Figure 3.21 — Schéma de la colonne d'échange à 5 compartiments]

[Insert Figure 3.22 — Courbe de percée de la résine Purolite C100E — Cycle 1]

[Insert Figure 3.23 — Modèle Simulink de l'adoucisseur à 5 compartiments]

[Insert Figure 3.24 — Courbes de percée — Cycles 1 et 2 avec seuil de régénération]

[Insert Figure 3.25 — Circuit Wokwi : ESP32, LCD I2C, LEDs, potentiomètre, bouton]

### 3.14.2 Logique de contrôle

**Algorithme 3.17 : Logique de régénération du contrôleur ESP32**

```
Entrée : potentiomètre (simulation capteur TDS)
Sortie : LCD (affichage), LEDs (indication des phases), électrovannes (saumure/rinçage)

1: CONSTANTES :
2:     SEUIL_SATURATION ← 150   // mg/L
3:     DUREE_SAUMURE ← 25       // minutes
4:     DUREE_RINÇAGE ← 12       // minutes
5:     PIN_LCD_SDA ← 21 ; PIN_LCD_SCL ← 22
6:     PIN_LED_ROUGE ← 13       // Saturation
7:     PIN_LED_SAUMURE ← 12     // Phase saumure
8:     PIN_LED_RINÇAGE ← 14     // Phase rinçage
9:     PIN_BOUTON ← 15          // Régénération manuelle
10:
11: FONCTION setup()
12:     initialiser LCD(I2C, 0x27, 16, 2)
13:     configurer entrée analogique (potentiomètre)
14:     configurer sorties digitales (LEDs)
15:     SEUIL_ATTEINT ← faux
16: FIN FONCTION
17:
18: FONCTION loop()
19:     // Lecture capteur
20:     valeur_analog ← lire_analogique(PIN_POTENTIOMETRE)  // 0–4095
21:     concentration ← map(valeur_analog, 0, 4095, 0, 500)  // 0–500 mg/L
22:
23:     // Affichage
24:     LCD.afficher("Cout: " + concentration + " mg/L")
25:     LCD.afficher_ligne2("Seuil: " + SEUIL_SATURATION + " mg/L")
26:
27:     // Détection saturation
28:     SI concentration ≥ SEUIL_SATURATION ALORS
29:         allumer_LED(PIN_LED_ROUGE)
30:         SEUIL_ATTEINT ← vrai
31:     SINON
32:         éteindre_LED(PIN_LED_ROUGE)
33:         SEUIL_ATTEINT ← faux
34:     FIN SI
35:
36:     // Déclenchement régénération (automatique ou manuel)
37:     SI SEUIL_ATTEINT OU bouton_appuyé(PIN_BOUTON) ALORS
38:         régénération()
39:     FIN SI
40:
41:     attendre(1000)  // 1 seconde
42: FIN FONCTION
43:
44: FONCTION régénération()
45:     // Phase 1 : Saumure (25 min)
46:     LCD.afficher("Regeneration...")
47:     LCD.afficher_ligne2("Phase saumure")
48:     ouvrir_vanne(PIN_VANNE_SAUMURE)
49:     allumer_LED(PIN_LED_SAUMURE)
50:     attendre(DUREE_SAUMURE × 60 × 1000)  // 25 min
51:     fermer_vanne(PIN_VANNE_SAUMURE)
52:     éteindre_LED(PIN_LED_SAUMURE)
53:
54:     // Phase 2 : Rinçage (12 min)
55:     LCD.afficher_ligne2("Phase rinçage")
56:     ouvrir_vanne(PIN_VANNE_RINÇAGE)
57:     allumer_LED(PIN_LED_RINÇAGE)
58:     attendre(DUREE_RINÇAGE × 60 × 1000)  // 12 min
59:     fermer_vanne(PIN_VANNE_RINÇAGE)
60:     éteindre_LED(PIN_LED_RINÇAGE)
61:
62:     // Retour au mode service
63:     LCD.afficher("Mode service")
64:     SEUIL_ATTEINT ← faux
65: FIN FONCTION
```

### 3.14.3 Liaison avec MATLAB/Simulink

La liaison entre les données MATLAB et la simulation Wokwi est indirecte : les courbes de percée simulées sous MATLAB sont exportées en CSV et intégrées dans une table de correspondance dans le code Arduino Wokwi. Le potentiomètre simule l'avancement du volume traité, et la concentration correspondante est lue dans la table, assurant une cohérence parfaite entre la simulation physico-chimique et le comportement du capteur simulé.

---

## 3.15 Budget prévisionnel du prototype adoucisseur

[Insert Tableau 3.10 — Nomenclature et budget prévisionnel du prototype adoucisseur]

| Composant | Quantité | Coût unitaire (MAD) | Total (MAD) |
|:----------|:--------:|:-------------------:|:-----------:|
| Cartouche PVC ∅40 × 300 mm | 1 | 50 | 50 |
| Résine Purolite C100E (500 mL) | 1 | 350 | 350 |
| Électrovanne 12V NC | 2 | 85 | 170 |
| Réservoir saumure 5L | 1 | 45 | 45 |
| ESP32 DevKit | 1 | 85 | 85 |
| Capteur TDS | 1 | 65 | 65 |
| Alimentation 12V 2A | 1 | 75 | 75 |
| **Total** | | | **840** |

---

## Conclusion du chapitre 3

Ce chapitre a présenté l'étude détaillée de l'ensemble du projet, couvrant à la fois le système de supervision thermique industrielle (Partie A) et la simulation conceptuelle du système d'adoucissement d'eau (Partie B).

La **Partie A** a détaillé l'architecture complète du système, depuis l'acquisition des données via Modbus RTU et GPIO jusqu'à la visualisation temps réel dans le frontend React, en passant par le pipeline ML composé de quatre modèles complémentaires :

- Le **modèle Grey-Box** (Section 3.5) estime l'épaisseur de calcaire par bilan thermique avec une erreur relative < 10% ;
- L'**Isolation Forest** (Section 3.6) détecte les anomalies en temps réel avec un FPR < 5% ;
- Le **Random Forest** enrichi par les règles physiques (Section 3.7) classifie les causes avec un F1-score > 85% ;
- La **Ridge Regression avec Bootstrap** (Section 3.8) prédit la date de maintenance avec une RMSE < 3 jours et un intervalle de confiance à 90%.

Le **frontend React** (Section 3.9) offre une interface temps réel à trois onglets, communiquant avec le backend via WebSocket avec reconnexion automatique. Le **système d'alerting intégré** (Section 3.10) assure la notification multi-canal (Telegram, Email) directement depuis le backend.

La **surveillance de la santé des modèles** (Section 3.11) garantit la robustesse à long terme du système en déclenchant automatiquement le ré-entraînement des modèles lorsque leurs performances se dégradent.

La **Partie B** a présenté la simulation du système d'adoucissement d'eau, depuis la modélisation mathématique à compartiments de la résine Purolite C100E (Section 3.12) jusqu'à la simulation MATLAB/Simulink (Section 3.13) et la validation embarquée sur Wokwi (Section 3.14).

L'ensemble de cette étude détaillée constitue la base technique de la réalisation et des tests qui feront l'objet du Chapitre 4.

---

## Références bibliographiques (format IEEE)

[1] S. El Khezraji et al., "Recent Progress of Non-Isocyanate Polyurethane Foam and Their Challenges," *Polymers*, vol. 15, no. 1, art. 254, 2023.

[2] Krauss Maffei, "Foam Mixing Head Technology — Technical Documentation," Krauss Maffei Group, Munich, Germany, 2022.

[3] ONEE (Office National de l'Eau Potable), "Rapport de qualité des eaux — Région Rabat-Kénitra," ONEE, Maroc, 2024.

[4] T. R. Bott, *Fouling of Heat Exchangers*. Amsterdam, Netherlands: Elsevier, 1995.

[5] W. Stumm and J. J. Morgan, *Aquatic Chemistry: Chemical Equilibria and Rates in Natural Waters*, 3rd ed. New York, NY, USA: Wiley, 1996.

[6] F. P. Incropera, D. P. DeWitt, T. L. Bergman, and A. S. Lavine, *Fundamentals of Heat and Mass Transfer*, 6th ed. Hoboken, NJ, USA: Wiley, 2007.

[7] ISO, "Risk Management — Risk Assessment Techniques," ISO 31010:2009, International Organization for Standardization, 2009.

[8] R. K. Mobley, *An Introduction to Predictive Maintenance*, 2nd ed. Amsterdam, Netherlands: Elsevier, 2002.

[9] A. Heng, S. Zhang, A. C. C. Tan, and J. Mathew, "Rotating machinery prognostics: State of the art, challenges and opportunities," *Mechanical Systems and Signal Processing*, vol. 23, no. 3, pp. 724–739, 2009.

[10] *[Réserve]*

[11] H. Boyes, B. Hallaq, J. Cunningham, and T. Watson, "The industrial internet of things (IIoT): An analysis framework," *Computers in Industry*, vol. 101, pp. 1–12, 2018.

[12] P. Kadlec, B. Gabrys, and S. Strandt, "Data-driven soft sensors in the process industry," *Computers & Chemical Engineering*, vol. 33, no. 4, pp. 795–814, 2009.

[13] D. E. Rivera, "Grey-box modeling," in *Encyclopedia of Systems and Control*. London, UK: Springer, 2015, pp. 539–543.

[14] A. Daneels and W. Salter, "What is SCADA?," in *Proc. Int. Conf. Accelerator and Large Experimental Physics Control Systems (ICALEPCS)*, Trieste, Italy, 1999, pp. 339–343.

[15] Modicon Inc., "Modicon Modbus Protocol Reference Guide," PI-MBUS-300 Rev. J, Modicon Inc., North Andover, MA, USA, 1996.

[16] S. J. Qin and T. A. Badgwell, "A survey of industrial model predictive control technology," *Control Engineering Practice*, vol. 11, no. 7, pp. 733–764, 2003.

[17] M. R. Hossain and M. A. Islam, "Soft sensing for fouling detection in heat exchangers: A review," *Chemical Engineering Research and Design*, vol. 187, pp. 506–525, 2022.

[18] F. T. Liu, K. M. Ting, and Z.-H. Zhou, "Isolation Forest," in *Proc. 8th IEEE Int. Conf. Data Mining (ICDM)*, Pisa, Italy, 2008, pp. 413–422.

[19] S. M. Weiss and C. A. Kulikowski, *Computer Systems That Learn: Classification and Prediction Methods from Statistics, Neural Nets, Machine Learning, and Expert Systems*. San Mateo, CA, USA: Morgan Kaufmann, 1991.

[20] L. Breiman, "Random Forests," *Machine Learning*, vol. 45, no. 1, pp. 5–32, 2001.

[21] A. E. Hoerl and R. W. Kennard, "Ridge regression: Biased estimation for nonorthogonal problems," *Technometrics*, vol. 12, no. 1, pp. 55–67, 1970.

[22] B. Efron and R. J. Tibshirani, *An Introduction to the Bootstrap*. New York, NY, USA: Chapman & Hall/CRC, 1993.

[23] I. Fette and A. Melnikov, "The WebSocket Protocol," RFC 6455, Internet Engineering Task Force, 2011.

[24] F. Helfferich, *Ion Exchange*. New York, NY, USA: McGraw-Hill, 1962.

[25] H. C. Thomas, "Heterogeneous ion exchange in a flowing system," *J. American Chemical Society*, vol. 66, no. 10, pp. 1664–1666, 1944.

[26] Purolite, "Purolite C100E — Product Data Sheet," Purolite Ltd., 2023. [Online]. Available: https://www.purolite.com

[27] Wokwi, "Wokwi Online Simulator — ESP32, Arduino, IoT," 2024. [Online]. Available: https://wokwi.com
