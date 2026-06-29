# Plan du rapport — Supervision Thermique

---

## Remerciements

## Liste des figures

## Liste des tableaux

## Liste des algorithmes

## Acronyms

## Introduction

---

## Chapitre 1 — Présentation de l'entreprise d'accueil

**Introduction**

1.1 Le groupe Yazaki
: 1.1.1 Historique
: 1.1.2 Chiffres clés et présence mondiale
: 1.1.3 Domaines d'activité

1.2 YMOK : Yazaki Morocco Kénitra
: 1.2.1 Création et localisation
: 1.2.2 Fiche signalétique
: 1.2.3 Politique qualité et démarche 5S

1.3 Structure organisationnelle

1.4 Activités et processus de production
: 1.4.1 Zone de coupe — P1
: 1.4.2 Zone de pré-assemblage — P2
: 1.4.3 Zone d'assemblage — P3
: 1.4.4 Zone de foaming

1.5 Déroulement du stage

**Conclusion**

---

## Chapitre 2 — Contexte général du Projet

**Introduction**

2.1 Description de la problématique

2.2 Analyse des modes de défaillance (AMDEC)

2.3 Cahier des charges
: 2.3.1 Objectifs
: 2.3.2 Exigences fonctionnelles
: 2.3.3 Exigences non fonctionnelles

2.4 Étude préalable
: 2.4.1 Approches envisageables
: 2.4.2 Limites de la solution existante

2.5 Plan d'action : le cycle en V

2.6 Planning prévisionnel

**Conclusion**

---

## Chapitre 3 — Étude détaillée du projet

**Introduction**

3.1 Architecture globale du système
: 3.1.1 Architecture à trois niveaux

3.2 Architecture matérielle

3.3 Architecture détaillée

3.4 Conception logicielle — Diagrammes UML
: 3.4.1 Diagramme de cas d'utilisation
: 3.4.2 Diagramme de classes
: 3.4.3 Diagramme d'activité
: 3.4.4 Diagramme de séquence
: 3.4.5 Diagramme d'états
: 3.4.6 Modèle conceptuel des données (MCD)

3.5 Modèle Grey-Box pour l'estimation de l'encrassement
: 3.5.1 Principe du soft sensing
: 3.5.2 Équations du bilan thermique
: 3.5.3 Niveaux d'urgence

3.6 Détection d'anomalies par Isolation Forest
: 3.6.1 Principe théorique
: 3.6.2 Caractéristiques utilisées

3.7 Classification des causes — Approche hybride
: 3.7.1 Principe à deux niveaux
: 3.7.2 Règles physiques (Niveau 1)
: 3.7.3 Modèle aléatoire (Niveau 2)

3.8 Prédiction de maintenance par régression Ridge
: 3.8.1 Principe
: 3.8.2 Estimation de l'incertitude par Bootstrap
: 3.8.3 Fréquence et seuils

3.9 Système d'alertes

**Conclusion**

---

## Chapitre 4 — Réalisation et résultats

**Introduction**

4.1 Outils et technologies de réalisation
: 4.1.1 Matériel utilisé
: 4.1.2 Stack backend
: 4.1.3 Stack frontend
: 4.1.4 Modules d'apprentissage automatique
: 4.1.5 Librairies Python
: 4.1.6 Protocoles de communication

4.2 Réalisation matérielle
: 4.2.1 Configuration du système embarqué
: 4.2.2 Câblage du bus RS485 en daisy chain
: 4.2.3 Adressage des modules de transmission
: : 4.2.3.1 Détection du bus et adressage
: : 4.2.3.2 Vérification du bus
: 4.2.4 Raccordement du débitmètre YF-S201

4.3 Réalisation logicielle
: 4.3.1 Acquisition des données
: : 4.3.1.1 Acquisition de la température
: : 4.3.1.2 Acquisition du débit
: 4.3.2 Stockage temporel — InfluxDB
: : 4.3.2.1 Modèles pré-entraînés persistés
: 4.3.3 Orchestration du pipeline de diagnostic
: : 4.3.3.1 Boucle principale d'acquisition
: : 4.3.3.2 Ré-entraînement programmé des modèles
: 4.3.4 Modèle Grey-Box — implémentation du soft sensing
: 4.3.5 Détection d'anomalies par Isolation Forest
: : 4.3.5.1 Extraction des caractéristiques
: : 4.3.5.2 Modèle et décision
: 4.3.6 Classification des causes — approche hybride N1/N2
: : 4.3.6.1 Architecture à deux niveaux
: : 4.3.6.2 Règles physiques (N1)
: : 4.3.6.3 Random Forest (N2)
: : 4.3.6.4 Performance du classifieur
: : 4.3.6.5 Étiquetage automatique pour l'entraînement supervisé
: 4.3.7 Maintenance prédictive par Ridge Régression
: : 4.3.7.1 Implémentation
: : 4.3.7.2 Intervalle de confiance par Bootstrap
: 4.3.8 Interface de supervision
: : 4.3.8.1 Architecture frontend
: 4.3.9 Système d'alertes multicanal
: : 4.3.9.1 Canal Telegram
: : 4.3.9.2 Canal SMTP
: : 4.3.9.3 Niveaux de sévérité et déclenchement

4.4 Tests et vérification
: 4.4.1 Stratégie de test
: 4.4.2 Tests unitaires
: 4.4.3 Tests d'intégration
: : 4.4.3.1 Monkey patching des dépendances matérielles
: 4.4.4 Tests d'acceptation

4.5 Mise en œuvre et plan de maintenance
: 4.5.1 Déploiement
: 4.5.2 Mise en service et validation terrain
: : 4.5.2.1 Procédure de mise en service
: 4.5.3 Plan de maintenance
: : 4.5.3.1 Maintenance préventive
: : 4.5.3.2 Maintenance corrective
: : 4.5.3.3 Surveillance de la santé du système

4.6 Résultats et interprétation
: 4.6.1 Performances des modèles
: 4.6.2 Confrontation au cahier des charges
: 4.6.3 Discussion des limites

**Conclusion**

---

## Conclusion générale

## Annexes

## Bibliographie

## Glossaire
