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

# Future Milestones

Future sections will document the next Demo Analyzer milestones as they are implemented.

The objective is to preserve not only **what CS2Guard does**, but also the reasoning and technical decisions that led to the final implementation.
