[English](README.md) | [Français](README.fr.md) | [简体中文](README.zh-CN.md)

<a id="cs2guard"></a>
# CS2Guard

**Détection comportementale de triche par apprentissage automatique pour Counter-Strike 2**

CS2Guard est un projet expérimental d'apprentissage automatique conçu pour détecter des comportements suspects chez les joueurs de Counter-Strike 2.

Ce projet commence par une **analyse hors ligne des fichiers de démo de CS2** afin d'extraire des données de jeu, de concevoir des caractéristiques comportementales, de construire des ensembles de données et d'entraîner des modèles de détection.

L'objectif à long terme est d'évoluer le projet en un **anti-triche côté serveur en temps réel**, capable d'analyser continuellement le comportement des joueurs pendant les matchs, sans dépendre d'une surveillance intrusive côté client.

> **État :** 🚧 En développement **Développement :** 🤖 Aidé par l'IA

<a id="quick-start"></a>
## Démarrage rapide

À partir de la racine du dépôt, installez avec Python 3.11 ou une version ultérieure et exécutez les tests (PowerShell) :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest -q
```

Pour analyser une démo, fournissez un fichier `.dem` et un modèle M5 `.joblib` fiable avec ses métadonnées adjacentes `.json`. Adaptez les chemins d'entrée à vos fichiers :

```powershell
.\.venv\Scripts\cs2guard.exe analyze '.\demo_analyzer\data\raw\train_sources\demo\test.dem' --model '.\demo_analyzer\models\supervised\random_forest_v1.joblib' --output '.\demo_analyzer\data\processed\manual_analysis'
```

Ouvrez `demo_analyzer/data/processed/manual_analysis/report.md` pour les classements et les liens PNG ; `report.json` contient toutes les fenêtres évaluées. Sans `--output`, les rapports sont envoyés vers `<demo stem>_analysis/` dans le répertoire de travail.

Une copie fraîche inclut les métadonnées du modèle, mais pas le modèle entraîné ni les démos : les fichiers `.joblib` et `.dem` sont ignorés par Git. L'installation et les tests n'ont pas besoin de ces fichiers. L'inférence nécessite les deux, mais n’entraîne jamais de modèle ; consultez [les prérequis du modèle](docs/demo_analyzer_memory.fr.md#reproducible-validation) pour la procédure séparée d'entraînement et la nécessité d'un ensemble de données.

<a id="contents"></a>
## Contenus

* [Objectifs du projet](#-project-goals)
* [Approche du projet](#-project-approach)
* [Démarrage rapide](#quick-start)
* [Carte de progression](#️-roadmap)
* [Architecture du projet](#️-project-architecture)
* [Stack technique](#️-tech-stack)
* [Stratégie de détection](#-detection-strategy)
* [Défis de recherche](#️-research-challenges)
* [Documentation / Mémoire technique](#documentation--technical-memory)

---

<a id="-ai-assisted-development"></a>
## 🤖 Développement aidé par l'IA

Des outils d'IA accompagnent le code, les tests, la documentation et la recherche. L'architecture, les expériences et les intégrations restent soumis à une vérification et validation humaines.

---

<a id="-project-goals"></a>
## 🎯 Objectifs du projet

Étudier si les comportements de jeu observables côté serveur peuvent révéler des comportements suspects sans surveillance intrusive côté client :

* Objectif : déplacement, positionnement de la lunette et suivi de cible
* Temps de réaction, vitesse angulaire et accélération
* Tir, déplacement du joueur, conscience des ennemis et motifs pré-tirés

Le développement commence par une recherche sur des démos hors ligne et l'entraînement de modèles, puis vise une détection en temps réel côté serveur.

---

<a id="-project-approach"></a>
## 🧠 Approche du projet

<a id="stage-1--offline-demo-analysis"></a>
### Phase 1 - Analyse hors ligne des démos

L'analyse hors ligne lit les matchs enregistrés, extrait des caractéristiques comportementales et évalue les modèles d'apprentissage automatique sans contraintes en temps réel.

```text
CS2 Demo
    │
    ▼
Demo Parser
    │
    ▼
Normalized Game Data
    │
    ▼
Feature Extraction
    │
    ▼
ML Detection
    │
    ▼
Suspicion Score
```

<a id="stage-2--real-time-server-side-detection"></a>
### Phase 2 - Détection en temps réel côté serveur

Le système côté serveur prévu adapte la chaîne de traitement hors ligne aux données en temps réel, en réutilisant les caractéristiques et les modèles autant que possible.

```text
CS2 Server
    │
    ▼
Live Game Events
    │
    ▼
Event Buffer
    │
    ▼
Feature Extraction
    │
    ▼
ML Inference
    │
    ▼
Risk Aggregation
    │
    ▼
Player Suspicion Score
```

<a id="documentation--technical-memory"></a>
## Documentation / Mémoire technique

* [Mémoire du projet Analyse des démos](docs/demo_analyzer_memory.fr.md) : implémentation, expériences, métriques et protocoles de validation.
* [Mémoire du projet côté serveur](docs/server_anticheat_memory.fr.md) : architecture en temps réel future et recherche.

---

<a id="️-roadmap"></a>
# 🗺️ Plan d'actions

<a id="m1--demo-parsing"></a>
## M1 - Analyse de démonstration

Construire la base pour extraire des données structurées de fichiers de démonstrations CS2.

* [x] Configurer la structure du projet Python
* [x] Intégrer un parseur de démonstrations CS2
* [x] Charger et parser les fichiers `.dem`
* [x] Extraire les métadonnées de la partie
* [x] Extraire les joueurs et les équipes
* [x] Extraire les tours
* [x] Extraire les positions des joueurs au niveau des ticks
* [x] Extraire les angles de vue (yaw / pitch)
* [x] Extraire les informations sur les armes
* [x] Extraire les tirs, les impacts et les meurtres
* [x] Définir des structures normalisées `Match`, `Player`, `Round`, `Tick` et `Event`
* [x] Ajouter des tests d'analyse de démonstrations

---

<a id="m2--aim-feature-engineering"></a>
## M2 - Ingénierie de la cible

Transformer les données brutes de jeu en comportements mesurables de visée.

* [x] Calculer la direction de la lunette
* [x] Calculer la distance angulaire entre la lunette et la cible
* [x] Calculer la vitesse angulaire
* [x] Calculer l'accélération angulaire
* [x] Détecter l'acquisition de cible
* [x] Mesurer le temps de réaction
* [x] Mesurer l'erreur de suivi
* [x] Mesurer les corrections de visée et les dépassements
* [x] Détecter des visées rapides possibles
* [x] Associer les tirs aux séquences de visée
* [x] Visualiser les trajectoires de visée
* [x] Valider les caractéristiques sur des séquences de démonstrations sélectionnées

---

<a id="m3--dataset-builder"></a>
## M3 - Constructeur de jeu de données

Créer une chaîne de traitement reproductible pour générer des jeux de données adaptés à l'apprentissage automatique à partir de plusieurs parties.

* [x] Traiter automatiquement plusieurs fichiers de démonstrations
* [x] Générer des échantillons au niveau des événements
* [x] Générer des échantillons au niveau des joueurs
* [x] Générer des fenêtres temporelles
* [x] Stocker les caractéristiques extraites
* [x] Gérer les données manquantes ou invalides
* [x] Normaliser les caractéristiques numériques
* [x] Ajouter une prise en charge des étiquettes légitimes / suspectes
* [x] Créer des divisions d'entraînement / validation / test
* [x] Éviter la fuite de données entre parties et joueurs
* [x] Générer des statistiques du jeu de données
* [x] Définir un schéma canonique pour le jeu de données CS2Guard
* [x] Prendre en charge et normaliser des jeux de données externes tels que CS2CD vers le schéma canonique

L'isolement au niveau de la partie est respecté pour l'évaluation M5. L'isolement au niveau du joueur dépend des identités disponibles ; l'anonymisation CS2CD empêche de garantir des joueurs réels distincts entre les parties.

<a id="external-datasets"></a>
### Jeux de données externes

L'adaptateur **CS2CD** mappe les étiquettes anonymisées de jeu et de niveau joueur sur des comportements frauduleux au schéma canonique. Voir [détails d'intégration et de limitations](docs/datasets/cs2cd.fr.md).

---

<a id="m4--anomaly-detection"></a>
## M4 - Détection d'anomalies

Construire le premier détecteur de comportement basé sur l'apprentissage automatique sans nécessiter de grandes quantités de données étiquetées sur la fraude.

* [x] Établir des bases statistiques pour le comportement légitime
* [x] Implémenter l'Isolation Forest
* [x] Tester le Local Outlier Factor
* [x] Expérimenter avec un SVM unifié
* [x] Comparer les approches de détection d'anomalies
* [x] Générer des scores d'anomalie pour des événements individuels
* [x] Générer des scores d'anomalie pour les joueurs
* [x] Analyser les faux positifs
* [x] Identifier les caractéristiques les plus influentes
* [x] Définir une stratégie initiale de scoring de suspicion

---

<a id="m5--supervised-detection"></a>
## M5 - Détection supervisée

Former des modèles de classification une fois que des données étiquetées suffisamment fiables deviennent disponibles.

* [x] Construire un ensemble de données étiqueté
* [x] Établir un classificateur de base
* [x] Former des modèles de Forêt aléatoire
* [x] Expérimenter avec des modèles de boosting par gradient
* [x] Ajuster les hyperparamètres des modèles
* [x] Mesurer la précision
* [x] Mesurer le rappel
* [x] Mesurer le score F1
* [x] Mesurer ROC-AUC / PR-AUC
* [x] Analyser le taux de faux positifs
* [x] Comparer les approches supervisées et de détection d'anomalies
* [x] Ajouter la versionning et la persistance des modèles

Sur les matchs historiques CS2CD réservés, la Forêt aléatoire atteint un score de **ROC-AUC 0.7779 / PR-AUC 0.6840** par joueur-match, contre **0.6323 / 0.4624** pour LOF. Voir [Résultats M5](docs/demo_analyzer_memory.fr.md#result-4) pour les métriques et les compromis de seuils.

---

<a id="m6--demo-analyzer"></a>
## M6 - Analyseur de démo

* [x] Analyser une démo complète à partir d'une seule commande
* [x] Analyser chaque joueur dans le match, en conservant les joueurs avec données insuffisantes sans score
* [x] Générer un score global de suspicion par joueur en utilisant la moyenne du score dans la fenêtre M5
* [x] Générer des indicateurs comportementaux séparés avec unités et disponibilité
* [x] Classer les joueurs par score de suspicion avec une ordonnancement déterministe en cas d'égalité
* [x] Identifier les rounds à inspecter à partir des fenêtres évaluées, en conservant les associations inconnues
* [x] Identifier les événements à inspecter sans affirmer un seuil de triche validé
* [x] Expliquer les caractéristiques mesurées, l'importance globale et les contributions de probabilités locales signées des arbres/forêts aléatoires
* [x] Visualiser les séquences d'aimage sélectionnées pour l'inspection
* [x] Générer un rapport d'analyse de match au format JSON et Markdown
* [x] Construire une interface en ligne de commande pour l'analyse des démos

<a id="m6-usage-and-validation"></a>
### Utilisation et validation de M6

Utiliser la commande dans [Démarrage rapide](#quick-start) avec un ensemble M5 entraîné. Les rapports incluent les classements des joueurs, les séquences d'inspection, les fichiers JSON/Markdown et les graphiques d'aimage.

**Validation :** M6 produit des rapports pour trois enregistrements techniques de démos et neuf démos externes jugées légitimes. L'inférence Frozen-RF sur les **64 matchs historiques CS2CD de test** reproduit le score de ROC-AUC 0.7779 / Précision moyenne 0.6840 pour les joueurs-match de M5, avec **44/64 au Hit@1** et **59/64 au Hit@3**. Ces matchs ont déjà été évalués lors de M5 ; il s'agit d'une reproduction, pas d'une validation indépendante.

Un autre ensemble de **478 matchs CS2CD avec uniquement des annotations négatives** donne **4 726 matchs de joueurs évalués dans 477 matchs**. À la seuil descriptif 0.50, **61/4 726 sont marqués (taux de flag descriptif 1,29 % ; intervalle de bootstrap à 95 % : 0,91–1,71 %)** sous ces annotations. Ce groupe ne peut pas mesurer la discrimination ou le rappel ; son absence dans les artefacts de développement n'implique pas qu'il n'a jamais été consulté.

Les scores sont des sorties non calibrées des modèles. Le seuil de 0,50 n'est pas validé opérationnellement ; le taux d'indication annoté ne permet pas d'estimer une fréquence de fausses positives en production. L'évaluation CS2CD au format JSON/Parquet ne valide ni la lecture native des démos ni la détection de nouveaux cheaters confirmés indépendamment.

Voir [Résultats et protocole CS2CD](docs/demo_analyzer_memory.fr.md#m6--cs2cd-evaluation-2026-10-15) et [Implémentation de l'Analyseur de démos](docs/demo_analyzer_memory.fr.md#m6--demo-analyzer) pour des preuves détaillées et des limites.

---

<a id="m7--temporal-modeling"></a>
## M7 - Modélisation temporelle

Étudier si les modèles basés sur des séquences améliorent la détection du comportement.

Les modèles analyseront des séquences consécutives de ticks :

```text
Tick t
Tick t+1
Tick t+2
...
Tick t+n
    │
    ▼
Temporal Model
```

* [x] Définir des séquences de ticks de longueur fixe
* [x] Construire un ensemble de données temporel
* [x] Mettre en place une base de comparaison temporelle simple
* [x] Tester des modèles de réseaux de neurones 1D
* [x] Tester des modèles LSTM / GRU
* [x] Tester des modèles basés sur des transformateurs
* [x] Comparer les modèles temporels aux modèles basés sur des caractéristiques
* [x] Mesurer la performance d'inférence
* [x] Analyser les séquences qui déclenchent des prédictions
* [x] Intégrer le meilleur modèle dans l'Analyseur de démos

**Résultat du milestone** : CS2Guard peut analyser le comportement des joueurs comme des séquences temporelles, et non seulement comme des statistiques agrégées.

### État d'implémentation de M7

Le chemin technique est implémenté : les séquences de 32 ticks deviennent six canaux cinématiques de visée, normalisés depuis le seul split d'entraînement, puis consommés par une baseline logistique aplatie, un CNN, un LSTM, un GRU et un Transformer. L'isolation entraînement/validation/test par match réutilise le test de M5. `cs2guard analyze` peut déjà charger les bundles PyTorch, et les rapports d'occlusion nulle exposent la sensibilité par tick et par canal.

Construire le dataset depuis la racine du dépôt, puis réentraîner uniquement le Transformer dans WSL2 avec ROCm :

```powershell
.\.venv\Scripts\python.exe demo_analyzer/scripts/build_temporal_dataset.py
cs2guard analyze match.dem --model demo_analyzer/models/temporal/transformer_v1.pt
```

```bash
source ~/.venvs/cs2guard-rocm/bin/activate
export HSA_ENABLE_DXG_DETECTION=1
python demo_analyzer/scripts/train_temporal.py --device cuda --models transformer --epochs 5 --m5-model demo_analyzer/models/supervised/random_forest_v1.joblib
```

L'exécution complète contient 397 480 séquences : 242 996 d'entraînement, 63 315 de validation et 91 169 de test verrouillé. Le Transformer réentraîné sur le RX 7800 XT avec ROCm obtient une PR-AUC joueur-match de validation de **0,7794** et atteint **ROC-AUC 0,8282 / PR-AUC 0,7500** sur les matchs de test M5, contre **0,7779 / 0,6840** pour M5 gelé. Les différences d'un bootstrap apparié de 1 000 tirages par match sont **+0,0503 ROC-AUC [0,0272 ; 0,0766]** et **+0,0660 PR-AUC [0,0376 ; 0,0957]**. Hit@1 reste à 44/64 et Hit@3 à 59/64. Sous WSL2 Ubuntu 24.04, PyTorch 2.9.1 et ROCm 7.2, l'inférence GPU batch 1 mesure 0,520 ms en médiane / 0,951 ms au p95 ; le débit batch 256 est d'environ 239 474 séquences/s.

Ces résultats sont internes et utilisent les matchs de test M5 déjà évalués ; ils ne constituent pas une validation indépendante. Le seuil 0,50 n'est pas validé opérationnellement et les sorties restent des scores d'inspection non calibrés, pas des probabilités ni des preuves de triche.

---

<a id="m8--awareness-analysis"></a>
## M8 - Analyse de la conscience

Étendre la détection comportementale au-delà de l'alignement de la cible pour investiguer la conscience des ennemis.

* [ ] Déterminer la visibilité des ennemis à chaque tick pertinent
* [ ] Calculer l'alignement de la cible avec les ennemis
* [ ] Détecter le suivi de la cible d'ennemis non visibles
* [ ] Analyser le comportement avant l'alignement
* [ ] Analyser le timing avant le tir
* [ ] Compter les ennemis récemment visibles
* [ ] Tenir compte des informations des équipes lorsqu'elles sont disponibles
* [ ] Tenir compte des informations sonores lorsqu'elles sont disponibles
* [ ] Construire des caractéristiques liées à la conscience
* [ ] Définir un score d'anomalie de conscience
* [ ] Évaluer les fausses positives sur des joueurs légitimes
* [ ] Intégrer les signaux de conscience dans le score global de suspicion

Interpréter la conscience dans un contexte : les sons, les équipes, les angles communs et le sens du jeu peuvent expliquer une apparente anticipation.

**Résultat du milestone** : CS2Guard combine les signaux liés à l'alignement de la cible et à la conscience des ennemis lors de l'évaluation du comportement suspect.

---

<a id="m9--real-time-detection-engine"></a>
## M9 - Engine de détection en temps réel

Adapter la chaîne de traitement de machine learning en mode hors-ligne pour les données de jeu en continu.

```text
Live Events
    │
    ▼
Sliding Window
    │
    ▼
Feature Engine
    │
    ▼
ML Model
    │
    ▼
Risk Aggregator
    │
    ▼
Suspicion Score
```

* [ ] Définir une représentation commune des données pour les démos et les données en temps réel
* [ ] Mettre en place un tampon d'événements en temps réel
* [ ] Mettre en place des fenêtres temporelles glissantes
* [ ] Convertir les caractéristiques hors-ligne en caractéristiques incrémentales
* [ ] Exécuter l'inférence ML de manière continue
* [ ] Maintenir l'état des joueurs entre les événements
* [ ] Regrouper les prédictions au fil du temps
* [ ] Mettre à jour les scores de suspicion des joueurs de manière continue
* [ ] Mesurer la latence de calcul des caractéristiques
* [ ] Mesurer la latence d'inférence du modèle
* [ ] Gérer les informations incomplètes en temps réel
* [ ] Comparer les performances des modèles en mode hors-ligne et en mode en temps réel

**Résultat de marque:** Le pipeline de détection peut fonctionner de manière incrémentale sur un flux en direct au lieu de nécessiter une démonstration complète.

---

<a id="m10--server-side-real-time-anti-cheat"></a>
## M10 - Anti-détection en temps réel côté serveur

Intégrer le moteur de détection dans un environnement côté serveur de CS2.

```text
             ┌─────────────────┐
             │   CS2 Server    │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Game Telemetry  │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Feature Engine  │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │  ML Inference   │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Risk Aggregator │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Suspicion Score │
             └─────────────────┘
```

* [ ] Étudier les données de télémétrie disponibles côté serveur de CS2
* [ ] Construire la couche d'ingestion des données côté serveur
* [ ] Convertir les événements côté serveur en format normalisé de CS2Guard
* [ ] Connecter la télémétrie en direct au moteur de traitement en flux
* [ ] Exécuter des inférences ML pendant les matchs
* [ ] Maintenir un score de suspicion en temps réel pour chaque joueur
* [ ] Mettre en place des seuils de détection configurables
* [ ] Générer des alertes côté serveur
* [ ] Enregistrer des événements suspects pour une revue ultérieure
* [ ] Stocker des preuves pour une analyse hors ligne
* [ ] Mesurer la latence totale de détection
* [ ] Mesurer l'impact sur les performances du serveur
* [ ] Tester avec plusieurs joueurs en parallèle
* [ ] Comparer les résultats en temps réel avec les résultats du Demos Analyzer après match
* [ ] Construire une interface de surveillance pour l'administrateur
* [ ] Évaluer le système complet sur des matchs contrôlés

**Résultat de marque:** CS2Guard fonctionne comme une anti-détection en temps réel, côté serveur, basée sur des modèles ML pour Counter-Strike 2.

---

<a id="️-project-architecture"></a>
# 🏗️ Architecture du projet

```text
CS2Guard/
│
├── data/
│
├── demo_analyzer/
│   ├── data/
│   ├── models/
│   │   └── supervised/
│   ├── scripts/
│   ├── src/
│   │   └── cs2guard_demo/
│   │       ├── dataset/
│   │       │   └── adapters/
│   │       ├── detection/
│   │       ├── features/
│   │       ├── models/
│   │       ├── parser/
│   │       ├── supervised/
│   │       ├── utils/
│   │       └── visualization/
│   └── tests/
```

Les adaptateurs de démonstration et les futurs serveurs ciblent une représentation partagée de l'état de jeu et un pipeline d'analyse commun :

```text
Demo Parser ─────┐
                 │
                 ▼
              Game State
                 │
                 ▼
            Feature Engine
                 │
                 ▼
             ML Detector
                 │
                 ▼
           Suspicion Score
                 ▲
                 │
Server Stream ───┘
```

---

<a id="️-tech-stack"></a>
# 🛠️ Stack technique

<a id="currently-used"></a>
## Actuellement utilisé

<a id="core"></a>
### Core

* Python
* NumPy
* pandas
* demoparser2

<a id="machine-learning"></a>
### Machine Learning

* scikit-learn
* joblib (persistance des modèles)

L'approche de boosting graduel utilise `HistGradientBoostingClassifier` de scikit-learn.

<a id="data-analysis--visualization"></a>
### Analyse et visualisation des données

* Matplotlib
* pytest (tests de développement)

<a id="planned--under-investigation"></a>
## À venir / En étude

* PyTorch et modèles temporels (M7)
* Ingérence en temps réel et traitement en flux de télémétrie (M9–M10)
* XGBoost / LightGBM et Jupyter restent des candidats de la pile initiale ; ils ne sont pas des dépendances intégrées.

---

<a id="-detection-strategy"></a>
# 📊 Stratégie de détection

M6 calcule les scores de la fenêtre M5 par joueur. La stratégie à long terme combine plusieurs signaux comportementaux au fil du temps :

```text
Raw Gameplay
     │
     ▼
Behavioral Features
     │
     ▼
Event Anomaly Scores
     │
     ▼
Temporal Aggregation
     │
     ▼
Behavioral Scores
     │
     ▼
Global Suspicion Score
```

Les scores comportementaux supplémentaires et leur combinaison restent des recherches futures.

---

<a id="️-research-challenges"></a>
# ⚠️ Défis de recherche

* **Faux positifs et compétence :** des mécanismes inhabituels peuvent être légitimes ; comparer les joueurs selon leur niveau de compétence et agréger les preuves au fil du temps.
* **Qualité du jeu de données :** il est difficile d'obtenir des étiquettes fiables et des populations d'évaluation indépendantes.
* **Contexte de jeu :** les sons, les informations sur les camarades, la visibilité précédente et les temps attendus peuvent expliquer des actions suspectes.
* **Passage de l'off-line à l'online :** l'inférence en temps réel doit gérer des informations incomplètes, l'état des joueurs et les joueurs simultanés avec une latence faible et une surcharge minimale sur le serveur.

```text
Anomaly ≠ Cheater
```

---

<a id="-research-questions"></a>
# 🔬 Questions de recherche

1. Quels éléments liés à l'objectif et à la conscience permettent de distinguer un comportement suspect d'une compétence ou d'un contexte légitime ?
2. Comment les modèles d'anomalie, supervisés et temporels se comparent-ils, et quels éléments expliquent leurs prédictions ?
3. Comment peut-on combiner plusieurs signaux faibles tout en contrôlant les fausses positives ?
4. Quelle précision reste-t-elle lors du passage aux données en temps réel, et peut-on satisfaire les contraintes de latence des serveurs ?

---

<a id="-long-term-goal"></a>
# 🚀 Objectif à long terme

Étudier si les données de jeu peuvent soutenir une solution expérimentale de détection en temps réel, côté serveur, en progressant du niveau M1 au niveau M10.

---

<a id="-disclaimer"></a>
# 📌 Avertissement

CS2Guard est un projet de recherche et d'enseignement expérimental.

Un score élevé d'anomalie ou de suspicion ne constitue pas preuve que le joueur triche. Des joueurs légitimes peuvent présenter un comportement inhabituel, et tout système de détection anti-triche pratique doit tenir compte de l'incertitude et des fausses positives.

CS2-Guard n'est pas affilié ni appuyé par Valve Corporation.
