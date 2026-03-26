# Supervision Thermique Industrielle : Diagnostic intelligent des Causes et Maintenance Prédictive de l'Encrassement par Soft Sensing et Machine Learning

  ***Projet de Fin d'Études 2025-2026 - ENSA Kénitra***

## Vue d'Ensemble
Ce projet, réalisé dans le cadre du Projet de Fin d'Études (PFE) 2025-2026 à l'ENSA Kénitra, a été développé pour Yazaki Morocco. L'objectif principal est de superviser la ligne de production de mousse (foaming), qui comprend 12 moules, afin de détecter et diagnostiquer les causes de baisse de température. Le système intègre des technologies de machine learning et de soft sensing pour une maintenance prédictive.

## Fonctionnalités Principales

Le projet est un système de supervision thermique avancé qui passe d'une simple surveillance à un diagnostique intelligent des causes et une maintenance prédictive. Les fonctionnalités clés incluent :

Acquisition et Monitoring Temps Réel : Le système collecte des données en continu à partir de 12 capteurs de température et de 3 capteurs de débit via le protocole Modbus RTU. Un tableau de bord développé avec React affiche ces données en temps réel.

Détection et Diagnostic Intelligent : Une anomalie de température est détectée par un modèle Isolation Forest. Ensuite, un modèle Random Forest, basé sur l'analyse AMDEC (Analyse des Modes de Défaillance, de leurs Effets et de leur Criticité), diagnostique la cause probable parmi 7 classes de défaillance.

Maintenance Prédictive par Soft Sensing : Le système utilise un modèle physique de type Grey-Box pour estimer l'épaisseur de calcaire dans les circuits de refroidissement. Cette méthode de "capteur logiciel" (soft sensing) permet de prédire l'encrassement sans capteur direct, optimisant ainsi la planification de la maintenance.

Alertes et Automatisation : Des alertes multi-canaux (Dashboard, Telegram, Email, LED) sont déclenchées via des workflows n8n. Un rapport Excel est également généré automatiquement chaque jour pour le suivi de la production.

## Architecture Technique
L'architecture du projet est structurée en trois niveaux distincts :

**Niveau 1** : Acquisition Physique

Composé d'un Raspberry Pi 4 8GB qui interroge les 12 capteurs de température et 3 capteurs de débit via Modbus RTU.

Inclut un système d'alertes visuelles avec une LED WS2812B.

**Niveau 2** : Traitement et Machine Learning

C'est le cœur intelligent du système. Il reçoit les données brutes et applique les modèles de machine learning.

**Isolation Forest** pour la détection d'anomalies (contamination 5%, 200 estimators).

**Random Forest** pour classifier la cause de l'anomalie (7 classes basées sur l'AMDEC, accuracy ~85%, 100 estimators).

**Ridge Regression** et un modèle Grey-Box pour la maintenance prédictive et l'estimation de l'épaisseur de calcaire (IC 90% avec bootstrap 1000 iterations).

L'AMDEC est intégrée pour prioriser la criticité des défaillances (calculée par Gravité × Occurrence × Détection).

**Niveau 3** : Présentation et Automatisation

**Dashboard React** : Interface utilisateur pour la visualisation en temps réel via WebSocket.

**InfluxDB** : Base de données pour le stockage des séries temporelles.

**n8n** : Plateforme d'automatisation pour la gestion des alertes (Telegram/Email) et la génération de rapports.

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
