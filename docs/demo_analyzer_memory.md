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

M2 focuses on transforming raw view-angle data into meaningful **aim-related features**.

Raw pitch and yaw values alone provide limited information.

The objective is therefore to derive temporal measurements describing **how the player's aim moves over time**.

These features will later contribute to suspicious-behavior analysis.

Conceptually:

```text
View angles
    ↓
Angle processing
    ↓
Aim movement features
    ↓
Behavior analysis
```

## Features

### Angle Processing

Raw view angles must be handled correctly before calculating movement-related features.

This is especially important for yaw because angles wrap around.

For example, a transition around the `-180° / +180°` boundary must not incorrectly appear as an extremely large rotation.

### Angular Velocity

Angular velocity measures how quickly the player's view direction changes over time.

It allows CS2Guard to distinguish between slow aim adjustments and rapid rotations.

### Angular Acceleration

Angular acceleration measures how quickly angular velocity itself changes.

This provides information about sudden changes in aim movement.

Large values are not automatically suspicious: rapid mouse movements, flicks, direction changes and the discrete nature of sampled demo data can naturally produce significant acceleration values.

The feature must therefore be interpreted in context rather than used as a standalone cheat indicator.

### Temporal / Rolling Features

Aim behavior can also be analyzed over a window of consecutive samples rather than only between two individual samples.

These windows allow later stages to describe short sequences of player behavior.

The exact interpretation of these windows must take Counter-Strike 2's tick and subtick systems into account.

## Current Status

M2 is currently under development.

This section should be expanded as each aim feature is implemented and validated.

For every completed feature, the following should be documented:

* purpose;
* mathematical definition;
* implementation;
* affected files;
* edge cases;
* tests;
* example output;
* interpretation for anti-cheat analysis.

---

# Future Milestones

Future sections will document the next Demo Analyzer milestones as they are implemented.

The objective is to preserve not only **what CS2Guard does**, but also the reasoning and technical decisions that led to the final implementation.
