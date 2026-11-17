[English](demo_analyzer_memory.md) | [Français](demo_analyzer_memory.fr.md) | [简体中文](demo_analyzer_memory.zh-CN.md)

<a id="cs2guard--demo-analyzer-project-memory"></a>
# CS2Guard - Analyseur de démo Projet Mémoire

<a id="1-purpose"></a>
## 1. Objectif

Ce document suit le développement du **Analyseur de démo CS2Guard**.

Son objectif n'est pas de remplacer le principal `README.md`, mais de fournir un enregistrement technique plus détaillé du projet :

* ce qui a été implémenté ;
* pourquoi chaque fonctionnalité a été introduite ;
* comment chaque fonctionnalité fonctionne ;
* quels éléments du codebase sont impliqués ;
* comment l'implémentation a été testée ;
* quels choix techniques ont été faits au fil du chemin.

L'Analyseur de démo correspond à la phase de développement **v0.x** de CS2Guard.

Son objectif à long terme est d'analyser les fichiers de démo de Counter-Strike 2 et d'extrait des caractéristiques de jeu significatives qui peuvent ensuite être utilisées pour identifier des comportements suspects des joueurs.

---

<a id="m1--demo-parsing-foundation"></a>
# M1 - Fondation de l'analyse de démo

<a id="objective"></a>
## Objectif

L'objectif de M1 était de construire la base de données d'extraction de CS2Guard.

Avant d'essayer de détecter des comportements suspects, le projet doit d'abord transformer un fichier brut de Counter-Strike 2 `.dem` en données structurées en Python pouvant être traitées par les étapes ultérieures d'analyse.

En forme simplifiée :

```text
CS2 Demo (.dem)
      ↓
 Demo Parser
      ↓
Structured match data
      ↓
Players / Rounds / Ticks / Events
```

<a id="main-features"></a>
## Fonctionnalités principales

<a id="demo-parsing"></a>
### Analyse de démo

CS2Guard peut charger et analyser un fichier de démo de Counter-Strike 2.

Le parser permet d'accéder aux informations de match et aux données de jeu enregistrées pendant le match.

<a id="match-metadata"></a>
### Métadonnées du match

Des métadonnées de base peuvent être extraites à partir du démo, telles que des informations décrivant le match et le démo lui-même.

Cela fournit des informations contextuelles sur les données analysées.

<a id="players-and-teams"></a>
### Joueurs et équipes

L'information sur les joueurs est extraites et normalisées afin que les joueurs puissent être identifiés de manière cohérente tout au long de l'analyse.

Cela inclut des informations telles que :

* noms des joueurs ;
* identifiants Steam ;
* informations sur les équipes.

<a id="round-data"></a>
### Données des rounds

Le match peut être divisé en rounds afin que les événements et les comportements des joueurs puissent être analysés dans le contexte correct de jeu.

<a id="tick-level-player-data"></a>
### Données des joueurs au niveau du tick

L'état des joueurs peut être extrait au fil du temps.

Cela fournit la base pour des caractéristiques temporelles telles que l'analyse du mouvement et de l'alignement.

L'information importante inclut :

* position du joueur ;
* angles de vue ;
* arme active ;
* état du joueur à un moment donné dans le démo.

<a id="gameplay-events"></a>
### Événements de jeu

Plusieurs événements importants de jeu sont extraites.

<a id="shots"></a>
#### Tirs

Représente un tir effectué par un joueur.

L'information utile inclut le joueur, l'arme et le moment du tir.

<a id="hits"></a>
#### Coup

Représente un dommage infligé à un autre joueur.

Les événements de coup fournissent des informations telles que :

* attaquant ;
* victime ;
* arme ;
* dommage ;
* groupe de coup ;
* moment.

<a id="kills"></a>
#### Meurtres

Représente l'élimination d'un joueur.

Les événements de mort contiennent des informations contextuelles supplémentaires telles que :

* l'agresseur et la victime ;
* l'arme ;
* l'état de tete-bas ;
* la distance ;
* la pénétration ;
* l'interaction avec la fumée ;
* l'état sans lunette.

<a id="data-normalization"></a>
## Normalisation des données

La sortie brut de la fonction de parsing est convertie en structures internes CS2Guard.

L'objectif est de prévenir que le reste du projet ne dépende pas directement de la représentation retournée par la bibliothèque de parsing des démos.

Conceptuellement :

```text
Raw demo data
      ↓
DemoParser
      ↓
Normalization
      ↓
CS2Guard models
```

Cette séparation rendra plus facile l'entretien et les tests des composants d'analyse ultérieurs.

<a id="testing"></a>
## Tests

La fondation de parsing est couverte par des tests automatisés.

Une importante décision de conception a été d'éviter de faire dépendre le principal ensemble de tests d'un fichier local `test.dem` qui ne serait pas nécessairement disponible dans le référentiel ou dans l'environnement CI.

Des fichiers de démo réels peuvent encore être utilisés manuellement pour des tests d'intégration et de visualisation.

<a id="result"></a>
## Résultat

À la fin de M1, CS2Guard dispose d'une base fonctionnelle capable de transformer les données de démo CS2 en informations structurées adaptées à l'extraction de caractéristiques.

Le projet peut donc passer de :

> "Peut CS2Guard lire une partie ?"

à :

> "Quelles caractéristiques comportementales CS2Guard peut-il extraire de cette partie ?"

---

<a id="m2--aim-feature-extraction"></a>
# M2 - Extraction des caractéristiques d'objectif

<a id="objective-1"></a>
## Objectif

L'objectif de M2 était de transformer les informations brutes d'angle extraites lors de M1 en caractéristiques réutilisables **d'ajustement de l'objectif**.

Les valeurs de pitch et de yaw décrivent où un joueur regarde, mais elles ne sont pas suffisantes directement pour une analyse comportementale. M2 introduit donc une couche d'extraction de caractéristiques qui décrit l'évolution de l'objectif du joueur au fil du temps.

Conceptuellement :

```text
Tick-level view angles
        ↓
Angle normalization / deltas
        ↓
Angular velocity
        ↓
Angular acceleration
        ↓
Rolling temporal features
        ↓
Aim behavior analysis
```

Ces caractéristiques forment la première famille de caractéristiques comportementales du Analyseur de démo.

<a id="main-features-1"></a>
## Caractéristiques principales

<a id="angle-processing"></a>
### Traitement de l'angle

Les calculs d'objectif sont basés sur les valeurs de pitch et de yaw extraites à partir de ticks consécutifs de démo.

Le yaw nécessite un traitement spécial car les angles se ferment à la frontière `-180° / +180°`. Une transition comme `179° → -179°` doit donc être interprétée comme une petite rotation plutôt qu'une rotation de presque 360°.

Des différences angulaires normalisées garantissent que les calculs de vitesse et d'accélération représentent effectivement le mouvement d'objectif.

<a id="angular-velocity"></a>
### Vitesse angulaire

La vitesse angulaire mesure la rapidité avec laquelle la direction de vue du joueur change entre les échantillons.

La vitesse est calculée de manière indépendante pour le pitch et le yaw, permettant ainsi de distinguer les mouvements horizontaux et verticaux d'objectif.

Conceptuellement :

```text
angular velocity = angular displacement / elapsed time
```

Cela peut décrire un suivi lent, des corrections normales d'objectif, des rotations rapides et des mouvements de type 'flick'.

Une vitesse angulaire élevée seule n'est pas considérée comme une preuve de triche.

<a id="angular-acceleration"></a>
### Accélération angulaire

L'accélération angulaire mesure la rapidité avec laquelle la vitesse angulaire change au fil du temps.

Conceptuellement :

```text
angular acceleration = change in angular velocity / elapsed time
```

Cela permet de caractériser des changements brusques dans le mouvement de la cible, y compris le début ou la fin de mouvements rapides de la souris.

Des valeurs d'accélération élevées peuvent survenir naturellement en raison de mouvements rapides, de changements de direction rapides, d'échantillonnage discret lors de démonstrations et d'intervalles de temps courts. L'accélération est donc une caractéristique comportementale qui doit être interprétée ultérieurement avec un contexte supplémentaire plutôt que considérée comme un indicateur isolé de fraude.

<a id="rolling--temporal-aim-features"></a>
### Fonctions d'orientation temporelles / enroulées

Les mesures individuelles entre ticks peuvent être bruitées et fournir une description très locale du comportement du joueur.

L'implémentation actuelle calcule des statistiques sur des fenêtres temporelles sélectionnées, et non sur une série glissante de statistiques. Ces caractéristiques temporelles synthétisent des séquences courtes d'orientation et fournissent une information plus stable pour une analyse ultérieure.

Les calculs temporels sont conçus autour des données de ticks de démonstration ; leur interprétation doit rester consciente du comportement de enregistrement de ticks et de sous-ticks de CS2.

<a id="shot-centered-aim-sequences"></a>
## Séquences d'orientation centrées sur le tir

Pour une validation manuelle, M2 peut examiner une séquence d'orientation autour d'un tir sélectionné.

Le workflow de visualisation expose des informations contextuelles telles que :

* joueur ;
* cible ;
* arme ;
* tick du tir ;
* tick de l'impact si applicable.

Une fenêtre autour du tir peut alors être inspectée afin de comprendre comment le joueur a orienté sa cible immédiatement avant et après le tir.

<a id="aim-visualization"></a>
## Visualisation de l'orientation

Un script de visualisation dédié est utilisé pour l'inspection manuelle des fonctionnalités M2.

Les responsabilités sont séparées entre :

```text
scripts/parse_demo.py
    → M1 parsing / structured demo inspection

scripts/visualize_aim.py
    → M2 aim feature inspection / visualization
```

Les graphiques générés permettent de visualiser l'évolution des valeurs liées à l'orientation autour d'un tir sélectionné. Ils servent de outil de développement et de validation, et non pas comme mécanisme final de détection de fraude.

<a id="weapon-context"></a>
## Contexte de l'arme

La séquence de tir sélectionnée expose également l'arme utilisée par le joueur.

Les noms d'armes proviennent des données de démonstration. Par exemple, `elite` correspond aux Dual Berettas.

Le contexte de l'arme pourrait devenir utile ultérieurement car le comportement légitime de l'orientation peut varier selon l'arme et la situation de tir. À M2, il reste une information contextuelle plutôt qu'un critère de suspicion.

<a id="implementation-structure"></a>
## Structure de l'implémentation

L'extraction des caractéristiques d'orientation est maintenue séparée de l'ingestion des démonstrations.

Conceptuellement :

```text
src/cs2guard_demo/parser/
        ↓
normalized tick/event data
        ↓
src/cs2guard_demo/features/aim.py
        ↓
aim features
        ↓
scripts/visualize_aim.py
```

Cela permet à l'extraction des caractéristiques d'être réutilisée ultérieurement par des composants de détection ou d'apprentissage automatique, sans dépendre du code de visualisation.

<a id="testing-1"></a>
## Tests

M2 est couvert par des tests automatisés pour la logique d'extraction des caractéristiques d'orientation.

Ces tests valident les calculs des caractéristiques de manière indépendante d'un fichier local `.dem`, ce qui rend le jeu de tests répétable et adapté à l'infrastructure de CI.

Un démonstration réel peut encore être utilisé manuellement via `visualize_aim.py` pour la validation d'intégration et visuelle.

À la fin de M2, tous les tests automatisés sont passés.

<a id="technical-decisions"></a>
## Decisions techniques

Les décisions importantes prises pendant M2 incluent :

* l'extraction des caractéristiques d'orientation à partir de données de ticks normalisées plutôt que directement à partir de la sortie brute du parser ;
* le traitement de l'angle de rotation avant les calculs de mouvement ;
* garder les mouvements de pitch et de yaw distincts ;
* traiter la vitesse et l'accélération comme des signaux descriptifs plutôt que comme des indicateurs directs de triche ;
* utiliser des statistiques glissantes pour fournir un contexte temporel ;
* utiliser des séquences centrées sur le tir pour une inspection manuelle pratique ;
* garder les tests automatisés indépendants d'un fichier démo commis ;
* garder `parse_demo.py` centré sur M1 et `visualize_aim.py` centré sur M2.

<a id="result-1"></a>
## Résultat

M2 est complet et validé.

CS2Guard peut désormais transformer les données brutes d'angle de vue en caractéristiques structurées de comportement d'orientation et inspecter ces caractéristiques autour d'événements de jeu tels que les tirs et les coups.

L'Analyseur de démo a progressé de :

> "Où regarde le joueur ?"

à :

> "Comment le comportement d'orientation du joueur évolue-t-il au fil du temps, en particulier autour des actions de combat ?"

Ces caractéristiques d'orientation fournissent les premiers signaux comportementaux qui peuvent ensuite être combinés avec d'autres familles de caractéristiques et des logiques de détection pour identifier des comportements suspectés.

---

<a id="m3--dataset-builder"></a>
# M3 - Constructeur de jeu de données

<a id="objective-2"></a>
## Objectif

L'objectif de M3 était de transformer les données de match structurées et les caractéristiques comportementales produites par les étapes précédentes en jeux de données reproductibles adaptés aux workflows de machine learning.

Au lieu d'analyser un seul démo manuellement, CS2Guard peut désormais traiter des collections de matchs et générer des échantillons standardisés qui peuvent être utilisés ultérieurement pour le traitement, la validation et l'évaluation.

Conceptuellement :

```text
Multiple match sources
        ↓
Source ingestion / adapters
        ↓
Canonical CS2Guard representation
        ↓
Feature extraction
        ↓
Dataset samples
        ↓
Train / validation / test splits
```

<a id="main-features-2"></a>
## Fonctionnalités principales

<a id="multi-demo-processing"></a>
### Traitement multi-démonstration

Le constructeur de jeu peut traiter automatiquement plusieurs fichiers de démonstration au lieu de nécessiter l'analyse individuelle de chaque correspondance.

Cela permet de construire des ensembles de données plus grands à partir de collections de parties CS2 tout en maintenant une chaîne de traitement reproductible.

<a id="event-level-samples"></a>
### Échantillons au niveau des événements

Les événements de jeu peuvent être convertis en échantillons individuels de jeu.

Ces échantillons préserve le contexte des événements tout en exposant des caractéristiques sous une forme adaptée aux étapes ultérieures d'apprentissage automatique.

<a id="player-level-samples"></a>
### Échantillons au niveau du joueur

CS2Guard peut également regrouper des informations au niveau du joueur.

Cela fournit une représentation du comportement du joueur sur une partie plus large plutôt que seulement autour d'événements isolés.

<a id="temporal-windows"></a>
### Fenêtres temporelles

Les fenêtres temporelles regroupent des observations consécutives afin de représenter le comportement à court terme sous forme de séquences.

Ceci est important pour des caractéristiques telles que le mouvement de visée, où l'évolution d'un signal au fil du temps peut être plus informatif qu'une mesure unique.

<a id="feature-storage"></a>
### Stockage des caractéristiques

Les échantillons générés et leurs caracté-ristiques associées peuvent être stockés dans des fichiers de jeu réutilisables.

L'objectif est de séparer le traitement coûteux des démonstrations de l'expérimentation ultérieure en apprentissage automatique afin que le même jeu de données généré puisse être réutilisé sans repasser chaque partie source.

La construction complète du jeu écrit chaque partie traitée directement dans les sorties CSV au lieu de conserver toutes les parties précédemment traitées en mémoire. Cela réduit l'utilisation maximale de mémoire lors de grands builds.

Un fichier de point d'arrêt léger est mis à jour après chaque match terminé. Si la compilation est interrompue, elle peut être reprise avec `--resume` sans reconstruire les matches déjà terminés. Si une interruption survient pendant l'écriture du fichier, les fichiers de sortie sont remis en marche à leurs tailles précédentes avant de réexécuter le match interrompu.

<a id="missing-and-invalid-data"></a>
### Données manquantes ou invalides

La pipeline de données gère les valeurs manquantes ou invalides afin que les échantillons mal formés ne corrompent pas silencieusement le jeu de données généré.

Ceci est particulièrement important lors du traitement de grandes collections de matches provenant de différentes sources.

<a id="numeric-normalization"></a>
### Normalisation numérique

Les caractéristiques numériques peuvent être normalisées pour obtenir des représentations cohérentes adaptées au traitement par apprentissage automatique.

La normalisation est effectuée au niveau du jeu de données, et non pas en modifiant les informations de jeu originales extraites à partir de la source.

<a id="labels"></a>
### Étiquettes

Les échantillons du jeu de données supportent des étiquettes représentant la classe attendue du comportement associé, y compris des données légitimes et suspectes.

La couche d'étiquetage est maintenue séparée de l'extraction des caractéristiques afin que les caractéristiques comportementales ne codent pas directement le résultat attendu.

<a id="dataset-splits"></a>
### Divisions du jeu de données

Le constructeur génère des divisions d'entraînement, de validation et de test pour des expériences ultérieures d'apprentissage automatique.

Une exigence centrale est de prévenir la fuite d'information entre ces divisions.

Les matchs et les identités des joueurs sont donc pris en compte lors de l'affectation des échantillons afin que des observations fortement liées ne soient pas réparties entre les sous-ensembles d'entraînement et d'évaluation lorsque les données sources le permettent.

<a id="dataset-statistics"></a>
### Statistiques du jeu de données

Le jeu de données généré peut exposer des statistiques décrivant son contenu.

Ces statistiques constituent une étape de validation de base pour vérifier le nombre et la répartition des échantillons générés avant leur utilisation dans l'entraînement des modèles.

<a id="external-dataset-support"></a>
## Support des jeux de données externes

M3 introduit un support pour des jeux de données externes via des adaptateurs spécifiques à la source et une représentation canonique du jeu de données CS2Guard.

La première source externe intégrée est CS2CD. Un adaptateur dédié a été mis en place et ses tests automatisés sont passés.

Les décisions détaillées concernant l'intégration de CS2CD, y compris le traitement des identités anonymes et les limites de fuite de données, sont documentées dans [`datasets/cs2cd.md`](datasets/cs2cd.fr.md).

<a id="cs2cd-identity-and-leakage-constraints"></a>
## Contraintes d'identité et de fuite de données de CS2CD

CS2CD anonymise les identités des joueurs, ce qui empêche CS2Guard de lier directement ses enregistrements aux identités Steam originales des fichiers de démo.

Cela signifie que la prévention de la fuite d'identité au niveau du joueur ne peut pas s'appuyer sur un identifiant réel du monde réel persistant entre des matchs CS2CD non liés.

La pipeline de données doit donc préserver l'information de regroupement la plus forte disponible à partir de la source et documenter les limites de garanties de fuite de données imposées par l'anonymisation de la source.

Cette distinction est importante car la prévention de la fuite de données est une propriété à la fois de la stratégie de division et des informations d'identité fournies par le jeu de données source.

<a id="coach--non-player-edge-case"></a>
## Cas particulier du coach / du joueur non présent

Lors de la validation M3, un cas limite a été observé dans les données de démonstration impliquant des personnes présentes uniquement en tant que coaches.

Un coach peut apparaître dans les données extraites liées aux joueurs et peut même produire des enregistrements inattendus ressemblant à une partie, comme une mort pendant la période de freeze.

Cela signifie que la présence dans la sortie du parser ne suffit pas à garantir qu'un entité doit être traitée comme un joueur normal participant.

Ce cas doit donc rester pris en compte lors de la construction des ensembles de données au niveau du joueur afin d'éviter que des participants non joueurs ne contaminent silencieusement les échantillons générés.

<a id="implementation-structure-1"></a>
## Structure de l'implémentation

M3 étend le projet de l'inspection d'une seule démonstration de fonctionnalité vers une pipeline de construction de données réutilisable.

Conceptuellement :

```text
Demo files / external datasets
        ↓
src/cs2guard_demo/dataset/adapters/
        ↓
canonical CS2Guard data
        ↓
src/cs2guard_demo/features/
        ↓
dataset builder
        ↓
generated ML-ready datasets
```

La logique spécifique à la source reste isolée de la représentation canonique du jeu de données. Cela permet d'intégrer des données externes via leurs propres adaptateurs sans forcer le reste du pipeline à dépendre de leur schéma d'origine.

<a id="testing-2"></a>
## Tests

M3 est couvert par des tests automatisés pour le pipeline de construction de données et l'adaptateur CS2CD.

L'ensemble des tests valide la logique du jeu de données indépendamment des grandes collections locales de démonstrations, tandis que des constructions multi-démonstrations réelles sont utilisées pour la validation d'intégration.

À la fin de M3, le jeu de tests automatisés est passé, y compris les tests dédiés à l'adaptateur CS2CD.

Une construction complète d'un jeu de données a également été réalisée avec succès à l'aide à la fois de fichiers de démonstrations natifs et de données CS2CD.

Le jeu de données canonique final contient :

* 2 sources de données (`demo` et `cs2cd`);
* 320 matchs;
* 3 133 joueurs;
* 523 083 événements;
* 229 149 465 ticks;
* 405 663 fenêtres temporelles;
* 405 663 échantillons de caractéristiques d'objectif.

Cette construction à grande échelle a également validé le système de stockage incrémental et de points d'arrêt dans des volumes réalistes de jeu de données.

<a id="technical-decisions-1"></a>
## Decisions techniques

Les décisions importantes prises lors de M3 incluent :

* le traitement de plusieurs matchs à travers un pipeline de construction de données reproductible;
* le support des représentations au niveau des événements, des joueurs et temporels;
* la séparation de l'ingestion de la source de la représentation canonique du jeu de données CS2Guard;
* l'introduction d'adaptateurs spécifiques à la source pour les jeux de données externes;
* l'utilisation de CS2CD comme première intégration de jeu de données externe;
* le maintien de l'extraction de caractéristiques indépendante des étiquettes du jeu de données;
* la génération de divisions d'entraînement, de validation et de test avec la prévention de la fuite comme exigence fondamentale;
* le regroupement d'échantillons en utilisant les informations de match et de joueur lorsque la source fournit des informations d'identité suffisantes;
* la documentation explicite de garanties plus faibles au niveau des joueurs lorsqu'un jeu de données externe anonymise les identités;
* le traitement des échantillons manquants ou invalides avant la génération du jeu de données;
* l'exposition des statistiques du jeu de données pour la validation;
* l'écriture des matchs complets de manière incrémentale dans les fichiers du jeu de données final afin d'éviter de stocker toute la donnée source en mémoire;
* l'utilisation d'un point d'arrêt léger par match et du mécanisme `--resume` pour gérer des constructions longues et interrompues.
* annuler partiellement les fichiers de sortie non complétés avant de reprendre une partie interrompue ;
* tenir compte du cas particulier coach/jeu non joué lorsqu'on détermine les échantillons valides de joueurs.

<a id="result-2"></a>
## Résultat

M3 est terminé et validé.

CS2Guard peut maintenant transformer les données de plusieurs parties en ensembles structurés et réutilisables, adaptés aux étapes futures d'apprentissage automatique.

L'Analyseur de Démo a progressé de :

> "Quels sont les traits comportementaux qu'on peut extraire d'une partie ?"

à :

> "Comment peut-on transformer ces traits en un ensemble réutilisable sans introduire de fuites de données évitables ?"

Le projet possède désormais la base de données requise pour les étapes ultérieures d'apprentissage de modèles et de détection de comportements suspects.

---

<a id="m4--anomaly-detection"></a>
# M4 - Détection d'anomalies

<a id="objective-3"></a>
## Objectif

L'objectif de M4 était de construire le premier détecteur d'apprentissage automatique capable d'identifier des comportements inhabituels d'attaque sans que le détecteur lui-même soit formé sur des étiquettes de fraude.

M4 utilise les caractéristiques d'attaque générées par les étapes précédentes et évalue plusieurs approches de détection d'anomalies non supervisées.

Conceptuellement :

```text
Aim feature samples
        ↓
Feature preprocessing
        ↓
Unsupervised anomaly detection
        ↓
Window / shot anomaly scores
        ↓
Player-level aggregation
        ↓
Initial suspicion score
```

Les étiquettes provenant de CS2CD sont utilisées uniquement pour l'évaluation et la calibration après la génération des scores d'anomalie. Elles ne sont pas fournies comme caractéristiques d'entrée pour les modèles non supervisés.

<a id="input-features"></a>
## Caractéristiques d'entrée

M4 utilise six caractéristiques numériques d'attaque :

* `mean_angular_speed`;
* `max_angular_speed`;
* `std_angular_speed`;
* `mean_angular_acceleration`;
* `max_angular_acceleration`;
* `std_angular_acceleration`.

Les identifiants, les métadonnées de source et les étiquettes sont exclus des entrées du modèle.

Avant les expérimentations de modèle, le jeu complet des caractéristiques a été validé :

* 405 663 échantillons de caractéristiques d'attaque ;
* aucune valeur manquante dans les six caracté-ristiques du modèle ;
* aucune valeur infinie dans les six caractéristiques du modèle.

Les distributions des caractéristiques sont fortement asymétriques et contiennent des valeurs extrêmes légitimes, donc une vitesse ou une accélération élevée seule n'est pas considérée comme preuve de fraude.

<a id="legitimate-behavior-baseline"></a>
## Base de comportement légitime

Une base statistique a été établie à partir des 282 022 fenêtres étiquetées `legitimate`.

Cette base légitime inclut la moyenne, l'écart-type, la médiane et les percentiles supérieurs de chaque caractéristique d'attaque.

Les percentiles 99 sont approximativement :

* `mean_angular_speed`: 175.17;
* `max_angular_speed`: 692.76;
* `std_angular_speed`: 191.97;
* `mean_angular_acceleration`: 5,219.80;
* `max_angular_acceleration`: 25,087.75;
* `std_angular_acceleration`: 6,250.98.

Les échantillons légitimes peuvent encore dépasser ces valeurs de manière importante. La base est donc utilisée comme contexte statistique plutôt qu'au titre d'un ensemble de seuils de fraude.

<a id="isolation-forest"></a>
## Forêt d'Isolation

La Forêt d'Isolation a été mise en œuvre comme première base de détection d'anomalies.

Les six caractéristiques sont standardisées avant l'inférence, et le modèle produit :

* un score d'anomalie au niveau de la fenêtre ;
* une prédiction binaire d'anomalie ;
* des scores regroupés au niveau du joueur.

Sur l'ensemble complet des données :

* fenêtres : 405 663 ;
* observations joueur-partie : 3 138 ;
* fenêtres anormales : 41 133.

Au niveau du joueur, les joueurs suspects ont reçu des scores moyens d'anomalie supérieurs à ceux des joueurs légitimes :

```text
legitimate mean   = -0.082159
suspicious mean   = -0.064996
```

Cela indique que les caractéristiques d'attaque contiennent un signal d'anomalie mesurable, bien que la séparation reste limitée.

<a id="local-outlier-factor"></a>
## Facteur local d'anomalie

Le Local Outlier Factor a été évalué à l'aide de la même représentation standardisée des caractéristiques.

Sur l'ensemble du jeu de données :

* fenêtres : 405 663 ;
* observations de correspondance joueur : 3 138 ;
* fenêtres anormales : 1 216.

Le LOF a produit des scores bruts très asymétriques. La plupart des fenêtres restent proches d'un score LOF d'environ 1, tandis qu'un petit nombre d'échantillons isolés reçoivent des scores extrêmement élevés.

Au niveau du joueur :

```text
mean anomaly score

legitimate mean   = 266.428996
suspicious mean   = 494.548139

median

legitimate        = 1.038084
suspicious        = 1.049517
```

Le rapport de fenêtres anormales était également plus élevé pour les joueurs suspects :

```text
legitimate mean ratio   = 0.002257
suspicious mean ratio   = 0.007781
```

Ces résultats montrent que les joueurs suspects présentent un comportement d'aimage localement inhabituel, tout en démontrant que les valeurs brutes du LOF sont sensibles à un petit nombre d'échantillons extrêmes.

<a id="one-class-svm"></a>
## SVM unilatérale

Une SVM unilatérale avec noyau RBF a également été évaluée.

Pour garder l'expérience computationnellement pratique, le modèle est entraîné sur un échantillon déterministe de au plus 20 000 fenêtres de caractéristiques, puis utilisé pour évaluer l'ensemble du jeu de données.

La base de comparaison utilise :

```text
kernel = rbf
gamma = scale
nu = 0.05
```

Sur l'ensemble du jeu de données :

* fenêtres : 405 663 ;
* observations de correspondance joueur : 3 138 ;
* fenêtres anormales : 15 295.

Les scores d'anomalie moyens et médians au niveau du joueur étaient plus élevés pour les joueurs suspects :

```text
                 mean       median
legitimate      -14.34      -16.01
suspicious       -7.97      -13.87
```

<a id="model-comparison"></a>
## Comparaison des modèles

Les trois approches ont été comparées en utilisant l'AUC ROC au niveau du joueur.

Les agrégations de joueurs évaluées étaient :

* `mean_anomaly_score`;
* `max_anomaly_score`;
* `anomalous_window_ratio`.

Les résultats les plus performants étaient :

```text
LOF / mean_anomaly_score                ROC-AUC = 0.648464
Isolation Forest / mean_anomaly_score   ROC-AUC = 0.632018
One-Class SVM / mean_anomaly_score      ROC-AUC = 0.615009
```

La comparaison complète a montré que `mean_anomaly_score` a obtenu les meilleurs résultats pour les trois modèles.

Le LOF a donc été conservé comme la base la plus forte pour la détection d'anomalies M4.

L'AUC ROC reste modéré, donc M4 ne prouve pas que la détection d'anomalies seule est suffisante pour une classification fiable des tricheurs.

<a id="false-positive-analysis"></a>
## Analyse des fausses positives

Les joueurs légitimes les plus performants ont été examinés à l'aide de leurs fenêtres LOF les plus anormales.

Un motif commun était que seulement un très petit nombre de fenêtres produisaient des scores LOF extrêmement élevés.

Ces fenêtres n'ont pas nécessairement dépassé le 99e percentile légitime pour n'importe quelle caractéristique individuelle.

Cela indique que le LOF détecte principalement des combinaisons multivariées inhabituelles de caractéristiques d'aimage plutôt que des extrémités simples de caractéristiques individuelles.

Ceci est une limitation importante pour l'interprétation :

```text
Anomalous behavior ≠ cheating
```

Un joueur légitime peut occuper une région localement sparsée de l'espace des caractéristiques et recevoir un score d'anomalie élevé.

<a id="feature-ablation"></a>
## Élimination de caractéristiques

L'influence des caractéristiques a été évaluée en supprimant une caractéristique d'entrée à la fois et en recalculant l'AUC ROC au niveau du joueur.

Base :

```text
ROC-AUC = 0.648464
```

Résultats :

```text
Removed feature                  ROC-AUC    Baseline drop
std_angular_acceleration         0.642331    +0.006133
max_angular_acceleration         0.648252    +0.000212
max_angular_speed                0.649006    -0.000542
mean_angular_acceleration        0.649695    -0.001231
mean_angular_speed               0.652057    -0.003593
std_angular_speed                0.652337    -0.003873
```

`std_angular_acceleration` était la caractéristique individuelle la plus influente dans cette expérience.

Cependant, les différences sont faibles. M4 conserve donc toutes les six caractéristiques et considère la détection d'anomalies comme principalement dépendante des combinaisons multivariées de caractéristiques plutôt qu'une mesure dominante unique.

<a id="shot-level-anomaly-scores"></a>
## Scores d'anomalie au niveau du tir

Chaque fenêtre temporelle d'aimage est centrée sur un tir individuel.

La sortie LOF peut donc être exposée directement comme une note d'anomalie au niveau des plans, tout en conservant le lien avec la fenêtre temporelle d'origine grâce à `window_id`.

La sortie générée au niveau des plans contient :

* 405 663 événements évalués ;
* 405 663 fenêtres uniques ;
* 1 216 événements classés comme anormaux par LOF.

La moyenne brute au niveau des événements de LOF est fortement influencée par des valeurs extrêmes. Les scores d'événements sont donc utiles pour localiser des séquences d'objectifs inhabituelles, mais l'agrégation au niveau du joueur reste plus appropriée pour la note initiale de suspicion.

<a id="player-level-anomaly-scores"></a>
## Notes d'anomalie au niveau du joueur

Les notes d'anomalie sont agrégées par match et par joueur.

La sortie au niveau du joueur inclut :

* le nombre de fenêtres analysées ;
* la moyenne de la note d'anomalie ;
* la note d'anomalie maximale ;
* le rapport de fenêtres anormales.

L'ensemble complet contient :

* 3 138 observations joueur-match ;
* 3 133 valeurs uniques de `player_id` ;
* 1 801 observations légitimes étiquetées joueur-match ;
* 1 307 observations suspectes étiquetées joueur-match ;
* 30 observations non étiquetées joueur-match provenant des données natives de démo.

La différence entre 3 138 observations joueur-match et 3 133 identifiants uniques de joueur est attendue car certains identifiants de joueur apparaissent dans plus d'une observation au niveau du match.

<a id="initial-suspicion-score"></a>
## Note initiale de suspicion

M4 introduit une note initiale de suspicion du joueur dérivée de la moyenne d'anomalie de LOF.

Comme les valeurs brutes de LOF peuvent devenir extrêmement grandes, la note brute d'anomalie n'est pas utilisée directement comme valeur finale interprétable.

Au lieu de cela :

```text
LOF mean anomaly score
        ↓
Percentile relative to legitimate players
        ↓
Suspicion score in [0, 100]
```

Un score de 95 signifie que la moyenne d'anomalie de LOF du joueur est supérieure à environ 95 % de la population de calibration légale.

Ce n'est pas une indication que le joueur a une probabilité de 95 % de tricher.

Sur l'ensemble étiqueté :

```text
                 mean       median
legitimate       50.03       50.03
suspicious       64.85       73.74
```

Plusieurs joueurs légitimes reçoivent encore des scores proches de 100, confirmant que la note de suspicion ne doit pas être interprétée comme preuve de tricherie ou comme un seuil d'application automatique.

<a id="implementation-structure-2"></a>
## Structure de mise en œuvre

M4 introduit la couche de détection d'anomalie :

```text
src/cs2guard_demo/detection/
        ↓
feature preprocessing
        ↓
Isolation Forest / LOF / One-Class SVM
        ↓
window / shot anomaly scores
        ↓
player aggregation
        ↓
suspicion score
```

Les scripts de support fournissent :

* l'analyse de base légale ;
* l'exécution du modèle d'anomalie ;
* la comparaison des modèles ;
* l'inspection des faux positifs ;
* l'ablation des caractéristiques ;
* la génération de la note de suspicion ;
* la génération de la note d'anomalie au niveau des plans.

<a id="testing-3"></a>
## Tests

M4 est couvert par des tests automatisés pour :

* l'exécution de l'Isolation Forest ;
* l'exécution du Local Outlier Factor ;
* les sous-ensembles de caractéristiques utilisés pour l'ablation du LOF ;
* l'exécution du One-Class SVM ;
* la validation des caractéristiques manquantes ;
* la validation des caractéristiques numériques invalides ;
* la génération de la note de suspicion.

À la fin de M4, le jeu complet de tests automatisés est passé.

Les trois modèles de détection d'anomalie ont également été exécutés sur l'ensemble complet de 405 663 fenêtres.

<a id="technical-decisions-2"></a>
## Decisions techniques

Les décisions importantes réalisées lors de M4 incluent :

* l'utilisation uniquement de caractéristiques d'objectif comportemental comme entrées pour les modèles non supervisés ;
* l'exclusion des identifiants, des métadonnées de source et des étiquettes des caractéristiques des modèles d'anomalie ;
* l'utilisation uniquement des étiquettes CS2CD pour l'évaluation et la calibration ;
* l'normalisation des caractéristiques avant les expériences de détection d'anomalie ;
* la comparaison de l'Isolation Forest, du Local Outlier Factor et de l'One-Class SVM ;
* le training de l'One-Class SVM sur un échantillon déterministe afin de rendre l'expérience computationnellement pratique ;
* l'utilisation de l'ROC-AUC pour la comparaison croisée entre modèles en raison des écarts importants des échelles des scores d'anomalie brut ;
* l'évaluation des scores au niveau du joueur plutôt que de traiter chaque fenêtre temporelle comme un joueur indépendant ;
* la conservation du Local Outlier Factor comme base la plus forte de M4 avec un ROC-AUC au niveau du joueur de 0,648464 ;
* la conservation des six caractéristiques d'objectif après ablation car les effets individuels des caractéristiques étaient faibles ;
* le traitement des scores d'anomalie élevés comme des comportements inhabituels plutôt que comme une preuve directe de triche ;
* l'exposition des scores de fenêtre temporelle comme des scores d'événement au niveau du tir ;
* la conversion du score de joueur du Local Outlier Factor en un pourcentage relatif légitime pour le score initial de suspicion allant de 0 à 100 ;
* l'évitement d'une limite de bannissement ou de classification de triche pendant M4.

<a id="result-3"></a>
## Résultat

M4 est terminé et validé.

CS2Guard peut désormais attribuer des scores d'anomalie aux événements centrés sur le tir et agréger ces signaux en scores d'anomalie et de suspicion au niveau du joueur.

Parmi les approches non supervisées évaluées, le Local Outlier Factor a produit la meilleure séparation au niveau du joueur :

```text
ROC-AUC = 0.648464
```

Le résultat démontre que les joueurs suspects et légitimes présentent des différences mesurables dans l'espace actuel des caractéristiques d'objectif, mais cette séparation n'est pas suffisamment forte pour considérer la détection d'anomalie comme un classificateur autonome de triche.

L'Analyseur de démonstration a évolué de :

> "Comment les caractéristiques comportementales peuvent-elles être converties en un ensemble de données reproductible ?"

à :

> "Peut-on détecter automatiquement un comportement inhabituel d'aimage, et comment peut-on agréger cette preuve en un signal de suspicion au niveau du joueur interprétable ?"

M4 fournit la base de détection d'anomalie nécessaire aux expériences supervisées prévues dans M5.

---

<a id="m5--supervised-detection"></a>
# M5 - Détection supervisée

<a id="objective-4"></a>
## Objectif

L'objectif de M5 était d'évaluer la classification supervisée une fois que des étiquettes légitimes et suspectes furent disponibles grâce à l'ensemble canonique.

M5 réutilise les mêmes six caractéristiques d'objectif évaluées lors de M4, mais contrairement à la détection d'anomalie, les modèles supervisés sont explicitement entraînés à l'aide des étiquettes disponibles du CS2CD.

Conceptuellement :

```text
Labeled aim features
        ↓
Leakage-safe train / test split
        ↓
Supervised classification
        ↓
Model evaluation
        ↓
Hyperparameter tuning
        ↓
Threshold analysis
        ↓
Player-level suspicion scores
```

Une exigence centrale de M5 est de préserver l'isolement au niveau de la partie entre les données d'entraînement et les données d'évaluation afin que des fenêtres provenant de la même partie ne soient pas présentes dans les deux ensembles.

<a id="labeled-dataset"></a>
## Ensemble étiqueté

Un ensemble supervisé dédié est généré à partir de l'ensemble canonique des caractéristiques d'objectif.

Seulement les échantillons avec une étiquette valide sont conservés :

```text
legitimate
suspicious
```

Les échantillons natifs non étiquetés sont exclus de l'entraînement supervisé.

L'ensemble de données supervisé contient :

* 397 487 échantillons étiquetés ;
* 317 correspondances ;
* 3 108 joueurs ;
* 6 caractéristiques numériques d'objectif.

La répartition des étiquettes est :

```text
legitimate    282,022
suspicious    115,465
```

Les six caractéristiques du modèle sont les mêmes que celles utilisées durant M4 :

* `mean_angular_speed`;
* `max_angular_speed`;
* `std_angular_speed`;
* `mean_angular_acceleration`;
* `max_angular_acceleration`;
* `std_angular_acceleration`.

Les identifiants tels que `match_id`, `player_id`, `window_id` et l'étiquette elle-même sont conservés pour la gestion et l'évaluation de l'ensemble de données, mais ne sont pas fournis comme entrées du modèle.

<a id="train--test-split"></a>
## Division d'entraînement / test

L'ensemble de données supervisé est divisé par regroupement au niveau de la correspondance.

Au lieu de distribuer aléatoirement des fenêtres individuelles entre l'ensemble d'entraînement et l'ensemble de test, tous les échantillons appartenant à la même correspondance restent dans la même partition.

Cela empêche un modèle d'être entraîné sur des fenêtres provenant d'une correspondance qui apparaît également dans l'ensemble de test réservé.

La division fixe utilise :

```text
Train
306,315 samples
253 matches

Test
91,172 samples
64 matches
```

La répartition des étiquettes dans l'ensemble d'entraînement est :

```text
legitimate    215,434
suspicious     90,881
```

La répartition des étiquettes dans l'ensemble de test est :

```text
legitimate     66,588
suspicious     24,584
```

La division utilise un état aléatoire fixe afin que tous les expériences M5 soient évaluées avec les mêmes correspondances réservées.

<a id="baseline-classifiers"></a>
## Classificateurs de référence

M5 établit d'abord deux classificateurs de référence.

<a id="dummy-classifier"></a>
### Classificateur vide

Un `DummyClassifier` utilisant la distribution des classes d'entraînement fournit une référence triviale.

Sur l'ensemble de test réservé :

```text
accuracy = 0.7304
```

Le modèle prédit aucun échantillon suspect à la règle de décision par défaut :

```text
Precision = 0.0000
Recall    = 0.0000
F1-score  = 0.0000
ROC-AUC   = 0.5000
PR-AUC    = 0.2696
FPR       = 0.0000
```

Le PR-AUC correspond à la prévalence de la classe positive dans l'ensemble de test réservé et fournit donc une base utile pour les modèles suivants.

<a id="logistic-regression"></a>
### Régression logistique

La régression logistique est utilisée comme première base supervisée apprise.

Le classificateur est placé après un `StandardScaler` dans une pipeline de scikit-learn afin que l'échelle des caractéristiques soit adaptée uniquement sur les données d'entraînement.

Résultats initiaux sont :

```text
accuracy  = 0.7306
Precision = 0.5102
Recall    = 0.0214
F1-score  = 0.0410
ROC-AUC   = 0.5547
PR-AUC    = 0.3230
FPR       = 0.0076
```

La précision est presque identique à la base vide, tandis que le rappel reste extrêmement faible.

Cela démontre pourquoi la précision seule n'est pas suffisante pour évaluer le problème de classification anti-triche.

<a id="random-forest"></a>
## Forêt aléatoire

La forêt aléatoire a été introduite comme premier modèle supervisé non linéaire.

La configuration initiale utilise :

```text
n_estimators     = 100
max_depth        = 20
min_samples_leaf = 5
```

Les résultats initiaux sur l'ensemble réservé sont :

```text
accuracy  = 0.7340
Precision = 0.5336
Recall    = 0.1078
F1-score  = 0.1794
ROC-AUC   = 0.5933
PR-AUC    = 0.3813
FPR       = 0.0348
```

La forêt aléatoire améliore considérablement la rétention, le score F1 et le PR-AUC par rapport à la régression logistique, indiquant que les interactions non linéaires entre les caractéristiques d'objectif contiennent des informations supervisées utiles.

<a id="histogram-gradient-boosting"></a>
## Boosting par histogramme

`HistGradientBoostingClassifier` a été évalué comme deuxième modèle supervisé non linéaire.

Il a été choisi au lieu de `GradientBoostingClassifier` car l'implémentation basée sur les histogrammes est mieux adaptée aux environnements de 300 000 échantillons d'entraînement utilisés par M5.

La configuration initiale utilise :

```text
learning_rate  = 0.1
max_iter       = 100
max_leaf_nodes = 31
```

Les résultats initiaux sur l'ensemble réservé sont :

```text
accuracy  = 0.7356
Precision = 0.5593
Recall    = 0.0915
F1-score  = 0.1572
ROC-AUC   = 0.5934
PR-AUC    = 0.3791
FPR       = 0.0266
```

Le modèle initial de boosting par histogramme présente une précision légèrement supérieure et un taux de fausses positives inférieur à celui de la forêt aléatoire initiale, tandis que la forêt aléatoire présente un rappel, un score F1 et un PR-AUC plus élevés.

<a id="evaluation-metrics"></a>
## Métriques d'évaluation

M5 introduit une couche commune d'évaluation pour tous les modèles supervisés.

Les métriques évaluées incluent :

* précision ;
* sensibilité ;
* score F1 ;
* AUC-ROC ;
* AUC-PR ;
* taux de faux positifs ;
* comptages de la matrice de confusion.

La classe suspecte est traitée comme la classe positive :

```text
0 = legitimate
1 = suspicious
```

L'AUC-PR est implémentée à l'aide de la précision moyenne plutôt que d'une intégration trapezoidale directe de la courbe de précision-rappel.

Cela assure que classificateur à score constant produit une base correspondant à la prévalence de la classe positive.

Pour l'ensemble de test réservé :

```text
positive prevalence ≈ 0.2696
```

et le classificateur Dummy produit donc :

```text
PR-AUC = 0.2696
```

<a id="hyperparameter-tuning"></a>
## Ajustement des hyperparamètres

La recherche aléatoire a été utilisée pour ajuster les Random Forest et les Gradient Boosting à base de histogramme.

L'ensemble de test réservé de 64 correspondances n'est pas utilisé lors du choix des hyperparamètres.

Au lieu de cela, l'ajustement s'opère uniquement sur les 253 correspondances d'entraînement en utilisant une validation croisée par groupes.

Conceptuellement :

```text
253 training matches
        ↓
StratifiedGroupKFold
        ↓
3 validation folds
        ↓
PR-AUC optimization
        ↓
Best hyperparameters
```

L'AUC-PR / la précision moyenne est utilisée comme métrique principale d'ajustement car les échantillons suspects sont moins fréquents que les échantillons légitimes et car le classement des comportements suspects est plus informatif que la précision brute.

<a id="random-forest-tuning"></a>
### Ajustement du Random Forest

Le meilleur résultat de validation croisée du Random Forest est :

```text
Best CV PR-AUC = 0.4471
```

avec :

```text
n_estimators     = 150
min_samples_leaf = 5
max_features     = sqrt
max_depth        = 15
class_weight     = None
```

<a id="histogram-gradient-boosting-tuning"></a>
### Ajustement du Gradient Boosting à base d'histogramme

Le meilleur résultat du Gradient Boosting à base d'histogramme est :

```text
Best CV PR-AUC = 0.4457
```

avec :

```text
max_leaf_nodes    = 63
max_iter          = 150
learning_rate     = 0.1
l2_regularization = 1.0
class_weight      = balanced
```

L'arrêt prématuré interne est désactivé pendant la validation croisée par groupes afin que l'ajustement supplémentaire par découpage aléatoire ne réintroduise pas une fuite au niveau des correspondances.

Le Random Forest atteint une AUC-PR de validation croisée légèrement supérieure et est retenu comme candidat principal du modèle supervisé M5.

<a id="tuned-model-evaluation"></a>
## Évaluation du modèle ajusté

Après ajustement, les deux configurations sélectionnées sont réentraînées sur l'ensemble complet de 253 correspondances d'entraînement et évaluées une fois sur l'ensemble de test réservé de 64 correspondances.

<a id="tuned-random-forest"></a>
### Random Forest ajusté

Le Random Forest ajusté produit :

```text
Precision = 0.5669
Recall    = 0.0929
F1-score  = 0.1596
ROC-AUC   = 0.5932
PR-AUC    = 0.3818
FPR       = 0.0262
```

Par rapport au Random Forest non ajusté, le modèle ajusté devient plus conservateur :

```text
Precision increases
FPR decreases
Recall decreases
```

<a id="tuned-histogram-gradient-boosting"></a>
### Gradient Boosting à base d'histogramme ajusté

Le modèle ajusté de Gradient Boosting à base d'histogramme produit :

```text
Precision = 0.3437
Recall    = 0.4488
F1-score  = 0.3893
ROC-AUC   = 0.5950
PR-AUC    = 0.3827
FPR       = 0.3164
```

Le poids équilibré des classes augmente fortement la détection des échantillons suspects, mais cela entraîne un taux de faux positifs beaucoup plus élevé.

Cela démontre que le fait d'avoir un score de classement utile ne signifie pas nécessairement que le seuil par défaut du modèle est approprié.

<a id="false-positive-and-threshold-analysis"></a>
## Analyse des faux positifs et seuils

M5 évalue donc les modèles ajustés sur plusieurs seuils de probabilité.

Les seuils analysés vont de :

```text
0.10
to
0.90
```

Pour chaque seuil, CS2Guard mesure :

```text
precision
recall
F1-score
false-positive rate
false positives
true positives
```

L'analyse démontre le compromis attendu :

```text
lower threshold
    ↓
higher recall
    ↓
more false positives

higher threshold
    ↓
lower false-positive rate
    ↓
lower recall
```

Par exemple, le Random Forest ajusté au seuil `0.50` produit :

```text
Precision = 0.5669
Recall    = 0.0929
F1-score  = 0.1596
FPR       = 0.0262
```

Le modèle ajusté de Gradient Boosting à base d'histogramme atteint une région similaire de faux positifs autour du seuil `0.70` :

```text
Precision = 0.5666
Recall    = 0.0967
F1-score  = 0.1652
FPR       = 0.0273
```

En revanche, son seuil par défaut de `0.50` produit :

```text
Recall = 0.4488
FPR    = 0.3164
```

Cela montre que pour obtenir un rappel considérablement supérieur, il faut actuellement une augmentation inacceptable des faux positifs.

Aucune seuil final de sanction ni de classification des cas de fraude n'est sélectionné pendant M5.

L'ensemble de test réservé est utilisé pour caractériser le comportement du modèle, et non pas pour optimiser répétitivement un seuil de production.

<a id="supervised-vs-anomaly-detection"></a>
## Apprentissage supervisé versus détection d'anomalies

M5 introduit également une comparaison directe entre l'apprentissage supervisé et l'approche de détection d'anomalies développée pendant M4.

Les expériences originales de M4 et les métriques d'événement du modèle supervisé de M5 ne pouvaient pas être directement comparées car ils utilisaient des conditions d'évaluation et des niveaux d'agrégation différents.

Une nouvelle évaluation commune est donc utilisée :

```text
same 253 training matches
same 64 held-out test matches
same six aim features
same player-match aggregation
```

Le Local Outlier Factor est évalué en mode de nouveauté.

Il est adapté uniquement sur les caractéristiques d'entraînement et puis utilisé pour évaluer les échantillons réservés, sans utiliser les étiquettes de fraude pendant l'adaptation.

Les probabilités d'événement supervisées et les scores d'anomalie du LOF sont ensuite agrégées par match et par joueur.

L'évaluation commune réservée contient :

```text
637 player-match observations
```

Les résultats sont :

```text
Random Forest tuned
ROC-AUC = 0.7779
PR-AUC  = 0.6840

HistGradientBoosting tuned
ROC-AUC = 0.7798
PR-AUC  = 0.6800

LOF held-out
ROC-AUC = 0.6323
PR-AUC  = 0.4624
```

Les approches supervisées surpassent donc considérablement la base de départ en LOF sur le jeu actuel de données annotées sur la caractéristique d'objectif.

Les forêts aléatoires et les gradient boosting à base de histogrammes restent très proches l'un de l'autre.

La forêt aléatoire est conservée comme modèle principal de M5 car elle a obtenu le meilleur PR-AUC lors de la validation croisée par groupes et le meilleur PR-AUC au niveau du joueur dans l'évaluation réservée.

Ce résultat ne signifie pas que la détection d'anomalies est obsolète.

L'évaluation non supervisée peut encore rester utile lorsque les étiquettes sont inaccessibles, pour une analyse exploratoire, ou comme signal supplémentaire dans l'agrégation des scores de suspicion ultérieurs.

<a id="model-persistence-and-versioning"></a>
## Persistence et versionnement des modèles

M5 introduit la persistance pour les modèles supervisés entraînés.

La forêt aléatoire sélectionnée peut être enregistrée sous forme d'un bundle de modèle versionné :

```text
models/supervised/
├── random_forest_v1.joblib
└── random_forest_v1.json
```

Le fichier `.joblib` contient le modèle entraîné scikit-learn.

Les métadonnées JSON enregistrent les informations nécessaires pour identifier et reproduire le modèle, y compris :

* nom du modèle ;
* version ;
* caractéristiques d'entrée ;
* cartographie des étiquettes ;
* paramètres hyperparamétriques ;
* état aléatoire ;
* nombre d'échantillons et de matches d'entraînement ;
* nombre d'échantillons et de matches de l'ensemble de test réservé ;
* métriques d'évaluation au niveau d'événement ;
* AUC ROC et AUC PR au niveau du joueur.

Les métadonnées du modèle conservent :

```text
decision_threshold = None
```

car M5 ne sélectionne pas un seuil opérationnel final.

Le modèle est donc principalement persisté sous forme de modèle de scoring probabiliste de suspicion plutôt que sous forme de classificateur automatique de fraude.

<a id="implementation-structure-3"></a>
## Structure de l'implémentation

M5 introduit une couche dédiée à l'apprentissage supervisé :

```text
src/cs2guard_demo/supervised/
        ↓
dataset preparation
        ↓
baseline / RF / HGB models
        ↓
evaluation
        ↓
hyperparameter tuning
        ↓
threshold analysis
        ↓
supervised / anomaly comparison
        ↓
model persistence
```

Les responsabilités principales de l'implémentation sont séparées en :

```text
dataset.py
    → labeled dataset preparation and grouped splitting

models.py
    → supervised model definitions and training

evaluation.py
    → classification metrics and threshold analysis

tuning.py
    → grouped hyperparameter search

comparison.py
    → player-level supervised / anomaly comparison

persistence.py
    → model and metadata serialization
```

Les scripts de support fournissent :

* génération de l'ensemble de données annoté ;
* entraînement de base et de modèle ;
* ajustement des hyperparamètres ;
* évaluation du modèle ajusté ;
* analyse du seuil ;
* comparaison supervisée versus détection d'anomalies ;
* persistance du modèle.

<a id="testing-4"></a>
## Test

M5 étend le cadre de tests automatisés pour couvrir :

* construction d'un ensemble de données étiqueté ;
* étiquettes invalides et valeurs numériques ;
* isolation au niveau du match entre entraînement et test ;
* préparation des caractéristiques et cibles supervisées ;
* création et entraînement d'un classificateur de référence ;
* création et entraînement d'un Random Forest ;
* création et entraînement d'un Histogram Gradient Boosting ;
* création et entraînement d'un modèle ajusté ;
* évaluation de la précision, du rappel, du score F1, de l'ROC-AUC et de l'AP-AUC ;
* comportement de l'AP-AUC pour un classificateur constant ;
* évaluation avec seuil configurable ;
* gestion des seuils invalides ;
* analyse des seuils ;
* validation croisée groupée sans surchevauchement de match ;
* ajustement du Random Forest ;
* ajustement du Histogram Gradient Boosting ;
* agrégation des scores au niveau du joueur ;
* évaluation du LOF sur un ensemble réservé ;
* comparaison supervisée versus détection d'anomalies ;
* comportement de persistance et de rechargement du modèle.

Le cadre de tests supervisés est passé à la fin de M5.

Des expériences réelles ont également été effectuées sur l'ensemble de données étiqueté complet et sur le découpage fixe de matches réservés.

<a id="technical-decisions-3"></a>
## Decisions techniques

Les décisions importantes prises durant M5 incluent :

* la réutilisation des six caractéristiques d'objectif de M4 afin que les expériences supervisées et de détection d'anomalies restent comparables ;
* l'exclusion des échantillons non étiquetés de l'entraînement supervisé ;
* la conservation des identifiants pour le regroupement tout en les excluant des entrées du modèle ;
* la séparation des données d'entraînement et de test par match plutôt que par fenêtre individuelle ;
* la conservation d'un ensemble de test réservé de 64 matches tout au long de M5 ;
* l'ajustement des prétraitements uniquement sur les données d'entraînement ;
* l'utilisation d'un DummyClassifier comme référence de performance triviale ;
* l'utilisation de la Régression Logistique comme première base supervisée apprise ;
* l'évaluation du Random Forest et du Histogram Gradient Boosting comme modèles non linéaires pour tableaux ;
* l'utilisation de la précision, du rappel, du score F-1, de l'ROC-AUC et de l'AP-AUC plutôt que de se baser sur l'exactitude ;
* l'utilisation de l'approche de précision moyenne pour l'AP-AUC ;
* l'utilisation de la validation croisée groupée pour l'ajustement des hyperparamètres ;
* l'optimisation des hyperparamètres en utilisant l'AP-AUC plutôt que l'exactitude ;
* la désactivation de l'arrêt prématuré interne du Histogram Gradient Boosting pendant l'ajustement groupé ;
* l'analyse des seuils de décision séparément de la performance de classement du modèle ;
* le traitement de la fréquence de faux positifs comme métrique critique d'évaluation anti-triche ;
* l'évitement du choix d'un seuil d'application en production à partir de l'ensemble de test réservé ;
* la comparaison des approches supervisées et non supervisées sur les mêmes matches réservés et l'agrégation au niveau du joueur ;
* la conservation du Random Forest comme modèle supervisé principal de M5 ;
* la conservation du Histogram Gradient Boosting comme modèle alternatif fort ;
* la persistance du modèle sélectionné accompagnée des métadonnées de reproductibilité ;
* enregistrer le seuil du modèle M5 sans modification afin que la logique ultérieure du Demo Analyzer puisse déterminer la manière dont les scores doivent être regroupés et interprétés.

<a id="result-4"></a>
## Résultat

M5 est complet et validé.

CS2Guard peut désormais entraîner, ajuster, évaluer et persister des classificateurs supervisés de comportement à partir de données étiquetées sur les caractéristiques d'objectif.

Les résultats au niveau des événements initiaux montrent que la classification reste difficile lorsque chaque fenêtre centrée sur une tirée est traitée de manière indépendante.

Cependant, l'agrégation au niveau du joueur sur les données de test réservées produit une séparation considérablement plus forte.

Le principal arbre aléatoire M5 atteint :

```text
ROC-AUC = 0.7779
PR-AUC  = 0.6840
```

au niveau du match joueur.

Pour comparaison, le facteur local d'outlier réservé atteint :

```text
ROC-AUC = 0.6323
PR-AUC  = 0.4624
```

Cela démontre que les étiquettes disponibles sur les cas de fraude fournissent une information substantielle au-delà de la détection d'anomalies purement non supervisée.

En même temps, l'analyse des seuils confirme que la performance de détection et le contrôle des fausses positives restent en tension.

Le modèle supervisé est donc considéré comme une preuve d'indications de comportement suspect, et non comme une preuve que le joueur est en train de tricher.

Le Demo Analyzer a évolué de :

> "Peut-on détecter automatiquement un comportement d'aimage inhabituel ?"

à :

> "Peut-on améliorer le classement des joueurs suspects à l'aide de données comportementales étiquetées, et peut-on évaluer et persister ce modèle sans introduire de fuites de données évitables ?"

M5 fournit le modèle supervisé utilisé par l'analyse de démo en mode hors ligne dans M6.

---

<a id="m6--demo-analyzer"></a>
# M6 - Analyse de démo

<a id="initial-audit-scope-and-reference-state--2026-10-14"></a>
## Portée initiale de l'audit et état de référence - 2026-10-14

L'audit et la mise en œuvre du 2026-10-14 conservent le plan de la documentation README : M6 est une analyse de démo hors ligne. Le streaming côté serveur reste M9/M10 ; `server_side/` reste inchangé. La branche initiale était `main`, sans modifications locales enregistrées. Le projet utilise une structure `src` de setuptools et des imports canoniques `cs2guard_demo`. Tous les fichiers Python, les 20 scripts historiques, les tests, la configuration de package/test, les documents d'architecture et les métadonnées persistées de M5 ont été inspectés. Les artefacts de modèle, les ensembles de données et les résultats de recherche ont été conservés.

L'outil existant `.venv` utilise Python 3.13.1, pytest 9.1.1, NumPy 2.5.2, pandas 3.0.5, scikit-learn 1.9.1, demoparser2 0.42.0, Matplotlib 3.11.1 et joblib 1.6.0. Le système Python manque de demoparser2 ; les commandes utilisent donc l'environnement du projet. Le modèle persisté installé est un RandomForestClassifier à 150 arbres, avec les classes `[0, 1]` et les six noms de caractéristiques attendus dans l'ordre d'entraînement. Il se charge sans avertissement de compatibilité. Ses fichiers de modèle et JSON restent inchangés.

La base avant tout changement de code était **179 passés, 0 échoués, 0 sautés**. Une exécution préalable dans un environnement par défaut avait **163 passés et 16 erreurs de configuration de fixture**, causées par un répertoire temporaire système inaccessible, et non par des erreurs d'application. Un `--basetemp` local au dépôt a établi une base propre. Ce contournement a été ultérieurement supprimé à la demande de l'utilisateur ; les tests finaux utilisent désormais les répertoires temporaires natifs de pytest avec un accès au système de fichiers approuvé.

<a id="confirmed-audit-findings-and-actions"></a>
## Trouvailles confirmées de l'audit et actions

Les chemins dans ce tableau sont relatifs à `demo_analyzer/` sauf indication contraire.

|Fichier / symbole|Problème|Preuves|Action|Risque|
|---|---|---|---|---|
| `src/cs2guard_demo/parser/events.py`, `utils/logger.py` |Placeholders morts|Fichiers vides, aucune référence en Python/documentation, aucune implémentation exportée|Supprimés uniquement ces deux fichiers|Faible|
|`parser/demo_parser.py` import pandas ; `scripts/parse_demo.py`, `visualize_aim.py` `ROOT_DIR`|Imports/variables inutilisés|Vérifications AST et de référence montrent uniquement la déclaration|Supprimé|Faible|
|`DemoParser` tirs/impact/éliminations/ticks/joueurs/équipes/rounds|Des cadres backend vides déclenchent `KeyError`|Des retours backend contrôlés retournent `DataFrame()` sans colonnes|Conserver les schémas/listes vides|Faible ; le comportement non vide reste inchangé|
| `DatasetBuilder.build_temporal_windows`, `build_canonical_temporal_windows` |Des lignes dupliquées de tirs/ticks corrompent les fenêtres|Des duplications de tirs dupliquent une `window_id` ; une duplication de tick peut satisfaire le comptage de lignes sans chronologie complète|Éliminer les tirs, rejeter les fenêtres ambiguës de ticks|Moyen ; le comportement face à des entrées invalides/dupliquées a été corrigé intentionnellement|
|Mêmes constructeurs de fenêtres|Scans répétés d'entiers complets|Le cadre complet de tick est filtré par tir|Regrouper et trier une fois, sélectionner les bornes avec `searchsorted`|Faible ; les résultats de fonctionnalités exacts ont été testés|
| `dataset/builder.py`, `dataset/adapters/demo.py` |Remplacement de l'infini provoque une panne dans pandas installé|Cas de régression reproduit `IndexError: pop index out of range` avec `pd.NA`|Remplacer l'infini par NaN avant l'exclusion existante|Faible ; les sémantiques d'exclusion sont préservées|
| `dataset/adapters/cs2cd.py` |Les données de télémétrie infinies survivent à la normalisation|Données synthétiques NaN/Inf|Supprimer les données de télémétrie invalides requises|Faible|
| `scripts/build_dataset.py::append_dataframe` |Les en-têtes CSV diffèrent entre les sources ; les blocs vides affectent l'en-tête ultérieure|Des champs optionnels et un ordre différents dans les cas de test Demo/CS2CD|Union stable des champs existants, ignorer les blocs vides, rejeter les champs inconnus/headers incompatibles lors du reprise|Moyen ; les CSV interrompus en mode ancien peuvent nécessiter une reconstruction|
| `scripts/build_dataset.py::build_demo_chunk/build_cs2cd_chunk` |Pipeline de fonctionnalités identique|Seulement la construction de l'adaptateur varie|Réutiliser `build_chunk(builder, adapter)`|Faible|
| `dataset/statistics.py::generate_dataset_statistics` |Les ensembles canoniques comptent zéro joueur|La fonction lit uniquement `steamid`, absent du schéma canonique|Privilégier `player_id`, conserver le fallback ancien|Faible|
| `dataset/labels.py`, `statistics.py`, `detection/anomaly.py`, `scripts/analyze_false_positives.py` |Étiquettes dupliquées/listes de six caractéristiques|Constantes identiques dans plusieurs modules|Importer les constantes du schéma/existant et de la normalisation|Faible ; l'ordre a été vérifié|
| `scripts/validate_demo.py` |Des fenêtres vides déclenchent `KeyError: window_id`|Les tests exécutent le script réel `main()` avec des données vides|Réutiliser le comptage conditionnel de fenêtre|Faible|
| `supervised/comparison.py::aggregate_player_scores` |La série s'aligne sur un index pandas non lié|L'index du jeu `[10,11]`, l'index des scores `[0,1]` génèrent NaN|Affectation positionnelle `np.asarray(scores)`|Faible ; les scripts ndarray restent inchangés|
| `supervised/evaluation.py::evaluate_predictions` |Des cibles à une seule classe retournent des métriques indéfinies|Un ROC-AUC/FPR à une seule classe génèrent NaN|Erreur explicite sauf si les deux classes 0/1 existent|Faible ; les métriques historiques valides restent inchangées|
| `scripts/train_supervised.py`, `evaluate_tuned_supervised.py::print_metrics` |Impression identique des métriques|Mêmes champs/formats|Réutilisation de la fonction de module d'évaluation existante|Faible ; la sortie est vérifiée|
| `visualization/aim.py::plot_aim_trajectory` |Aucune sortie enregistrée pour M6|La figure se ferme sans exportation|Optionnelles `output_path` et `distance_label` ; le comportement par défaut reste inchangé|Faible|
|Cas de test M1–M5|Travail réellement dupliqué|Test d'événement répète exactement le cadre multi-démonstration ; les tests de détecteur et de formation répètent les configurations/affirmations|Regrouper les affirmations d'événement ; paramétrer les cas de modèle|Faible ; la couverture indépendante est conservée|

Les similarités suivantes ont été examinées et **ont été conservées**, plutôt que traitées comme du code mort confirmé :

|Symbole / famille|Motif de conservation|
|---|---|
|API d'événement/fenêtre du DatasetBuilder hérité vs API canonique du DemoAdapter|Des schémas d'identité différents, des structures de sortie et des appelants publics ; la fusion introduirait des conversions|
|Aggrégation des joueurs M4 vs M5|M4 utilise six clés d'identité et des ratios de moyenne/maximum/anomalie ; M5 utilise match/joueur et score moyen|
|M4 LOF transductif vs nouveauté LOF en dehors de l'ensemble M5|Des tâches d'évaluation différentes ; l'adaptateur de formation uniquement dans le chemin réservé est essentiel|
|Aideurs M2 d'acquisition, de suivi, de réaction, de correction et de snap|Appels publics, comportements indépendamment testés et appelants expérimentaux de visualisation|
|Scripts historiques et artefacts de recherche persistés|Des expériences distinctes, utilisation documentée et valeur de reproductibilité|
|Fixtures similaires d'adaptateur|Formats sources et responsabilités de normalisation diffèrent|
|Liste complète des joueurs du parser, incluant les participants possibles en phase de réchauffement|Les sémantiques historiques peuvent être utiles ; M6 conserve les joueurs et marque les preuves absentes plutôt que de les supprimer silencieusement|

Les formules scientifiques, le wrapping angular, les unités de tick, les écarts types de population (`ddof=0`), l'ajustement du scaleur, l'ordre des caractéristiques, les paramètres du modèle, le partage des divisions, les signes des scores LOF et la calibration de l'ECDF restent inchangés pour les données historiques valides. Aucun seuil de production ni nouvelle calibration n'est introduit. Les fenêtres invalides ou non-finies et les métriques non définies échouent ou sont explicitement exclues.

<a id="coverage-and-test-consolidation"></a>
## Couverture et consolidation des tests

|Zone fonctionnelle|Couverture vérifiée|Avant|Après|
|---|---|---:|---:|
|M1 parser|Payloads normalisés valides, joueurs/événements/rounds/ticks, début de match récent, fichiers manquants, erreurs du backend, données vides, match avec/sans ticks| 7 | 14 |
|M2 géométrie et graphiques|±180° wrapping, directions/distances, vitesse/accélération/temps, acquisition/réponse, suivi/corrections/overshoot/snaps, association des tirs, entrées invalides, export PNG réel| 95 | 96 |
|M3 ensembles de données/adapteurs/scripts|Identificateurs canoniques/étiquettes, fenêtres multiformes, données finies, caractéristiques numériques exactes, temps irrégulier d'horloge, doublons/fenêtres incomplètes, normalisation, divisions sans fuite de correspondance, statistiques, CSV stable/retour en arrière| 42 | 61 |
|Anomalies M4|Formation/évaluation IF/LOF/OCSVM, ordre des caractéristiques/cast, valeurs finies, sens des scores, reproductibilité, agrégation d'identité, nœuds ECDF/erreurs de calibration| 7 | 18 |
|M5 supervisé|Baselines/RF/HGB/modèles ajustés, probabilités normalisées finies, validation croisée par groupes/reproductibilité des divisions, seuils, métriques, moyennes des joueurs, scores positionnels, LOF réservé, persistance et ordre des caractéristiques| 28 | 46 |
|Analyse M6|Intégration fin-à-fin contrôlée M1–M5, équipe complète de joueurs, moyennes exactes/rang, tours/événements, graphiques/rapports, compatibilité des modèles, données partielles/vides, contributions exactes des arbres et CLI| 0 | 39 |
|**Total**|**Aucun test sauté**| **179** | **274** |

M1–M5 gagnent **57 cas** et suppriment **un cas exactement dupliqué**, pour **235 cas** après consolidation. `test_event_level_samples` est fusionné dans `test_process_multiple_demos`, tout en conservant les affirmations. Trois tests de détecteurs deviennent un test paramétré couvrant les mêmes trois détecteurs ; quatre tests de formation deviennent un test paramétré couvrant les mêmes quatre chemins. M6 ajoute 39 cas dans `test_analysis.py`. `test_build_dataset_script.py` est le seul autre fichier de test nouveau. Les 91 tests existants sur les caractéristiques M2 sont conservés ; des cas semblables couvrent des algorithmes ou des limites différents.

Les nouveaux tests ont exposé initialement la panne de pandas sur l'infini et l'omission des statistiques des joueurs canoniques ; les deux ont été corrigés et vérifiés. Une affirmation de persistance RF nouvellement ajoutée utilisait initialement une égalité exacte et a échoué à `1.11e-16` ; la tolérance `1e-12` prend désormais en compte la somme parallèle des arbres à virgule flottante. Deux attentes M6 ont été mises à jour après l'ajout de compteurs explicites pour les données partielles. Aucun test historique réussi n'a été affaibli pour cacher une régression du produit.

Les tests automatisés restent petits et synthétiques. Aucun test de suite n'exige un téléchargement de démonstration, des données CS2CD externes ou une formation coûteuse sur l'ensemble des données. L'anonymisation CS2CD empêche encore de garantir l'indépendance des joueurs réels entre différentes parties ; l'indépendance au niveau de la partie est testée. Cette première vérification n'a pas répété les expériences historiques sur les modèles à ensemble complet de données.

<a id="implementation-and-scientific-interpretation"></a>
## Implémentation et interprétation scientifique

L'implémentation initiale de M6 a introduit `analysis.py`, `cli.py` et `__main__.py` ; `pyproject.toml` inscrit `cs2guard = cs2guard_demo.cli:main`. Matplotlib, déjà utilisé et installé pour M2, est déclaré comme dépendance en temps de fonctionnement car les rapports en nécessitent. Le manque de support de construction setuptools dans l'environnement existant a bloqué initialement une installation sans isolement de construction ; l'installation isolée ordinaire installe uniquement les exigences de construction déjà déclarées par le projet. Aucune dépendance supplémentaire en matière de modélisation, de rapports ou de CLI n'est introduite.

Le pipeline réutilise DemoAdapter/DemoParser, DatasetBuilder, géométrie/plots M2, M4 `prepare_features`, chargement du bundle M5 et l'agrégation des joueurs M5. Il vérifie une entrée non vide `.dem`, des métadonnées adjacentes, des noms de caractéristiques/ordre/dimensions, la carte des classes, la forme/la plage de sortie de probabilité et les paramètres facultatifs d'extraction enregistrée. Il ne s'entraîne jamais à un modèle lors de l'analyse. Les paramètres d'extraction historiques sont fixés à 32 ticks et 64 Hz, correspondant aux scripts d'entraînement ; les paramètres de métadonnées manquants sont explicitement documentés comme une limitation de compatibilité.

Chaque joueur de la liste des parseurs, chaque acteur de la télemétrie/événement et chaque victime d'événement est conservé. Les joueurs sans fenêtre de tir fini sont attribués une note nulle avec une explication. Les joueurs ayant des fenêtres sont classés par ordre décroissant de la moyenne M5, puis par identifiant canonique ; les joueurs non notés suivent sans classement. Le JSON complet conserve chaque fenêtre notée et six caractéristiques mesurées. L'association de tour utilise le tick de tir ; dans l'absence de contexte de tour terminé, la valeur reste nulle et les fenêtres croisées sont marquées. Les événements dans le même acteur/arme/tour durant les deux ticks suivants fournissent un contexte d'inspection proche, sans prouver une relation causale entre tir et impact.

Les trois fenêtres les plus notées par joueur sont sélectionnées pour l'inspection, même si toutes les notes sont faibles. Ceci est une limite d'affichage, pas un seuil de suspicion validé. La priorité d'inspection de tour est la note maximale de fenêtre dans chaque tour terminé, et non une probabilité calibrée de tour. Les indicateurs de vitesse et d'accélération sont des moyennes arithmétiques des moyennes des caractéristiques de fenêtre, exprimées en degrés/seconde et degrés/seconde² ; ils ne sont pas combinés avec les sorties du modèle. Les mesures de traçage utilisent M2 uniquement lorsque la victime observée a une télemétrie simultanée. Sinon, le graphique fait explicitement référence à la direction de tir. La réaction n'a pas de stimulus visuel observé et reste indisponible. L'importance globale de la caractéristique RF et les valeurs brutes des fenêtres expliquent les mesures disponibles. Pour les M5 RF persistants et les arbres de décision natifs, les contributions locales décomposent également la prédiction existante : chaque coup de branchement contribue à sa caractéristique la probabilité de classe 1 de l'arbre fils moins celle du parent. La base de départ de la racine, ajoutée à ces changements signés, donne la probabilité de feuille. Les changements et les bases sont moyennés sur les arbres de forêt ; les contributions des joueurs sont moyennées sur les fenêtres, exactement correspondant à l'agrégation de la note M5. La conversion d'entrée utilise la même précision float32 que l'inference des arbres de scikit-learn. La reconstruction est affirmée à la tolérance `1e-12`. Ceci est une explication arithmétique du modèle inchangé, pas un nouveau détecteur ou une calibration. Elle dépend de l'ordre des coupes et n'est ni une attribution causale ni une SHAP. Les familles d'estimateurs non prises en charge conservent explicitement des contributions locales nulles ; leurs caractéristiques mesurées et leur importance globale restent séparées. Il n'y a pas de sous-modèle de comportement anormal nouveau, de score pondéré arbitraire, de calibration ECDF sur des joueurs non étiquetés ou de conclusion de fraude.

`report.json` est lisible par machine ; `report.md` fournit des classements, des valeurs comportementales, des priorités de tour, des limites de séquence de revue, des événements/paramètres, des liens d'images et des limites d'interprétation. La sortie CLI 0 signifie qu'au moins un joueur a une note ; les analyses partielles utilisables sont explicitement marquées `partial`. `complete` exige des fenêtres pour chaque joueur de la liste, que tous les tirs éligibles soient notés, et qu'il n'y ait pas de contexte de tour manquant ou croisé. `partial` conserve des notes utilisables tout en exposant ces lacunes ; `insufficient_data` signifie qu'aucun joueur ne peut être noté. La sortie 2 signifie une entrée invalide, un modèle manquant ou incompatibles, une erreur de parsing ou de sortie ou l'absence de fenêtre notée. Les rapports sans données conservent des notes nulles au lieu de zéros artificiels.

<a id="reproducible-validation"></a>
## Validation reproduisable

Le [README Quick Start](../README.fr.md#quick-start) couvre l'installation en Python 3.11+ et une analyse de base. Le protocole d'acceptation détaillé est conservé ici ; le README retient les onze éléments de la liste M6.

L'inférence nécessite un ensemble fiable M5 `.joblib` et des métadonnées adjacentes `.json` ; les données du modèle et les démonstrations sont ignorées par Git et ne sont pas incluses dans une clonage frais. L'installation et les tests automatisés n'ont pas besoin de cela. Si un ensemble doit être construit séparément, la commande historique ci-dessous entraîne M5 à partir de l'ensemble existant `demo_analyzer/data/processed/supervised_dataset.csv` ; elle n'est pas partie de l'inférence :

```powershell
Set-Location demo_analyzer
..\.venv\Scripts\python.exe scripts/save_supervised_model.py
Set-Location ..
```

Commandes exécutées à partir de la racine du dépôt :

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps --disable-pip-version-check -e .
.\.venv\Scripts\python.exe -m pytest -q --tb=short
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q demo_analyzer/src demo_analyzer/scripts demo_analyzer/tests
.\.venv\Scripts\python.exe -c "import cs2guard_demo.analysis, cs2guard_demo.cli, cs2guard_demo.parser, cs2guard_demo.dataset, cs2guard_demo.detection, cs2guard_demo.supervised, cs2guard_demo.visualization; print('Imports: OK')"
.\.venv\Scripts\cs2guard.exe analyze --help
.\.venv\Scripts\python.exe -m cs2guard_demo --help
.\.venv\Scripts\cs2guard.exe analyze demo_analyzer/data/raw/train_sources/demo/test.dem --model demo_analyzer/models/supervised/random_forest_v1.joblib --output demo_analyzer/data/processed/m6_validation
git diff --check
```

Séquence d'audit initiale : **274 passées, 0 échouées, 0 sautées**. `pip check`, compilation de la syntaxe, imports canoniques et aide CLI sont passés. Tous les **75 fichiers Python** sont analysés ; **26 modules d'implémentation non-espace** et **20 scripts** sont importés avec succès. Aucun outil de vérification de style ou de type n'est configuré. Les scripts d'entraînement historiques ont été importés et couverts par les tests de bibliothèque, sans être exécutés sur l'ensemble complet de données. Ils conservent leur répertoire de travail attendu `demo_analyzer/` ainsi que leurs prérequis de données. Les chemins d'aide et de reprise du constructeur multi-source sont testés, sans surécrire les ensembles de recherche.

<a id="initial-acceptance-protocol"></a>
### Protocole d'acceptation initial

Les vérifications automatisées ont couvert les onze critères du README avec un parseur contrôlé, le code réel M1–M5, un classificateur persisté de petite taille et une sortie réelle au format PNG. Cinq joueurs de test ont été présents ; les scores indisponibles étaient nuls. Les scores des matchs et les moyennes des joueurs étaient conformes, les cas invalides de modèle ou d'entrée ont été rejetés, et les nuls ou les entrées réorganisées ont conservé le classement. Les limites des tours, les associations inconnues, les indicateurs de limite et la limite d'affichage à trois fenêtres correspondaient aux matchs.

La base de référence RF/arbre, avec les contributions signées, a reconstruit les scores des fenêtres/joueurs dans `1e-12`. Les données JSON enregistrées correspondent aux données retournées ; les liens d'images Markdown sont résolus, les PNG sont non constants et les unités physiques ainsi que les indicateurs d'indisponibilité restent explicites. L'aide CLI et le scoring ont réussi ; les entrées invalides, les modèles manquants et les fenêtres sans score ont sorti avec le code 2. Ces vérifications restent dans `test_analysis.py` et `test_aim_visualization.py` ; les commandes ci-dessus les exécutent avec l'ensemble complet.

La première exécution réelle utilisait uniquement des références de direction des tirs. Les résultats enregistrés ci-dessous conservent cette preuve ; les graphiques observés-victime ont été démontrés lors de l'audit de robustesse suivant.

<a id="real-local-demo"></a>
### Démonstration locale réelle

La commande installée `cs2guard` fonctionne effectivement sur `demo_analyzer/data/raw/train_sources/demo/test.dem` (312 377 735 octets) avec le bundle M5 RF inchangé. L'analyse est répétée pendant l'implémentation ; les moyennes des joueurs affichées et le classement sont conformes à six décimales. L'état du rapport final est **partiel** car certains tours manquent de contexte complet ou traversent une frontière ; tous les dix joueurs ont toutefois des scores.

|Élément enregistré|Résultat|
|---|---:|
|Joueurs / joueurs notés| 10 / 10 |
|Lignes de télémétrie normalisées| 1,624,992 |
|Événements normalisés| 2,966 |
|Fenêtres de 32 ticks notées| 2,272 |
|Tours complets| 21 |
|Tirs non notés et éligibles| 0 |
|Fenêtres sans association de tour complet| 42 |
|Fenêtres traversant une frontière de tour| 36 |
|Graphiques de revue PNG enregistrés| 30 |
|Moyenne du joueur le plus élevé / le plus bas| 0.263435 / 0.237090 |

Chaque score de joueur enregistré est comparé à la moyenne des scores de ses fenêtres enregistrées, avec une tolérance `1e-12`. La valeur de base à la racine, additionnée aux contributions signées des chemins, est aussi comparée aux probabilités des 2 272 fenêtres du RF ; erreur maximale `4.44e-16`. Les contributions JSON enregistrées reconstruisent les 2 282 scores de fenêtres et de joueurs, avec une erreur maximale de `5.55e-16`. Le classement, les identifiants canoniques des joueurs, les limites de fenêtres de 32 ticks, les limites des manches valides et les associations des événements aux acteurs, armes et manches sont contrôlés dans le JSON généré. Les 30 PNG existent, ont des dimensions positives et des pixels non constants. Un graphique réel est inspecté visuellement : sa trace, son axe des ticks, ses unités en degrés, son repère de tir et sa référence de direction du tir sont lisibles. Toutes les séquences réelles sélectionnées utilisent le repli sur la direction du tir. Le suivi de la victime observée est vérifié dans le cas contrôlé de bout en bout, mais n’est pas démontré sur ces candidats réels. Le JSON et le Markdown restent en local sous `demo_analyzer/data/processed/m6_validation/`, exclus de Git comme sorties générées. Le cas CLI avec démo absente est aussi exécuté et se termine avec le code 2 et une erreur explicite.

<a id="temporary-directory-correction"></a>
### Correction du répertoire temporaire

Les dossiers `.pytest_tmp*` proviennent des commandes explicites de cette tâche (`--basetemp=demo_analyzer/.pytest_tmp*`) et de tests manuels plus anciens. `pytest.ini`, `pyproject.toml` et tous les scripts du dépôt ne contiennent pas de telles surcharges. Les cas d'essai utilisent le stockage natif `tmp_path`. Toutes les commandes de test suivantes omettent `--basetemp` et utilisent le stockage temporaire natif de pytest (`E:\Temp` sur cet hôte). Le répertoire temporaire remapé du sandbox est inaccessible pour le nettoyage de pytest ; l'accès autorisé à l'exécution résout ce problème d'environnement sans modifier les cas d'essai ni les fonctionnalités du projet. Après avoir confirmé que les sessions de test de la tâche étaient terminées et avoir vérifié les lignes de commande réelles des processus Python/pytest, dix dossiers `.pytest_tmp*` sont supprimés exclusivement dans les chemins vérifiés du dépôt. Aucune autre donnée n'est supprimée. `.gitignore` protège également `.pytest_tmp*/` contre une traçabilité accidentelle ; ce n'est qu'un mécanisme de garde, pas la solution. Après une exécution complète de pytest natif, une vérification du répertoire est effectuée : **aucun dossier `.pytest_tmp*` au niveau racine du dépôt ou sous `demo_analyzer/`**.

<a id="initial-audit-limits"></a>
## Limites de l'audit initial

La chaîne logicielle est mise en œuvre et testée ; M6 n'est pas **entièrement validée**. Les probabilités de comportement calibrées et un seuil opérationnel validé n'existent pas dans M1–M5 et ne sont pas inventés ici. Les contributions des chemins RF/arbre local reconstruisent les prédictions, mais ne permettent ni de définir une importance causale ni de soutenir des familles d'estimateurs autres que les arbres. Des étiquettes indépendantes et une transfert validé CS2CD-vers-démonstration étaient absentes. Les métadonnées du modèle omettent les détails d'extraction/versions, donc la compatibilité structurelle ne permet pas de valider scientifiquement. Le suivi ciblé de la cible et le contexte complet associé restent partiellement démontrés comme décrit ci-dessus. Cet audit initial n'a pas répété la formation sur l'ensemble de données, ni les comparaisons avec des modèles réservés, ni évalué un serveur en temps réel. Aucune mise à jour ou déploiement n'a été effectuée.

<a id="m6--targeted-robustness-validation-2026-10-14"></a>
# M6 - Validation de robustesse ciblée (14 octobre 2026)

Cet examen de suivi valide l'implémentation existante, en conservant tous les édits locaux précédents et les sorties originales `m6_validation/`. Les preuves générées se trouvent sous `demo_analyzer/data/processed/m6_robustness_20261014/` : `reference/`, trois analyses `before/`, trois analyses `after/`, une analyse répétée `test.dem` dans `repeat/`, et des vérifications indépendantes dans `audit/<demo stem>/`. Chaque audit inclut `validation.json`, `raw_round_events.json`, ainsi que des inventaires CSV/JSON de chaque fenêtre non attribuée et de chaque fenêtre croisant. `corrections.diff` isole les modifications de cette tâche dans trois fichiers d'implémentation provenant de l'implémentation existante.

<a id="a-diagnosis"></a>
## A. Diagnostique

Pour `test.dem`, la condition exacte `partial` est 42 fenêtres sans association terminée et 36 fenêtres franchissant une frontière. Tous les dix joueurs sont notés ; les 2 272 tirs éligibles génèrent des fenêtres complètes et finies. Aucun tir éligible ni ligne de fonctionnalité générée n'est omis. L'absence de suivi et les stimuli de visibilité manquants n'ont pas de portée sur cet état.

Les 42 tirs non attribués se situent strictement après un `round_end` et avant le prochain `round_start`. Cette lacune est confirmée de manière indépendante par les événements analysés `round_officially_ended`, qui correspondent à l'heure de début suivante ; des événements officiels de fin dupliqués sont présents dans la sortie brute du parser. Trente-six fenêtres contiennent les ticks finaux de la ronde terminée suivis des ticks post-résultat ; six fenêtres se trouvent entièrement dans une transition. Aucune fenêtre ne contient deux rondes actives simultanées. Les 36 fenêtres franchissant la frontière constituent un sous-ensemble des 42, et non un ensemble supplémentaire. Les tirs se produisent entre 3 et 434 ticks après la fin précédente. Aucun événement de début ou de fin manquant n'explique ces 42 cas.

Les six fenêtres entièrement dans une transition sont : LuchoG au tick 27003 ; Syzel aux ticks 107079, 107085 et 130735 ; et squeezie aux ticks 26993 et 27011. L'inventaire CSV enregistre pour chaque joueur les identifiants canoniques et d'origine, le nom, les limites de la fenêtre, le tick du tir, les secondes reconstructibles (`tick / 64`, pas des horloges murales), la ronde précédente/fin, la ronde suivante/début et le score. Les identifiants des rondes terminées sont normalisés séquentiellement après `begin_new_match` ; les valeurs brutes des événements `round` diffèrent entre les événements de début et de fin et ne sont pas substituées dans ces identifiants. L'intervalle premier conservé commence à la dernière `begin_new_match`, au tick 5787, immédiatement après le premier début en cours au tick 5786.

Le contrat de fenêtre terminée est inclusif `[start_tick, end_tick]`. Un tir post-résultat n'a pas d'association terminée active selon ce contrat. Son contexte de ronde précédente et suivante est enregistré dans l'inventaire diagnostique ; `round_number` reste nul plutôt que d'agrandir silencieusement le contrat. Tous les 42 scores restent dans la moyenne arithmétique de leur joueur.

Les fenêtres historiques M3 contiennent 32 ticks consécutifs uniques des joueurs se terminant au tir (31 intervalles de ticks, 0,484375 seconde à la fréquence historique de 64 Hz). Elles ne filtrent pas par ronde. Les 36 fenêtres franchissant la fin suivent cette définition et incluent des échantillons d'orientation post-résultat. Le pas angulaire maximal exactement au moment de la fin est de 3,390503569 degrés ; le pas maximal de position est de 3,359422697 unités de jeu. Ces mesures ne montrent pas de discontinuités de spawn ni de fonctionnalités corrompues. Modifier cette population modifierait la définition d'entrée M5 et nécessiterait une étude de compatibilité/évaluation séparée ; aucune telle modification ou re-entraînement n'est justifiée ici.

Deux défauts affectent les sorties réelles :

* `weapon_fire` utilise des noms comme `weapon_ak47`, tandis que `player_hurt`/`player_death` utilisent `ak47`. La comparaison exacte exclut chaque contact/élimination dans tous les intervalles notés, y compris tous les graphiques sélectionnés. En supprimant uniquement le préfixe optionnel lors de la comparaison M6, les contacts observés sont restaurés sans modifier les armes stockées ni les caractéristiques M3/M5.
* L'impression des noms de joueurs en Unicode vers la sortie standard Windows `cp1252` déclenche `UnicodeEncodeError` après que les rapports aient été écrits. Les deux démos réelles supplémentaires quittent initialement avec le code d'erreur 1 pour cette raison. Les caractères non encodables dans la console utilisent désormais des échappements par slash ; JSON/Markdown conservent les identités complètes en Unicode.

Les régressions synthétiques démontrent également une limite non détectée lorsqu'aucun des deux extrémités de l'intervalle n'est connu, mais qu'un tour complet se situe à l'intérieur ; l'absence d'un `round_start` réutilise le début d'un tour précédent, créant des intervalles superposés ; et les événements de fin dupliqués déplacent les numéros normalisés des tours. La détection des limites vérifie désormais les limites réelles des intervalles. L'analyse élimine les ticks de fin dupliqués et exige qu'un début suivant soit strictement situé après la fin précédente. Ces cas limites dans le parser ne modifient pas les intervalles complétés des trois démos réelles.

<a id="b-changes"></a>
## B. Modifications

* `analysis.py` : comparaison optionnelle du préfixe d'arme, détection des limites, raisons explicites de l'absence de suivi et limitations de tours comptés dans JSON/Markdown. Aucune modification de score, de fonctionnalité, de sélection de candidats ou de définition d'intervalle.
* `cli.py` : encodage sécurisé des noms de joueurs dans la console.
* `parser/demo_parser.py` : correction des paires de tours en deux lignes décrite ci-dessus.
* `test_analysis.py` et `test_demo_parser.py` : 18 cas synthétiques supplémentaires. Deux tests existants gagnent des affirmations pour le reporting et les entrées de type arbre fini extrême.
* README et cette mémoire : enregistrer les nouvelles preuves tout en conservant les résultats de validation historiques.
* `.gitignore` : exclure les rapports, images, journaux et captures de référence générés par cette validation.

L'agrégation positionnelle existante de M5, le classement avec un critère de rupture d'identité, la sélection de la colonne de classe, l'ordre des fonctionnalités, le rejet des valeurs finies, la navigation dans les arbres de type float32 et les étiquettes descriptives/scientifiques fonctionnent déjà correctement.

<a id="c-tests-and-environment"></a>
## C. Tests et environnement

Base : **274 cas passés en 22,07 s**. Six cas de régression échouent par rapport à l'implémentation originale enregistrée : sortie standard en Unicode, les deux directions du préfixe d'arme, une limite interne avec des extrémités inconnues, un début de tour manquant et une fin dupliquée. Après correction, le run ciblé M1/M2/M6 passe **76 tests en 20,68 s** ; l'ensemble complet M1–M6 passe **292 tests en 22,59 s**, sans échec ni saut. Les runs ciblés incluent tous les tests d'intégration en fin de chaîne M6. Les nouveaux cas couvrent également les bornes inclusives des événements, les fenêtres sans contexte de tour, et les données de témoignage manquantes, isolées, ou dupliquées. Les tests existants sur les égalités, l'ordre d'entrée, l'identité, l'agrégation positionnelle, les modèles invalides et les fixtures déterministes restent intacts.

La première exécution dans l'environnement de sandbox donne 207 cas passés / 67 erreurs de fixture car pytest ne peut pas utiliser le répertoire temporaire rémappé. Définir uniquement pour ce processus les variables d’environnement `TEMP` et `TMP` sur le répertoire système natif `E:\Temp` résout ce problème sans modifier les fixtures ni la configuration de pytest. Aucun répertoire `.pytest_tmp*` n'est créé. Le lanceur Python affiche également `Failed to find real location of E:\Python\python.exe` sur stderr dans ce contexte d'exécution, y compris pour les commandes réussies ; les trois codes de sortie CLI corrigés restent cependant égaux à 0. Aucune exception de parseur n'est récupérée ni masquée.

Tous les 36 modules de paquets importables sont importés avec succès. Compilation syntaxique, `pip check`, aide CLI installée/module, sortie CLI invalide 2 et `git diff --check` passent. Aucune commande de vérification ou de type n'est configurée. Aucune installation de dépendance, apprentissage du modèle, téléchargement, commit ou push n'occure.

<a id="d-real-analyses"></a>
## D. Analyse réelle

Les trois fichiers `.dem` disponibles localement sont analysés avant et après correction. Aucun n'est téléchargé ni modifié.

|Démo|Joueurs détectés / notés|Fenêtres générées / notées|Rondes complétées|Aucune ronde|Croisement|Scores des joueurs min / moyen / max|Sélectionnés / PNG|Graphiques de suivi|CLI après|Secondes avant / après|
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| `test.dem` | 10 / 10 | 2272 / 2272 | 21 | 42 | 36 | 0.237090 / 0.251237 / 0.263435 | 30 / 30 | 4 | 0 | 143.85 / 37.75 |
| `2026-09-01_19-31-10_17_de_inferno_team_Kay_vs_team_YY.dem` | 10 / 11 | 3104 / 3104 | 23 | 129 | 42 | 0.235112 / 0.250149 / 0.259392 | 30 / 30 | 7 | 0 | 52.10 / 50.56 |
| `2026-09-02_19-03-20_18_de_ancient_team_alxska-_vs_team_Palmoleeve.dem` | 10 / 10 | 2800 / 2800 | 24 | 106 | 58 | 0.240015 / 0.249423 / 0.261043 | 30 / 30 | 9 | 0 | 60.58 / 40.06 |

Tout état reste `partial` ; les deux formats JSON et Markdown sont présents et cohérents. Tous les tirs normalisés admissibles ont des fenêtres notées ; aucun score n'est NaN ou infini. Inferno conserve l'identifiant Steam `76561198125674008` avec des données de suivi mais n'a aucun tir admissible et un score nul. Les fenêtres non attribuées d'Inferno comprennent 38 entre les rondes complétées, quatre après la dernière ronde terminée mais avant le début suivant, et 87 dans une ronde finale commençant au tick 188682 sans événement de fin. Les 106 fenêtres non attribuées d'Ancient se situent entre les intervalles complétés. Chaque croisement réel est une frontière de fin ; aucun vrai intervalle ne traverse le début d'une ronde suivante. Les temps incluent des travaux de validation simultanés et ne constituent pas une mesure de performance.

<a id="e-independent-beforeafter-checks"></a>
## E. Vérifications indépendantes avant/après

Les 8 176 fenêtres sont reconstruites à partir des données brutes normalisées et des événements. Leurs six valeurs de caractéristiques correspondent exactement aux rapports enregistrés. Le modèle RF persisté prédit à nouveau ces entrées brutes : la différence maximale par rapport aux scores rapportés est `2.78e-16` ; les moyennes indépendamment calculées des joueurs diffèrent au plus de `2.78e-17`. La base de référence plus les contributions par chemin de caractéristique reconstruit chaque score fenêtre/joueur dans une marge de `6.11e-16`. Aucune différence avant/après inattendue n'excède `1e-12` : les identités, les limites des fenêtres, les intervalles complétés, les scores, les classements, les identifiants des candidats et les contributions sont conservés.

Pour `test.dem`, le lien passe de 2 272 tirs uniquement à 2 272 tirs plus 320 associations de tir et 148 associations de meurtre. Dans toutes les fenêtres, 347 ont un victime observée liée avec suffisamment de données de suivi concurrentes ; quatre se trouvent dans les trois sélections par joueur. Les autres 1 925 fenêtres, y compris 26 séquences sélectionnées, n'ont aucune interaction satisfaisant les conditions existantes d'agresseur/arme/ronde/deux-ticks. Inferno a 515 fenêtres de suivi disponibles (7 sélectionnées) ; Ancient a 507 (9 sélectionnées). Aucun cible réelle liée n'a insuffisamment de données de suivi concurrentes, et aucun victime ultérieure n'est exclue par le choix de première interaction dans ces exécutions. Les cas synthétiques de victime manquante ou dupliquée conservent un fallback explicite sur la direction du tir.

Les données transmises à M2 sont vérifiées pour chacun des 90 graphiques finaux : acteur, cible, ticks d'échantillon, bornes, titre et géométrie angulaire. La géométrie flottante indépendante float64 diffère de au plus `1.12e-6` degrés par rapport au calcul actuel mixte float32/float64 ; aucune formule M2 n'est modifiée. Tous les graphiques sont de taille 1100×600 RGBA, avec des données non constantes, des liens d'image corrects et des valeurs finies. Quatre graphiques représentatifs sont visuellement inspectés dans les trois démonstrations, incluant les références observées-victime et direction de tir. Seulement les graphiques de suivi attendus 4/7/9 diffèrent de la base. La réaction reste inaccessibles sans stimuli visibles observés. Le suivi utilise la géométrie de position corporelle, sans visibilité, hauteur oculaire ou reconstruction de hitbox ; un impact survient juste après le tir peut légitimement se trouver en dehors du graphique précédent au tir.

|Joueur `test.dem`, rang inchangé|Windows|Moyenne avant / après (six décimales)|Aucune itération / croisement|Contribution additive des fenêtres non attribuées / croisées à la moyenne du joueur|
|---|---:|---|---|---|
|1 MDMiro| 159 | 0.263435 / 0.263435 | 2 / 2 | 0.002642 / 0.002642 |
|2 KeaZy| 120 | 0.260880 / 0.260880 | 2 / 2 | 0.004495 / 0.004495 |
|3 LuchoG| 188 | 0.258100 / 0.258100 | 9 / 8 | 0.013038 / 0.011063 |
|4 YEL7OWORE| 375 | 0.256915 / 0.256915 | 2 / 2 | 0.001172 / 0.001172 |
|5 samu777-| 258 | 0.256882 / 0.256882 | 6 / 6 | 0.005533 / 0.005533 |
|6 NthraX| 250 | 0.252927 / 0.252927 | 11 / 11 | 0.012024 / 0.012024 |
|7 -s4ndor| 286 | 0.244495 / 0.244495 | 0 / 0 | 0 / 0 |
|8 squeezie| 225 | 0.244215 / 0.244215 | 4 / 2 | 0.004866 / 0.002441 |
|9 Syzel| 139 | 0.237428 / 0.237428 | 6 / 3 | 0.009635 / 0.004724 |
|10 Draw0x| 272 | 0.237090 / 0.237090 | 0 / 0 | 0 / 0 |

Une contribution additive est la somme des scores du sous-ensemble divisée par le nombre total de fenêtres du joueur, et non la moyenne du sous-ensemble. Les sous-ensembles superposés ne doivent pas être ajoutés ensemble.

L'exécution répétée de l'installation CLI de `test.dem` se termine en 33,63 s. Une comparaison approfondie de chaque champ de rapport ne révèle aucune différence sémantique à la tolérance absolue `1e-12` ; tous les 30 PNG sont identiques au niveau des octets. Le JSON n'est pas identique au niveau des octets : la sommation parallèle des flottants RF (`n_jobs=-1`) modifie les scores des fenêtres de au plus `2.22e-16`. Aucun champ de rapport n'est omis dans cette comparaison répétée, et le classement reste inchangé. La reproduction binaire exacte des scores flottants n'est pas affirmée.

Les manifestes SHA-256 sont identiques avant et après pour les trois démonstrations sources, les métadonnées du modèle et les octets du modèle. L'empreinte du modèle RF reste `322ea64dddf12164824a5269371429ae87f714f7a2c0bf89c2eb10185cc09d11`.

<a id="f-manual-reproduction"></a>
## F. Réproduction manuelle

À partir du répertoire racine, utilisez l'environnement existant et le répertoire temporaire natif du système :

```powershell
$env:TEMP = 'E:\Temp'
$env:TMP = 'E:\Temp'
.\.venv\Scripts\python.exe -m pytest -q demo_analyzer/tests/test_analysis.py demo_analyzer/tests/test_demo_parser.py demo_analyzer/tests/test_aim_visualization.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\cs2guard.exe analyze --help
.\.venv\Scripts\python.exe -m cs2guard_demo --help

$model = '.\demo_analyzer\models\supervised\random_forest_v1.joblib'
$modelHashBefore = (Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash
$runRoot = Join-Path '.\demo_analyzer\data\processed' ('m6_manual_' + [guid]::NewGuid().ToString('N'))
Get-ChildItem '.\demo_analyzer\data\raw\train_sources\demo' -Filter '*.dem' | ForEach-Object {
    $out = Join-Path $runRoot $_.BaseName
    .\.venv\Scripts\cs2guard.exe analyze $_.FullName --model $model --output $out
    if ($LASTEXITCODE -ne 0) { throw "Analysis failed: $($_.Name)" }
    $report = Get-Content -LiteralPath (Join-Path $out 'report.json') -Raw -Encoding utf8 | ConvertFrom-Json
    $report.summary
    $report.players | Format-Table rank,player_id,score,window_count
    $report.review_events.visualization | Format-Table path,reference,sample_count
    if (-not (Test-Path -LiteralPath (Join-Path $out 'report.md'))) { throw 'Missing Markdown report' }
}
if ((Get-FileHash -LiteralPath $model -Algorithm SHA256).Hash -ne $modelHashBefore) { throw 'Model changed' }
git diff --check
git status --short
Get-ChildItem -Force -Directory -Path '.', '.\demo_analyzer' -Filter '.pytest_tmp*'
```

Enregistré le 2026-10-14 : 76 cibles / 292 tests totaux, sortie CLI à 0 pour chaque démonstration locale, comptes et scores comme ci-dessus, hachage du modèle inchangé et aucune répertoire `.pytest_tmp*`. L'analyse répétée compare tous les champs JSON avec une tolérance absolue numérique `1e-12` ; les autres champs et tous les octets des PNG sont identiques.

<a id="g-validation-status-and-limits"></a>
## G. Statut de validation et limites

* Validité technique M6 : validée pour le contrat d'inférence existant et les erreurs testées.
* Intégrité des données et des associations : partielle. Les transitions connues et la ronde incomplète restent explicitement en dehors de la couverture des rondes terminées. Les contacts proches sont du contexte temporel, pas de l'attribution causale du tir.
* Robustesse sur plusieurs démonstrations : validée sur les trois démonstrations locales disponibles, pas sur des formats de enregistrement arbitraires ou des populations arbitraires.
* Validité du score scientifique sur des démonstrations ordinaires : non validée. Les étiquettes indépendantes, l'évaluation de décalage de domaine, les données d'ajustement appropriées et les métadonnées de version d'extraction manquent. Aucune nouvelle seuil opérationnel, probabilité de fraude, verdict ou retraining n'est introduite. L'élimination de `weapon_` ne permet pas d'inférer des alias non documentés tels que les différences entre armes silencieuses dans les événements de dommages.

<a id="m6--presumed-legitimate-external-evaluation"></a>
# M6 - Évaluation externe supposée légitime

`cs2guard_demo.validation` évalue des démonstrations locales sous `demo_analyzer/data/raw/held_out/legitimate/` avec le bundle RF existant et gelé. Il appelle directement M6, conservant les scores, les caractéristiques, les identités des joueurs, les compteurs de qualité et les contributions des chemins RF. L'argument facultatif `review_plots=False` supprime les images PNG de visée par joueur pour cette étude ; les appels ordinaires à M6 conservent leurs graphiques existants. Aucune modification n'est apportée aux contrats de caractéristique, de fenêtre, de notation, de formation ou d'ajustement.

Le protocole est enregistré **avant** l'inférence externe : hachage SHA-256 du modèle/métadonnées, hachages exacts des sources et un ZIP de source, état Git, versions de Python/deploiement, paramètres 32-tick/64-Hz, caractéristiques ordonnées, agrégation par moyenne arithmétique, étiquettes, paramètres de bootstrap et le seuil historique de grille descriptive **0.10–0.90**. Le comparateur est `>=`, comme dans M5 ; **0.50 n'est pas un seuil opérationnel**. Les sorties sont disponibles sous `demo_analyzer/data/processed/validation_legitimate/` ignoré, avec des tentatives distinctes de correspondance par adresse de contenu et des dossiers d'étude séparés. La répétition de la commande réutilise les rapports uniquement après réception/hachage, identités, valeurs finies, compteurs et vérifications de moyenne par joueur. Les tentatives invalides et les études précédentes restent disponibles.

Les étiquettes par défaut sont `presumed_legitimate`, basées uniquement sur la déclaration de l'utilisateur. Un JSON facultatif `--manifest` permet de mapper des chemins relatifs des démonstrations vers la provenance et les surcharges par joueur. Les joueurs inconnus restent dans les sorties descriptives et sont exclus des dénominateurs des indicateurs. Une étiquette confirmée nécessite une surcharge individuelle avec preuve :

```json
{
  "match.dem": {
    "status": "presumed_legitimate",
    "evidence": "User-supplied recording; no independent adjudication",
    "players": {
      "demo:76561198000000000": {"status": "unknown"},
      "demo:76561198000000001": {
        "status": "confirmed_legitimate",
        "evidence": "Describe the individual verification here"
      }
    }
  }
}
```

L'unité principale est le **match joueur**. Les résumés descriptifs conservent les valeurs manquantes, les écarts-types d'échantillon et les percentiles d'extrémités exploratoires. Les intervalles de bootstrap 95 % à semence fixe rééchantillonnent les matches, en préservant la dépendance intra-match ; une seconde analyse rééchantillonne des matches connectés partageant des identités persistantes. Lorsqu'il y a moins de deux composantes indépendantes, cet intervalle n'est pas disponible. Les intervalles de Wilson sont des références explicites de sensibilité IID, pas des bornes corrigées. Les intervalles de bootstrap pour les indicateurs nuls ou totaux sont dégénérés et ne peuvent établir une FPR de population. La métrique est `presumed_legitimate_flag_rate`, pas une FPR confirmée.

L'ancienne `supervised_dataset.csv` fournit des distributions légitimes des caractéristiques CS2CD, y compris une référence complète séparément rapportée et le découpage historique exact de M5. Les scores du modèle conservés testent la référence sans ajustement. Les caractéristiques et les scores de fenêtre, ainsi que les moyennes par match joueur équivalentes, sont rapportés séparément. Aucune base historique n'est régénérée ou téléchargée si l'entrée est absente. Les doublons exacts natifs des démonstrations sont exclus ; les surcharges de nom/fichier avec les trois rapports historiques de M6 sont enregistrées. L'anonymisation CS2CD et les identifiants de séances indisponibles empêchent encore des garanties d'indépendance complètes.

À partir de la racine du dépôt, exécutez ou reprenez l'étude complète avec la même commande :

```powershell
.\.venv\Scripts\python.exe -m cs2guard_demo.validation
```

Lisez l'étude la plus récente et ouvrez son rapport/figures :

```powershell
$study = (Get-Content '.\demo_analyzer\data\processed\validation_legitimate\latest.json' -Raw -Encoding utf8 | ConvertFrom-Json).run_directory
$statistics = Get-Content (Join-Path $study 'statistics.json') -Raw -Encoding utf8 | ConvertFrom-Json
$statistics.counts
$statistics.eligible_player_match_scores
$statistics.flag_rates | Select-Object threshold,evaluable_player_matches,flagged_player_matches,presumed_legitimate_flag_rate
Invoke-Item (Join-Path $study 'report.md')
Get-ChildItem -LiteralPath $study -Filter '*.png' | Invoke-Item
.\.venv\Scripts\python.exe -m pytest -q
```

Cette étude unilatérale négative a mesuré les distributions de scores et les taux d'indicateurs descriptifs. Elle ne peut pas mesurer le rappel externe, l'ROC-AUC ou le PR-AUC, valider la calibration, identifier les tricheurs ou démontrer la généralisation.

<a id="real-external-study--2026-10-14"></a>
## Étude externe réelle - 2026-10-14

Tous les **neuf** nouveaux démonstrations disponibles ont été analysés : **90 observations de correspondance joueur**, **57 identités observables Steam**, **29 010 fenêtres évaluées**, aucune démonstration échouée ou exclue et aucun joueur non évalué. Tous les 90 étiquettes sont considérés comme légitimes selon la déclaration de l'utilisateur ; aucune n'est confirmée indépendamment ni marquée comme inconnue. Tous les rapports sont `partial` : **685 fenêtres manquent de contexte de tour complet** et **415 franchissent une frontière de tour**, conservées selon le contrat d'extraction historique. Les joueurs évalués ont de 114 à 858 fenêtres (médiane 304,5).

La moyenne du score de correspondance est de **0,249250**, la médiane de **0,244984**, l'écart-type de l'échantillon de **0,014424**, la valeur minimale/maximale de **0,225987/0,295459**, les quartiles Q25/Q75 de **0,238631/0,255644** et les percentiles P90/P95/P99 de **0,267843/0,279872/0,289260**. Les percentiles des queues restent exploratoires avec 90 observations. Les moyennes de correspondance varient de **0,242817 à 0,256175**. Dix identités se répètent dans plusieurs correspondances ; leurs valeurs de score observées au sein du joueur varient de **0,001584 à 0,041159**, avec des preuves descriptives uniquement.

L'intervalle de confiance de 95 % basé sur le bootstrap des correspondances est de **[0,246899 ; 0,251793]**, conditionnel à l'hypothèse que neuf correspondances sont indépendantes. **Les neuf correspondances forment une composante connectée unique grâce à des joueurs répétés**, incluant une identité présente dans chaque correspondance. Le bootstrap conservant la dépendance n'a donc **aucune intervalle estimable**. L'intervalle de bootstrap étroit ne doit pas être interprété comme une précision fiable de la population.

À des seuils fixes de **0,10 et 0,20**, les indicateurs sont de **90/90 correspondances joueurs et 9/9 correspondances**. À **0,30 à 0,90**, y compris 0,50, les indicateurs sont de **0/90 et 0/9**. Aucune exclusion de label ou de données n'est incluse dans ces dénominateurs. Les intervalles de bootstrap à zéro indicateur sont dégénérés. À zéro indicateur, les références de sensibilité de Wilson IID sont de **[0 ; 4,09 %]** pour 90 observations et de **[0 ; 29,91 %]** pour neuf correspondances ; aucune n'ajuste la dépendance réelle partagée entre joueurs. Le fait d'observer zéro indicateur ne permet ni de déterminer une fausse positivité nulle ni de mesurer la sensibilité aux tricheurs.

Aucune duplication exacte n'apparaît parmi les neuf fichiers ni par rapport aux trois démonstrations historiques M6. **Six identités Steam se retrouvent dans les rapports techniques historiques**. Ces enregistrements sont des correspondances nouvelles, pas un groupe de joueurs entièrement nouveau ; les incertitudes liées au nom de fichier/séance et à l'anonymisation CS2CD persistent. La découverte de M3 est limitée à `train_sources` ; cette évaluation s'inscrit ailleurs et ne fait jamais appel à la formation. L'entrée existante de M5 contient **397 487 fenêtres CS2CD uniquement** et aucune superposition observable avec des matchs ou identifiants de joueurs externes ; l'anonymisation limite encore les vérifications sur des personnes réelles.

La comparaison CS2CD utilise **282 022 fenêtres légitimes / 1 801 correspondances joueurs** pour la référence descriptive complète des caractéristiques, et **66 588 fenêtres légitimes / 402 correspondances joueurs sur 64 matchs historiques** pour les comparaisons de score frozen-RF. Les décalages de médiane des caractéristiques de fenêtre sont faibles par rapport à l'IQR de référence (environ **−0,099 à +0,010 IQR**); les moyennes pondérées par équivalence des correspondances joueurs donnent **−0,060 à +0,040 IQR**. Les scores des joueurs externes sont plus bas et moins dispersés : moyenne/médiane **0,249250 / 0,244984**, contre **0,284594 / 0,274929** pour les observations de test CS2CD légitimes. Des médianes similaires ne signifient pas des queues identiques : la vitesse maximale P99 de fenêtre est **829,28 versus 692,76 degrés/s**, et l'écart-type de vitesse P99 est **231,30 versus 191,97 degrés/s**. Ces différences concernent des distributions descriptives, pas de tests de signification, d'améliorations opérationnelles ou de preuves de dégradation de détection.

Le score le plus élevé est **0,295459**, issu de 525 fenêtres avec **98,86 %** de couverture complète de tour (six fenêtres non attribuées et cinq fenêtres croisées). Cinq observations les plus élevées conservent les extrémités des caractéristiques et les contributions signées des chemins RF dans le rapport ; aucune n'est identifiée comme triche. Quatre figures PNG ont été inspectées visuellement.

Baseline automatisée : **292 cas passés** après correction du stockage temporaire inaccessible dans le sandbox avec les processus locaux `TEMP`/`TMP`. Ensemble complet après ajout des tests d'évaluation externes : **330 cas passés** (38 nouveaux cas) ; compilation syntaxique et `pip check` passés. Les tests couvrent les entrées vides/invalides, les doublons, les manifestes, les valeurs manquantes ou non finies, les taux/égalités, les resamplings regroupés, les comparaisons de référence, la conservation des rapports, la reprise, l'isolation des échecs et l'intégrité du modèle gelé. Les artefacts incluent des statistiques JSON/CSV, un rapport en Markdown, quatre figures, des preuves de source/protocole gelé et des rapports M6 par démonstration. Le modèle et les métadonnées restent inchangés ; aucune mise à jour ni poussée. La reprise réelle réutilise toutes les neuf rapports de match vérifiés et reproduit les statistiques exactement. Une relecture indépendante du modèle sur toutes les 29 010 lignes de caractéristiques sauvegardées donne une différence maximale de score de **2,776e-16** ; l'erreur maximale de reconstruction de la contribution RF était de **6,661e-16**, les deux valeurs étant inférieures à **1e-12**. Ce contrôle ne répète pas de manière indépendante la lecture de la source. La preuve finale se trouve dans `demo_analyzer/data/processed/validation_legitimate/run-0ae2814792ffd726/verification.json` ; `latest.json` pointe vers le rapport d'étude et les figures.

Classification de la preuve : traitement technique terminé ; les étiquettes de validation restent supposées ; la concentration des scores est observée sur cette échantillon ; les indicateurs de seuil sont mesurés de manière descriptive ; les différences de distribution sont observables ; la détection des tricheurs externes, la calibration et la généralisation restent **non validées**.

<a id="m6--cs2cd-evaluation-2026-10-15"></a>
# M6 - évaluation CS2CD (2026-10-15)

<a id="data-provenance-and-executed-protocol"></a>
## Données, provenance et protocole exécuté

L'inventaire JSON/Parquet local contient **795 matchs CS2CD**. L'existence de `supervised_dataset.csv` contient **397 487 fenêtres conservées provenant de 317 matchs**. Réapplication du partage historique regroupé (`test_size=0.20`, `random_state=42`) donne **253 matchs d'entraînement / 306 315 fenêtres / 2 471 correspondances joueurs notées** et **64 matchs de test / 91 172 fenêtres / 637 correspondances joueurs notés**. L'entraînement comporte 1 399 correspondances joueurs légitimes et 1 072 suspectes ; le test comporte **402 correspondances joueurs légitimes et 235 suspectes**, une prévalence positive de **36,8917 %**.

Les étiquettes brutes contiennent **640 correspondances joueur**. Trois joueurs légitimes n'ont pas de caractéristiques conservées et restent non évalués : `126.json / Player_7`, `178.json / Player_8` et `217.json / Player_5` n'ont pas d'événement brut `weapon_fire`. Les métriques de classification utilisent les 637 observations évaluées ; les classements excluent les trois joueurs non évalués, et Hit@k utilise les 64 correspondances contenant des suspects étiquetés. Les étiquettes et les identifiants canoniques par correspondance sont conformes entre les données historiques CSV conservées et les rosters bruts CS2CD. Les **478 paires JSON/Parquet** supplémentaires, disjointes des partitions historiques, ne contiennent pas de chevaliers annotés. Elles sont absentes des artefacts de développement inspectés ; cela ne prouve pas qu'ils n'ont jamais été vus. Les annotations des chevaliers manquantes deviennent `legitimate` dans l'adaptateur existant et ne permettent pas d'établir une légitimité indépendamment confirmée.

L'instance persistée **Random Forest v1** est utilisée sans ajustement, sans calibration ni apprentissage. Son SHA-256 est `322ea64dddf12164824a5269371429ae87f714f7a2c0bf89c2eb10185cc09d11`. Les six caractéristiques d'objectif ordonnées, le prétraitement, **32 ticks consécutifs de joueur / 64 Hz**, les notes moyennes par correspondance joueur et l'ordre décroissant des notes / ordre croissant des identifiants canoniques sont inchangés. L'inférence historique utilise les caractéristiques canoniques conservées ; les correspondances supplémentaires utilisent l'adaptateur existant CS2CD et le constructeur canonique. **Aucune analyse native `.dem` n'est évaluée.**

L'adaptateur projette maintenant les **16 colonnes consommées Parquet** au lieu de lire les 222 colonnes présentes dans une correspondance diagnostique. Sa normalisation, son extrait de caractéristiques et ses règles d'inférence restent inchangées. Sur cette correspondance réelle, les lectures complètes et projetées produisent **exactement 1 622 913 ticks canoniques identiques** et **5 443 lignes de caractéristiques identiques en termes de bytes** (`io_projection_validation.json`). Cela vérifie l'équivalence des données sur une seule correspondance ; les temps enregistrés lors d'une seule exécution ne constituent pas une référence. PyArrow, déjà installé pour le support Parquet, est maintenant une dépendance de runtime explicite.

Le bundle historique enregistre les compteurs et les métriques mais pas deempreinte de jeu, les listes de partitions ou la version d'extraction. La partition actuelle est reconstruite à partir du CSV actuel, dont le SHA-256 est `05ab29065646747b997908e7a17fd181cf0a73328db4a372f8c7d3e171f8b437`. Les compteurs correspondants et les métriques figées permettent de vérifier la cohérence ; ils ne fournissent pas de preuve cryptographique rétrospective de l'identité historique du jeu de données.

Les métriques de classification accordent une égale importance aux correspondances évaluées des joueurs. La précision moyenne utilise `average_precision_score`, pas l'aire du diagramme PR trapézoïdal. Hit@k accorde une égale importance aux correspondances contenant un suspect étiqueté évalué et mesure si au moins un joueur de ce type se classe parmi les premières positions k. Le seuil fixe **0,10–0,90** utilise `>=` ; il est descriptif et ne sélectionne aucun seuil opérationnel. **5 000 tirages de percentile avec semence fixe (42)** rééchantillonnent entièrement les correspondances, conservant la dépendance intra-correspondance. Les intervalles s'appuient sur le modèle figé et sur des correspondances indépendantes ; l'anonymisation empêche de mesurer une dépendance récurrente entre joueurs réels dans les correspondances. Les fenêtres ne sont jamais traitées comme des observations d'échantillonnage indépendantes.

<a id="historical-test-reproduction"></a>
## Réproduction de la base de test historique

|Métrique joueur-correspondance|Résultat|Intervalle de bootstrap de correspondance à 95 %|
|---|---:|---|
|ROC-AUC| 0.777898 | [0.729588, 0.819406] |
|Précision moyenne| 0.683983 | [0.599999, 0.757946] |
|Hit@1| 44/64 = 0.687500 | [0.562500, 0.796875] |
|Hit@3| 59/64 = 0.921875 | [0.843750, 0.984375] |

Tous les 64 matchs historiques contiennent des suspects marqués avec des étiquettes. ROC-AUC et AP reproduisent exactement les valeurs métadonnées **0,7778977453159733 / 0,6839833414991215**, précédemment arrondies à **0,7779 / 0,6840** dans M5. Les définitions du modèle, de la population, de la division regroupée, de l'agrégation et des métriques sont conformes. Ces matchs ont déjà été utilisés pour l'évaluation de M5 et l'analyse descriptive des seuils, donc il s'agit d'une **reproduction de l'expérience historique**, et non d'une estimation indépendante de la généralisation.

|Seuil|Précision|Rappel|F1|Taux de faux positifs|TN|FP|FN|TP|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.10 | 0.3689 | 1.0000 | 0.5390 | 1.0000 | 0 | 402 | 0 | 235 |
| 0.20 | 0.3689 | 1.0000 | 0.5390 | 1.0000 | 0 | 402 | 0 | 235 |
| 0.30 | 0.6234 | 0.6340 | 0.6287 | 0.2239 | 312 | 90 | 86 | 149 |
| 0.40 | 0.8033 | 0.2085 | 0.3311 | 0.0299 | 390 | 12 | 186 | 49 |
| 0.50 | 1.0000 | 0.0851 | 0.1569 | 0.0000 | 402 | 0 | 215 | 20 |
| 0.60 | 1.0000 | 0.0340 | 0.0658 | 0.0000 | 402 | 0 | 227 | 8 |
| 0.70 | 1.0000 | 0.0170 | 0.0335 | 0.0000 | 402 | 0 | 231 | 4 |
| 0.80 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 402 | 0 | 235 | 0 |
| 0.90 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 402 | 0 | 235 | 0 |

Le tableau concerne les moyennes joueur-match ; les métriques de seuil au niveau de la fenêtre historique de M5 ont des dénominateurs différents. À 0,50, le rappel est seulement **20/235**, malgré l'absence de faux positifs observés. L'intervalle de rappel basé sur la bootstrap de 95 % est **[0,046082 ; 0,126582]** ; l'intervalle du taux de faux positifs est dégénéré **[0 ; 0]** et ne permet pas d'établir un risque de population nul. La précision est nulle par convention lorsque aucun joueur n'est marqué. Les intervalles complets de seuil sont conservés dans `historical_test_metrics.json`.

Les inventaires d'erreurs conservent dix suspects à faible score et dix joueurs légitimes à haut score. Le suspect de plus bas score est le match `cs2cd_933b2a9d40151a48` / `Player_4` : **0,246399**, six fenêtres, classement 10. Un autre suspect obtient un score de **0,250059** sur 176 fenêtres, donc les faibles scores ne sont pas limités aux joueurs ayant très peu de fenêtres. Le joueur légitime de plus haut score est le match `cs2cd_966bc4025553eeec` / `Player_8` : **0,491801**, 232 fenêtres, classement 1. Un joueur légitime est classé en première position dans **20/64 matchs** ; **5/64** matchs n'ont pas de suspect marqué dans les trois premiers classements.

Les scores joueur-match des joueurs légitimes ont une moyenne/médiane de **0,284594 / 0,274929**, contre **0,350395 / 0,318411** pour les suspects marqués. Les moyennes de match historiques varient de **0,262760 à 0,488359**, avec une prévalence positive variable ; 39/64 matchs utilisent Dust II ou Mirage. Ces différences descriptives ne permettent ni d'identifier un effet de carte ni d'établir une explication causale. Les cas d'erreur révèlent des suspects marqués manquants et des erreurs de classement sous les annotations du jeu ; ils ne permettent pas de juger de la fraude réelle.

<a id="additional-cohort-with-negative-annotations"></a>
## Cohorte supplémentaire avec des annotations négatives

L'exécution complétée traite tous les **478 matchs supplémentaires** et extrait **1 268 375 fenêtres**. **477 matchs / 4 726 joueurs-match** reçoivent des scores, tous considérés comme légitimes selon la règle d'annotation de l'adaptateur. La liste contient **4 779 joueurs-match**, incluant **53 joueurs non notés sur 20 matchs**. Le match entièrement non noté `455.json` (`cs2cd_0835357838ac262a`) n'a pas d'événement `weapon_fire` et ne produit aucune fenêtre de caractéristique. Les entrées non notées de la liste conservent les scores indisponibles ; la valeur zéro n'est pas imputée. Les dénominateurs de classification et le bootstrap match excluent les scores indisponibles ; le dernier resample les 477 matchs notés.

L'analyse de `CS2CDAdapter.get_events()` sur ces 20 fichiers JSON révèle **aucun événement canonique de tir pour les 53 joueurs non notés** : dix appartiennent au match entièrement non noté et 43 aux 19 autres matchs. Aucun joueur ayant des événements canoniques de tir n'a de fenêtres de caractéristiques. Cela décrit les données canoniques fournies, et non une preuve que aucun tir réel n'a eu lieu (`data_quality_diagnostics.json`, `complete_cohort.unscored_player_shot_coverage`).

L'adaptateur existant conserve **498 335 087 sur 505 144 089 lignes brutes de tick** et exclut **6 809 002 (1,3479 %)** présentant des valeurs manquantes ou non finies pour les attributs requis d'identité, de position ou d'angle de vue. Ces totaux proviennent des reçus complets d'extraction. Un diagnostic séparé sur deux correspondances sélectionnées dans un aperçu antérieur de 82 correspondances reproduit les compteurs d'exclusion et constate la présence de champs manquants pour la position et l'angle de vue. Ce diagnostic sélectionné ne permet ni d'estimer les causes à l'échelle du groupe ni de prouver une couverture non biaisée. Les fenêtres canoniques conservées contiennent **40 588 000 lignes de tick** ; les règles de normalisation et d'imputation canoniques restent inchangées.

|Seuil (>=)|FN|FP|Taux de faux positifs|Intervalle de bootstrap à 95 %|
|---|---:|---:|---:|---|
| 0.10 | 0 | 4,726 | 1.000000 | [1.000000, 1.000000] |
| 0.20 | 1 | 4,725 | 0.999788 | [0.999361, 1.000000] |
| 0.30 | 3,483 | 1,243 | 0.263013 | [0.244794, 0.281640] |
| 0.40 | 4,526 | 200 | 0.042319 | [0.035001, 0.050266] |
| 0.50 | 4,665 | 61 | 0.012907 | [0.009072, 0.017143] |
| 0.60 | 4,702 | 24 | 0.005078 | [0.002736, 0.007877] |
| 0.70 | 4,708 | 18 | 0.003809 | [0.001693, 0.006356] |
| 0.80 | 4,712 | 14 | 0.002962 | [0.001264, 0.005078] |
| 0.90 | 4,714 | 12 | 0.002539 | [0.001055, 0.004435] |

À chaque seuil, TP et FN sont nuls et la précision est nulle sous les annotations négatives fournies. **ROC-AUC, Précision moyenne, rappel, F1 et Hit@k sont indisponibles**, ce qui ne signifie pas une performance de détection nulle : ce groupe ne contient aucune annotation positive. Le taux de faux positifs mesure l'insatisfaction par rapport à ces annotations, pas le comportement de tricherie adjudiqué. Ces intervalles dépendent de la couverture évaluée et des correspondances indépendantes. Ce groupe est conservé séparément du test historique, afin de préserver la prévalence de ce dernier et de permettre une comparaison avec M5.

Les **61 correspondances de joueurs marquées à 0,50 couvrent 44 correspondances évaluées**. Les moyennes/medians des scores sont **0,289650 / 0,273359**, le P99 est **0,518744** et la valeur maximale est **0,997079** pour `cs2cd_d63d08339edb4053 / Player_9`, basée sur cinq fenêtres et classée première. Les moyennes des scores par correspondance varient de **0,248276 à 0,480783**. Ces valeurs élevées s'opposent aux annotations même lorsque le taux de faux positifs du test historique était nul ; elles ne prouvent ni la tricherie réelle ni son absence. Les étiquettes, la couverture comportementale limitée et la transition vers les démonstrations natives restent des limites scientifiques.

Les **12 correspondances de joueurs avec un score supérieur ou égal à 0,90** couvrent neuf correspondances et 318 fenêtres. Une relecture confirme la présence de caractéristiques et de scores finis, y compris cinq fenêtres distinctes dans le cas maximal ; sept cas proviennent de quatre correspondances avec aucune ligne exclue. Cela établit des valeurs atypiques, pas leur origine ; aucune filtration supplémentaire ni seuil minimal de fenêtre n'est appliqué (`error_distribution_diagnostics.json`).

<a id="executed-checks"></a>
## Vérifications exécutées

L'évaluation se termine avec un code **0** et marque `integrity.json` comme **complète**. Tous les intersections entre correspondances de formation et d'évaluation sont vides. Les hachages du modèle, des métadonnées et du jeu historique restent inchangés ; les différences de ROC-AUC/AP historiques sont exactement nulles. Le redémarrage du modèle gelé et la répétition de l'inférence modifient tout score de fenêtre de manière maximale de **5,551115123125783e-16**, en dessous du seuil de tolérance **1e-12**. Les moyennes des joueurs recalculées indépendamment sont conformes aux moyennes des scores de fenêtre. Une extraction séparée à partir de la source réelle répète **158 fenêtres de manière identique au niveau des octets** sur une correspondance ; la réextraction complète du groupe n'est pas affirmée.

Un vérificateur exhaustif séparé se termine avec un code **0** et reproduit les scores RF, les moyennes des joueurs, les classements, la couverture du roster, les métriques et les intervalles de bootstrap à partir de **toutes les 478 caches canoniques / 1 268 375 fenêtres**, y compris le cache vide. Il vérifie tous les **478 hachages de sources Parquet**, les **795 sources JSON**, le code gelé et les archives sources ; la comparaison des archives confirme les transformations scientifiques inchangées lors du changement de lecture Parquet. Les vérifications du test historique sont également satisfaisantes. Cela confirme les caractéristiques canoniques persistantes et l'inférence, pas une réextraction complète des données brutes (`verification.json`, `verification_run.log`).

Le contrôle de conservation est satisfaisant pour **407 empreintes SHA-256**, comprenant le modèle, les métadonnées, les ensembles de données historiques et **403 fichiers de sortie M6 historiques**. Les ensembles de fichiers dans les trois répertoires de sortie historiques restent inchangés, y compris les études de robustesse et externes du 14 octobre 2026 (`integrity_preservation.json`).

L'ensemble complet d'automatisation passe **345 tests**. `pip check`, la compilation syntaxique et `git diff --check` sont validés. **Statut de M6 : complet dans son champ fonctionnel et technique, avec une évaluation scientifique interne documentée.** Ces vérifications logicielles ne permettent pas d'établir de probabilités calibrées, un seuil opérationnel, une généralisation positive indépendante ou une performance de détection de démonstrations natives.

<a id="reproduction-and-retained-evidence"></a>
## Réproduction et preuves conservées

À partir de la racine du dépôt :

```powershell
.\.venv\Scripts\python.exe demo_analyzer/scripts/evaluate_cs2cd.py
.\.venv\Scripts\python.exe -m pytest -q
```

Les sorties sont conservées sous `demo_analyzer/data/processed/validation_cs2cd_20261015/` ignoré. `protocol.json` fige les empreintes de modèle/métadonnées/ensembles de données, le code, les versions, l'état Git et les paramètres avant l'inférence ; `sources.zip` conserve la source. `partitions.json`, `raw_inventory.csv` et `raw_roster.csv` identifient les correspondances et les étiquettes. Les scores de fenêtre historique sont conservés au format CSV ; les fenêtres de cohortes nouvelles restent dans les caches canoniques par correspondance et utilisent le chemin d'inférence figé. Les fichiers CSV de population conservent les moyennes des joueurs, les classements, la couverture et les cas d'erreur ; `historical_test_metrics.json` et `unused_negative_metrics.json` conservent les intervalles complets, et `*_by_match.json` conserve les résultats au niveau de la correspondance. `extraction_integrity.json` enregistre les compteurs bruts et conservés ainsi que les hachages source/attributs ; `integrity.json` enregistre les vérifications finales. `report.md` résume les deux populations. Les vérifications de reprise conservent les reçus, répètent les évaluations et les métriques ; un autre répertoire `--output` effectue une extraction fraîche. Les tentatives interrompues sont archivées séparément, y compris le protocole avant la projection Parquet vérifiée. Les artefacts M5/M6 précédents et l'étude externe du 14 octobre 2026 sont conservés séparément.

Le champ de protocole `contract.raw_inventory_sha256` hachage la représentation JSON canonique de l'inventaire via `digest_json(inventory)`, et non les octets de `raw_inventory.csv` ; un hachage différent de fichier CSV est attendu.

<a id="m7-temporal-modeling-implementation"></a>
# M7 - Implémentation de la modélisation temporelle

M7 dispose maintenant d'un chemin technique exécutable. `build_temporal_dataset.py` transforme chaque fenêtre canonique complète de 32 ticks terminant sur un tir en six canaux float32 ordonnés : vitesses yaw et pitch, vitesse angulaire, accélérations yaw et pitch, et amplitude d'accélération angulaire. Les différences yaw gèrent le passage -180°/180°. Le NPZ conserve les tableaux de fenêtre, match, joueur, cible et split. Son JSON adjacent enregistre version du schéma, ordre des canaux, fréquence de 64 Hz, seed, compteurs et normalisation ajustée uniquement sur l'entraînement.

Le split conserve le test de 20 % groupé par match de M5, puis prélève les matchs de validation uniquement dans la partie entraînement restante. Une baseline de régression logistique aplatie et quatre candidats PyTorch compacts sont implémentés : CNN 1D, LSTM, GRU et Transformer Encoder à une couche. L'entraînement neuronal utilise une entropie croisée binaire pondérée, le seed 42 et un arrêt anticipé sur la PR-AUC joueur-match de validation. `train_temporal.py` accepte `--device auto|cpu|cuda` ; ROCm utilise l'API `torch.cuda`, donc `--device cuda` impose le GPU AMD et échoue s'il n'est pas disponible. La sélection ordonne les candidats par PR-AUC, ROC-AUC, latence sur le périphérique choisi, nombre de paramètres, puis nom. Le test verrouillé n'est lu qu'après la sélection.

`train_temporal.py` peut comparer le modèle temporel sélectionné, la baseline logistique temporelle et la Forêt aléatoire M5 gelée sur les mêmes fenêtres de test. Il rapporte métriques fenêtre/joueur, Hit@1/Hit@3, différences bootstrap appariées par match, latence batch 1, débit batch 256 et sensibilité par occlusion nulle selon le tick et le canal. Les bundles PyTorch contiennent un `state_dict` et un JSON. `cs2guard analyze` utilise `model_family`, préserve le chemin joblib M5 et ajoute l'occlusion temporelle aux rapports JSON/Markdown.

Commandes de reproduction :

```bash
# WSL2 Ubuntu 24.04, avec ROCm 7.2 et ROCDXG installés
source ~/.venvs/cs2guard-rocm/bin/activate
export HSA_ENABLE_DXG_DETECTION=1
python demo_analyzer/scripts/train_temporal.py --device cuda --models transformer --epochs 5 --m5-model demo_analyzer/models/supervised/random_forest_v1.joblib
```

Les tests logiciels couvrent forme des séquences, passage angulaire, isolation des splits, normalisation sur l'entraînement, quatre familles de modèles, persistance, occlusion, compatibilité M5 et analyse temporelle de bout en bout. La construction complète produit **397 480 séquences** : 242 996 d'entraînement, 63 315 de validation et 91 169 de test verrouillé. Après cinq epochs au maximum sur le RX 7800 XT, la PR-AUC joueur-match de validation du Transformer vaut **0,779367**. Elle reste supérieure aux valeurs précédemment enregistrées pour LSTM (0,7597), GRU (0,7553), CNN (0,7441) et régression logistique (0,6608).

Sur les matchs de test historiques M5, le Transformer ROCm atteint **ROC-AUC joueur-match 0,828231 / PR-AUC 0,750003**, contre **0,777898 / 0,683983** pour la Forêt aléatoire M5 gelée et **0,689690 / 0,616041** pour la régression logistique temporelle. Les différences bootstrap appariées par match contre M5 sont **+0,050333 ROC-AUC, IC 95 % [0,027248 ; 0,076609]**, et **+0,066019 PR-AUC, IC 95 % [0,037595 ; 0,095683]**, sur 1 000 tirages. Hit@1 vaut 44/64 et Hit@3 59/64. Au seuil 0,50, précision/rappel/F1/FPR par fenêtre valent 0,376901/0,490888/0,426408/0,299632 ; ce seuil reste descriptif et non validé.

L'exécution WSL2 Ubuntu 24.04 / Python 3.12.3 / PyTorch 2.9.1 / ROCm 7.2 sur un **AMD Radeon RX 7800 XT** mesure 0,520 ms en médiane et 0,951 ms au p95 pour le batch 1 sur 100 répétitions. Le batch 256 mesure 1,069 ms en médiane, soit environ 239 474 séquences/s. Métriques détaillées, bundle, historique, benchmarks CPU/GPU, JSON d'occlusion et dix graphiques restent dans `demo_analyzer/data/processed/m7_temporal_rocm/` ignoré. Le bundle sélectionné de 9 825 paramètres est conservé sous `demo_analyzer/models/temporal/transformer_v1.pt` avec l'environnement ROCm dans ses métadonnées. Ces résultats réutilisent les matchs de test M5 déjà évalués et ne constituent pas une validation indépendante. Les scores restent des priorités d'inspection non calibrées, pas des probabilités ni des preuves de triche.

<a id="future-milestones"></a>
# Étapes futures

M8 à M10 restent futurs. Une validation positive indépendante, le choix d'un seuil opérationnel et la calibration restent ouverts pour M7. Les limitations de validation de M6 restent visibles plutôt que de devenir des affirmations scientifiques non soutenues.
