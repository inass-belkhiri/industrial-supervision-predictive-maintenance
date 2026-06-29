# Guide de Validation des Modèles ML

Ce document explique comment mesurer la performance et la précision de vos modèles, y compris l'utilisation des données de simulation de l'adoucisseur.

## 1. Modèle Grey-Box (Soft Sensing - Épaisseur Calcaire)
*Ce modèle est déterministe (basé sur la physique), il n'a pas de "training".*

### Méthode de validation : Comparaison Théorique
Pour valider que votre modèle estime correctement l'épaisseur (`epaisseur_mm`), vous devez le comparer à des cas théoriques.

**Étapes :**
1.  **Injection de données simulées** : Créez un script Python qui envoie de fausses données à InfluxDB simulant une chute de température progressive (ex: -0.5°C par jour sur un moule).
2.  **Mesure** : Observez si la valeur `epaisseur_mm` calculée par le backend augmente linéairement comme prévu.
3.  **Intégration Adoucisseur (Simulation)** :
    *   Votre prototype adoucisseur (Simulink/Thomas Model) génère des courbes de percée (concentration $C_{out}$ en fonction du temps).
    *   Utilisez ces données $C_{out}(t)$ pour calculer la quantité de calcaire théoriquement déposée.
    *   **Formule de comparaison** :
        $$ \text{Erreur (\%)} = \frac{|e_{\text{GreyBox}} - e_{\text{Simulink}}|}{e_{\text{Simulink}}} \times 100 $$
    *   Si l'erreur est faible (< 10%), votre modèle Grey-Box est validé par la simulation.

## 2. Isolation Forest (Détection d'Anomalies)
*Modèle non supervisé : il apprend ce qui est "Normal".*

### Métrique clé : False Positive Rate (FPR)
Puisque vous n'avez pas d'étiquettes "Anomalie" réelles au début, la métrique principale est le taux de fausses alertes.

**Protocole de test :**
1.  Entraînez le modèle uniquement sur des données **normales** (saines).
2.  Testez-le sur un jeu de données contenant 90% de normal et 10% d'anomalies (que vous aurez injectées artificiellement, ex: chute brutale de T).
3.  **Résultat attendu** : Le modèle doit flagger les anomalies injectées et ignorer le bruit normal.

## 3. Random Forest (Classification des Causes)
*Modèle supervisé : il prédit la cause (ex: Calcaire, Pompe HS).*

### Métriques clés : Matrice de Confusion & F1-Score
Pour mesurer la précision, vous devez entraîner le modèle sur des données **étiquetées** (historique ou simulées).

**Procédure :**
1.  **Génération de dataset synthétique** :
    *   Générez 1000 lignes de données où vous simulez des pannes (ex: `Calcaire` = débit bas + delta_T haut).
2.  **Split** : 80% Train, 20% Test.
3.  **Matrice de Confusion** : Regardez les diagonales (bonnes prédictions) vs les hors-diagonales (erreurs).
    *   *Exemple d'erreur à éviter* : Confondre "Niveau Bas" et "Fuite".
4.  **F1-Score** : C'est la moyenne harmonique de la Précision et du Rappel. Visez > 0.85.

## 4. Ridge Regression (Maintenance Prédictive)
*Modèle supervisé : il prédit le temps restant avant maintenance (Jours).*

### Métriques clés : RMSE & $R^2$
1.  **RMSE (Root Mean Square Error)** :
    *   Indique de combien de jours votre prédiction se trompe en moyenne.
    *   *Objectif* : RMSE < 3 jours.
2.  **$R^2$ Score** :
    *   Indique la qualité de l'ajustement de la courbe polynomiale.
    *   *Objectif* : $R^2 > 0.80$.

---

## Résumé pour le Rapport PFE

Dans votre rapport, présentez un tableau de synthèse :

| Modèle | Type | Métrique | Objectif | Méthode de Validation |
|:---|:---|:---|:---|:---|
| **Grey-Box** | Physique (Soft Sensing) | Erreur relative | < 10% | Comparaison avec Simulink (Adoucisseur) |
| **Isolation Forest** | Non-supervisé | Faux Positifs | < 5% | Injection de bruit vs anomalies |
| **Random Forest** | Supervisé | F1-Score | > 85% | Matrice de confusion (données synthétiques) |
| **Ridge Reg.** | Supervisé | RMSE | < 3 jours | Validation croisée (Cross-Validation) |
