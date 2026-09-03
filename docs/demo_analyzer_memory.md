# CS2Guard — Demo Analyzer Project Memory

## 1. Purpose

This document keeps track of the development of the **CS2Guard Demo Analyzer**.

Its purpose is not to replace the main `README.md`, but to provide a more detailed technical record of the project:

* what was implemented;
* why each feature was introduced;
* how each feature works;
* which parts of the codebase are involved;
* how the implementation was tested;
* what technical decisions were made along the way.

The Demo Analyzer corresponds to the **v1.x** development phase of CS2Guard.

Its long-term objective is to analyze Counter-Strike 2 demo files and extract meaningful gameplay features that can later be used to identify suspicious player behavior.

---

# M1 — Demo Parsing Foundation

## Objective

The objective of M1 was to build the data extraction foundation of CS2Guard.

Before attempting to detect suspicious behavior, the project first needs to transform a raw Counter-Strike 2 `.dem` file into structured Python data that can be processed by later analysis stages.

In simplified form:

```text
CS2 Demo (.dem)
      ↓
 Demo Parser
      ↓
Structured match data
      ↓
Players / Rounds / Ticks / Events
```

## Main Features

### Demo Parsing

CS2Guard can load and parse a Counter-Strike 2 demo file.

The parser provides access to both match-level information and gameplay data recorded during the match.

### Match Metadata

Basic metadata can be extracted from the demo, such as information describing the match and the demo itself.

This provides contextual information about the data being analyzed.

### Players and Teams

Player information is extracted and normalized so that players can be identified consistently throughout the analysis.

This includes information such as:

* player names;
* Steam IDs;
* team information.

### Round Data

The match can be divided into rounds so that events and player behavior can later be analyzed in the correct gameplay context.

### Tick-Level Player Data

Player state can be extracted over time.

This provides the foundation for temporal features such as movement and aim analysis.

Important information includes:

* player position;
* view angles;
* active weapon;
* player state at a given point in the demo.

### Gameplay Events

Several important gameplay events are extracted.

#### Shots

Represents a weapon shot performed by a player.

Useful information includes the player, weapon and timing of the shot.

#### Hits

Represents damage inflicted on another player.

Hit events provide information such as:

* attacker;
* victim;
* weapon;
* damage;
* hitgroup;
* timing.

#### Kills

Represents player eliminations.

Kill events contain additional contextual information such as:

* attacker and victim;
* weapon;
* headshot status;
* distance;
* penetration;
* smoke interaction;
* no-scope status.

## Data Normalization

Raw parser output is converted into internal CS2Guard structures.

The goal is to prevent the rest of the project from depending directly on the representation returned by the demo parsing library.

Conceptually:

```text
Raw demo data
      ↓
DemoParser
      ↓
Normalization
      ↓
CS2Guard models
```

This separation will make later analysis components easier to maintain and test.

## Testing

The parsing foundation is covered by automated tests.

An important design decision was to avoid making the main test suite depend on a local `test.dem` file that would not necessarily be available in the repository or CI environment.

Real demo files can still be used manually for integration and visualization tests.

## Result

At the end of M1, CS2Guard has a functional foundation capable of transforming CS2 demo data into structured information suitable for feature extraction.

The project can therefore move from:

> "Can CS2Guard read a match?"

to:

> "What useful behavioral features can CS2Guard extract from that match?"

---

# M2 — Aim Feature Extraction

## Objective

The objective of M2 was to transform the raw view-angle information extracted during M1 into reusable **aim movement features**.

Pitch and yaw values describe where a player is looking, but they are not directly sufficient for behavioral analysis. M2 therefore introduces a feature-extraction layer that describes how the player's aim evolves over time.

Conceptually:

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

These features form the first behavioral feature family of the Demo Analyzer.

## Main Features

### Angle Processing

Aim calculations are based on the player's pitch and yaw values extracted from consecutive demo ticks.

Yaw requires special handling because angles wrap around at the `-180° / +180°` boundary. A transition such as `179° → -179°` must therefore be interpreted as a small rotation rather than a rotation of almost 360°.

Normalized angular differences ensure that velocity and acceleration calculations represent the actual aim movement.

### Angular Velocity

Angular velocity measures how quickly the player's view direction changes between samples.

Velocity is calculated independently for pitch and yaw, allowing horizontal and vertical aim movements to remain distinguishable.

Conceptually:

```text
angular velocity = angular displacement / elapsed time
```

This can describe slow tracking, normal aim corrections, rapid rotations and flick-like movements.

High angular velocity alone is not considered evidence of cheating.

### Angular Acceleration

Angular acceleration measures how quickly angular velocity changes over time.

Conceptually:

```text
angular acceleration = change in angular velocity / elapsed time
```

It helps characterize abrupt changes in aim movement, including the beginning or end of rapid mouse movements.

Large acceleration values can occur naturally because of flicks, rapid direction changes, discrete demo sampling and short time intervals. Acceleration is therefore a behavioral feature that must later be interpreted with additional context rather than as a standalone cheat indicator.

### Rolling / Temporal Aim Features

Individual tick-to-tick measurements can be noisy and provide only a very local description of player behavior.

M2 therefore also computes rolling statistics over consecutive samples. These temporal features summarize short aim sequences and provide more stable information for later analysis.

The rolling calculations are designed around demo tick data; their interpretation must remain aware of CS2's tick/subtick recording behavior.

## Shot-Centered Aim Sequences

For manual validation, M2 can inspect an aim sequence around a selected shot.

The visualization workflow exposes contextual information such as:

* player;
* target;
* weapon;
* shot tick;
* hit tick when applicable.

A window around the shot can then be inspected to understand how the player's aim behaved immediately before and after firing.

## Aim Visualization

A dedicated visualization script is used for manual inspection of M2 features.

Responsibilities are separated between:

```text
scripts/parse_demo.py
    → M1 parsing / structured demo inspection

scripts/visualize_aim.py
    → M2 aim feature inspection / visualization
```

The generated graphs allow the evolution of aim-related values around a selected shot to be inspected visually. They are a development and validation tool rather than a final cheat-detection mechanism.

## Weapon Context

The selected shot sequence also exposes the weapon used by the player.

Weapon names come from demo data. For example, `elite` corresponds to the Dual Berettas.

Weapon context may become useful later because legitimate aim behavior can vary with the weapon and firing situation. At M2, it remains contextual information rather than a suspiciousness criterion.

## Implementation Structure

Aim feature extraction is kept separate from demo ingestion.

Conceptually:

```text
src/cs2guard/ingestion/demo/
        ↓
normalized tick/event data
        ↓
src/cs2guard/features/aim/
        ↓
aim features
        ↓
scripts/visualize_aim.py
```

This allows feature extraction to be reused later by detection or machine-learning components without depending on visualization code.

## Testing

M2 is covered by automated tests for the aim feature extraction logic.

The tests validate feature calculations independently of a local `.dem` file, keeping the main test suite reproducible and suitable for CI.

A real demo can still be used manually through `visualize_aim.py` for integration and visual validation.

At the end of M2, all automated tests pass.

## Technical Decisions

Important decisions made during M2 include:

* deriving aim features from normalized tick-level data rather than directly from raw parser output;
* handling angular wrap-around before movement calculations;
* keeping pitch and yaw movements distinguishable;
* treating velocity and acceleration as descriptive signals rather than direct cheat indicators;
* using rolling statistics to provide temporal context;
* using shot-centered sequences for practical manual inspection;
* keeping automated tests independent from a committed demo file;
* keeping `parse_demo.py` focused on M1 and `visualize_aim.py` focused on M2.

## Result

M2 is complete and validated.

CS2Guard can now transform raw view-angle data into structured aim behavior features and inspect those features around gameplay events such as shots and hits.

The Demo Analyzer has progressed from:

> "Where is the player looking?"

to:

> "How is the player's aim moving over time, especially around combat actions?"

These aim features provide the first behavioral signals that can later be combined with other feature families and detection logic to identify suspicious gameplay.

---

# M3 — Dataset Builder

## Objective

The objective of M3 was to transform the structured match data and behavioral features produced by the previous milestones into reproducible datasets suitable for machine-learning workflows.

Instead of analyzing a single demo manually, CS2Guard can now process collections of matches and generate standardized samples that can later be used for training, validation and evaluation.

Conceptually:

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

## Main Features

### Multi-Demo Processing

The dataset builder can process multiple demo files automatically rather than requiring each match to be analyzed individually.

This makes it possible to build larger datasets from collections of CS2 matches while keeping the processing pipeline reproducible.

### Event-Level Samples

Gameplay events can be converted into individual dataset samples.

These samples preserve event context while exposing features in a format suitable for later machine-learning stages.

### Player-Level Samples

CS2Guard can also aggregate information at player level.

This provides a representation of player behavior across a larger portion of a match rather than only around isolated events.

### Temporal Windows

Temporal windows group consecutive observations so that short-term behavior can be represented as sequences.

This is important for features such as aim movement, where the evolution of a signal over time can be more informative than a single measurement.

### Feature Storage

Generated samples and their associated features can be stored in reusable dataset files.

The objective is to separate expensive demo processing from later machine-learning experiments so that the same generated dataset can be reused without parsing every source match again.

### Missing and Invalid Data

The dataset pipeline handles missing or invalid values so that malformed samples do not silently corrupt the generated dataset.

This is particularly important when processing large collections of matches coming from different sources.

### Numeric Normalization

Numeric features can be normalized into consistent representations suitable for machine-learning processing.

Normalization is performed at the dataset layer rather than changing the original gameplay information extracted from the source.

### Labels

Dataset samples support labels representing the expected class of the associated behavior, including legitimate and suspicious data.

The labeling layer is kept separate from feature extraction so that behavioral features do not directly encode the expected result.

### Dataset Splits

The builder generates train, validation and test splits for later machine-learning experiments.

A central requirement is to prevent information leakage between these splits.

Matches and player identities are therefore considered when assigning samples so that strongly related observations are not distributed across training and evaluation subsets when the available source data makes this possible.

### Dataset Statistics

The generated dataset can expose statistics describing its content.

These statistics provide a basic validation step for checking the number and distribution of generated samples before using them for model training.

## External Dataset Support

M3 introduces support for external datasets through source-specific adapters and a canonical CS2Guard dataset representation.

The first external source being integrated is CS2CD. A dedicated adapter has been implemented and its automated tests pass.

Detailed CS2CD integration decisions, including anonymous player identity handling and data-leakage limitations, are documented in [`datasets/cs2cd.md`](datasets/cs2cd.md).

## CS2CD Identity and Leakage Constraints

CS2CD anonymizes player identities, which prevents CS2Guard from directly associating its records with the original Steam identities from raw demo files.

This means player-level leakage prevention cannot rely on a persistent real-world player identifier across unrelated CS2CD matches.

The dataset pipeline must therefore preserve the strongest grouping information available from the source and document where leakage guarantees are limited by source anonymization.

This distinction is important because leakage prevention is a property of both the splitting strategy and the identity information provided by the source dataset.

## Coach / Non-Player Edge Case

During M3 validation, an edge case was observed in demo data involving people present only as coaches.

A coach can appear in extracted player-related data and may even produce unexpected gameplay-like records, such as a death during freeze time.

This means that presence in the parser output alone is not sufficient to guarantee that an entity should be treated as a normal participating player.

The case must therefore remain accounted for when constructing player-level datasets so that non-playing participants do not silently contaminate generated samples.

## Implementation Structure

M3 extends the project from single-demo feature inspection toward a reusable dataset pipeline.

Conceptually:

```text
Demo files / external datasets
        ↓
src/cs2guard/ingestion/
        ↓
canonical CS2Guard data
        ↓
src/cs2guard/features/
        ↓
dataset builder
        ↓
generated ML-ready datasets
```

Source-specific logic remains isolated from the canonical dataset representation. This allows future external datasets to be integrated through their own adapters without forcing the rest of the pipeline to depend on their original schema.

## Testing

M3 is covered by automated tests for the dataset-building pipeline and the CS2CD adapter.

The test suite validates the dataset logic independently of large local demo collections, while real multi-demo builds are used for integration validation.

At the end of M3, the automated test suite passes, including the dedicated CS2CD adapter tests.

## Technical Decisions

Important decisions made during M3 include:

* processing multiple matches through a reproducible dataset-building pipeline;
* supporting event-level, player-level and temporal representations;
* separating source ingestion from the canonical CS2Guard dataset representation;
* introducing source-specific adapters for external datasets;
* using CS2CD as the first external dataset integration;
* keeping feature extraction independent from dataset labels;
* generating train, validation and test splits with leakage prevention as a core requirement;
* grouping samples using match and player information when the source provides sufficient identity information;
* explicitly documenting weaker player-level leakage guarantees when external datasets anonymize identities;
* handling missing and invalid samples before dataset generation;
* exposing dataset statistics for validation;
* keeping the coach/non-player edge case in mind when determining valid player samples.

## Result

M3 is complete and validated.

CS2Guard can now transform data from multiple matches into structured, reusable datasets suitable for future machine-learning stages.

The Demo Analyzer has progressed from:

> "What behavioral features can be extracted from a match?"

to:

> "How can those features be converted into a reproducible dataset without introducing avoidable data leakage?"

The project now has the dataset foundation required for later model training and suspicious-behavior detection.

---

# Future Milestones

Future sections will document the next Demo Analyzer milestones as they are implemented.

The objective is to preserve not only **what CS2Guard does**, but also the reasoning and technical decisions that led to the final implementation.
