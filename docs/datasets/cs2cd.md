# CS2CD Integration

## Purpose

This document describes how the CS2CD dataset is integrated into the CS2Guard Dataset Builder.

CS2CD is used as an external source of labeled Counter-Strike 2 gameplay data. Its source-specific representation is converted into the canonical CS2Guard dataset format before being used by the feature extraction and machine-learning pipeline.

## Source Data

A CS2CD match is represented by two complementary files:

- JSON: match metadata, gameplay events and cheater annotations
- Parquet: tick-level player telemetry

The integration pipeline is:

CS2CD JSON + Parquet
→ CS2CD Adapter
→ Canonical CS2Guard Data
→ Feature Extraction
→ Dataset Pipeline

## CS2CD Adapter

CS2Guard uses a dedicated adapter located at:

`src/cs2guard_demo/dataset/adapters/cs2cd.py`

The adapter currently handles:

- match metadata
- tick-level player data
- shots
- hits
- kills
- legitimate / suspicious labels

Keeping this logic inside an adapter prevents the rest of CS2Guard from depending directly on the CS2CD format.

## Player Labels

CS2CD provides explicit annotations identifying cheating players.

These annotations are converted into CS2Guard labels:

- players listed as cheaters → `suspicious`
- other players in the match → `legitimate`

Labels therefore come from the external dataset and are not inferred from CS2Guard behavioral features.

## Anonymous Player Identities

CS2CD anonymizes players using identifiers such as `Player_1`, `Player_2` or `Player_3`.

These identifiers are local to a match and must not be treated as globally unique player identities.

For example:

`Match A / Player_3`

and:

`Match B / Player_3`

may correspond to two completely different real players.

A player can therefore be suspicious in one match while another player using the same anonymized identifier is legitimate in another match.

CS2Guard scopes CS2CD player identities to their match.

For example:

`source_player_id = Player_3`

becomes conceptually:

`player_id = cs2cd:<match_id>:Player_3`

This prevents anonymous players from different matches from being incorrectly merged.

## Data Leakage Limitation

Native CS2 demos can provide persistent Steam IDs, allowing CS2Guard to recognize the same player across multiple matches.

CS2CD removes this information through anonymization.

As a consequence, CS2Guard can guarantee that the same CS2CD match does not appear in multiple train, validation or test splits.

However, CS2Guard cannot guarantee that the same underlying real player does not appear anonymously in different CS2CD matches.

This limitation must be considered when evaluating models trained or tested with CS2CD.

## Current Status

The CS2CD adapter is implemented and covered by automated tests.

The adapter can currently normalize metadata, events, tick data and player labels.

The next step is to validate the adapter on real CS2CD JSON / Parquet match pairs and integrate the resulting data into the complete canonical CS2Guard Dataset Builder pipeline.