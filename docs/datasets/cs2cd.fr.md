[English](cs2cd.md) | [Français](cs2cd.fr.md) | [简体中文](cs2cd.zh-CN.md)

[README du projet](../../README.fr.md)

<a id="cs2cd-integration"></a>
# Intégration CS2CD

<a id="purpose"></a>
## Objectif

Ce document décrit la manière dont le jeu de données CS2CD est intégré dans le constructeur de jeu de données CS2Guard.

CS2CD est utilisé comme source externe de données de jeu de Counter-Strike 2 étiquetées. Sa représentation spécifique à la source est convertie au format canonique du jeu de données CS2Guard avant d'être utilisé par la chaîne de traitement des caractéristiques et de l'apprentissage automatique.

<a id="source-data"></a>
## Données de source

Un match CS2CD est représenté par deux fichiers complémentaires :

- JSON : métadonnées du match, événements de jeu et annotations sur les joueurs suspects
- Parquet : données de suivi des joueurs au niveau des ticks

La chaîne d'intégration est :

CS2CD JSON + Parquet → Adaptateur CS2CD → Données canoniques CS2Guard → Extraction des caractéristiques → Pipeline de jeu de données

<a id="cs2cd-adapter"></a>
## Adaptateur CS2CD

CS2Guard utilise un adaptateur spécifique situé à :

`src/cs2guard_demo/dataset/adapters/cs2cd.py`

L'adaptateur gère actuellement :

- métadonnées du match
- données des joueurs au niveau des ticks
- tirs
- coupures
- meurtres
- étiquettes légitimes / suspectes

L'implémentation de cette logique dans un adaptateur empêche le reste de CS2Guard de dépendre directement du format CS2CD.

<a id="player-labels"></a>
## Étiquettes des joueurs

CS2CD fournit des annotations explicites identifiant les joueurs suspects.

Ces annotations sont converties en étiquettes CS2Guard :

- les joueurs listés comme suspects → `suspicious`
- les autres joueurs du match → `legitimate`

Les étiquettes proviennent donc du jeu de données externe et ne sont pas inférées à partir des caractéristiques comportementales de CS2Guard.

<a id="anonymous-player-identities"></a>
## Identités anonymes des joueurs

CS2CD anonymise les joueurs en utilisant des identifiants tels que `Player_1`, `Player_2` ou `Player_3`.

Ces identifiants sont locaux à un match et ne doivent pas être traités comme des identités globalement uniques des joueurs.

Par exemple :

`Match A / Player_3`

et :

`Match B / Player_3`

peuvent correspondre à deux joueurs réels complètement différents.

Un joueur peut donc être suspect dans un match tandis qu'un autre joueur utilisant le même identifiant anonymisé est légitime dans un autre match.

CS2Guard restreint les identités des joueurs CS2CD à leur match.

Par exemple :

`source_player_id = Player_3`

devient conceptuellement :

`player_id = cs2cd:<match_id>:Player_3`

Cela empêche les joueurs anonymes provenant de matches différents d'être incorrectement fusionnés.

<a id="data-leakage-limitation"></a>
## Limitation de fuite de données

Les démos natives de CS2 peuvent fournir des identifiants Steam persistants, permettant à CS2Guard de reconnaître le même joueur dans plusieurs matches.

CS2CD supprime cette information par anonymisation.

En conséquence, CS2Guard peut garantir que le même match CS2CD ne figure pas dans plusieurs splits d'entraînement, de validation ou de test.

Cependant, CS2Guard ne peut pas garantir que le même joueur réel ne figure pas anonymement dans plusieurs matches CS2CD.

Cette limitation doit être prise en compte lors de l'évaluation des modèles entraînés ou testés avec CS2CD.

<a id="current-status"></a>
## État actuel

L'adaptateur CS2CD est implémenté et couvert par des tests automatisés.

L'adaptateur peut actuellement normaliser les métadonnées, les événements, les données au niveau des ticks et les étiquettes des joueurs.

L'adaptateur est intégré au constructeur canonique de Dataset et aux expériences M4/M5, comme enregistré dans la mémoire du projet Demo Analyzer. Les tests automatisés utilisent des fixtures JSON/Parquet contrôlées et couvrent les données de télémétrie non finies et les identités anonymes limitées à chaque match. L'audit M6 ne répète pas les expériences de formation sur l'ensemble complet du dataset historique.

Le constructeur multi-source écrit des en-têtes stables pour les événements/tick au format CSV. Un résultat historique avec un en-tête différent ne peut pas être reprendu de manière sécurisée. Conservez tous les résultats de recherche avant de les reconstruire sans `--resume` ; le constructeur remplace ses fichiers CSV générés lors d'une reconstruction fraîche.
