# CS2Guard

**Machine Learning-Based Behavioral Cheat Detection for Counter-Strike 2**

CS2Guard is an experimental machine learning project designed to detect suspicious player behavior in Counter-Strike 2.

The project starts with **offline analysis of CS2 demo files** to extract gameplay data, engineer behavioral features, build datasets, and train detection models.

The long-term goal is to evolve the project into a **real-time server-side anti-cheat** capable of continuously analyzing player behavior during matches without relying on intrusive client-side monitoring.

> **Status:** 🚧 In Development
> **Development:** 🤖 AI-Assisted

---

## 🤖 AI-Assisted Development

CS2Guard is developed with the assistance of AI tools.

AI is used as a development assistant for tasks such as:

* Code generation and refactoring
* Debugging and troubleshooting
* Documentation
* Architecture discussions
* Research and technical exploration
* Test generation
* Machine learning experimentation

The project's architecture, technical decisions, experiments, evaluation methodology, and final implementation remain under human supervision and validation.

AI-generated code and suggestions are reviewed, tested, and adapted before being integrated into the project.

---

## 🎯 Project Goals

CS2Guard explores whether cheating behavior can be detected from gameplay telemetry using machine learning.

The project focuses on behavioral signals such as:

* Aim movement
* Crosshair placement
* Target tracking
* Reaction time
* Angular velocity and acceleration
* Shooting behavior
* Player movement
* Enemy awareness
* Prefire patterns

Rather than searching for cheat software on the player's computer, CS2Guard focuses on detecting **abnormal gameplay behavior observable from game data**.

The project follows two main stages:

1. **Offline Demo Analysis** — research, feature engineering, dataset construction and model training.
2. **Real-Time Server-Side Detection** — deployment of the detection pipeline on live server data.

---

## 🧠 Project Approach

### Stage 1 — Offline Demo Analysis

CS2 demo files provide historical match data that can be analyzed without real-time constraints.

This stage is used to understand gameplay data, develop behavioral features and evaluate different machine learning approaches.

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

The offline analyzer acts as the research and validation environment for the future real-time system.

### Stage 2 — Real-Time Server-Side Detection

Once the detection approach has been validated on historical matches, the same feature extraction and ML pipeline will progressively be adapted to live server data.

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

A major objective is to reuse the same behavioral representation and detection models between offline and online analysis whenever possible.

---

# 🗺️ Roadmap

## M1 — Demo Parsing

Build the foundation for extracting structured gameplay data from CS2 demo files.

* [ ] Set up the Python project structure
* [ ] Integrate a CS2 demo parser
* [ ] Load and parse `.dem` files
* [ ] Extract match metadata
* [ ] Extract players and teams
* [ ] Extract rounds
* [ ] Extract tick-level player positions
* [ ] Extract view angles (yaw / pitch)
* [ ] Extract weapon information
* [ ] Extract shots, hits, and kills
* [ ] Define normalized `Match`, `Player`, `Round`, `Tick`, and `Event` structures
* [ ] Add tests for demo parsing

**Milestone result:** A `.dem` file can be converted into structured gameplay data usable by the rest of CS2Guard.

---

## M2 — Aim Feature Engineering

Transform raw gameplay data into measurable aiming behavior.

* [ ] Compute crosshair direction
* [ ] Compute crosshair-to-target angular distance
* [ ] Compute angular velocity
* [ ] Compute angular acceleration
* [ ] Detect target acquisition
* [ ] Measure reaction time
* [ ] Measure tracking error
* [ ] Measure aim corrections and overshoot
* [ ] Detect potential aim snaps
* [ ] Associate shots with aiming sequences
* [ ] Visualize aim trajectories
* [ ] Validate features on selected demo sequences

**Milestone result:** CS2Guard can represent a player's aiming behavior as numerical features.

---

## M3 — Dataset Builder

Create a reproducible pipeline for generating machine-learning-ready datasets from multiple matches.

* [ ] Process multiple demo files automatically
* [ ] Generate event-level samples
* [ ] Generate player-level samples
* [ ] Generate temporal windows
* [ ] Store extracted features
* [ ] Handle missing or invalid data
* [ ] Normalize numerical features
* [ ] Add support for legitimate / suspicious labels
* [ ] Create train / validation / test splits
* [ ] Prevent data leakage between matches and players
* [ ] Generate dataset statistics

**Milestone result:** A collection of CS2 demos can automatically be transformed into a clean ML dataset.

---

## M4 — Anomaly Detection

Build the first ML-based behavioral detector without requiring large amounts of labeled cheating data.

* [ ] Establish statistical baselines for legitimate behavior
* [ ] Implement Isolation Forest
* [ ] Experiment with Local Outlier Factor
* [ ] Experiment with One-Class SVM
* [ ] Compare anomaly detection approaches
* [ ] Generate anomaly scores for individual events
* [ ] Generate anomaly scores for players
* [ ] Analyze false positives
* [ ] Identify the most influential features
* [ ] Define an initial suspicion scoring strategy

**Milestone result:** CS2Guard can automatically identify unusual aiming behavior.

---

## M5 — Supervised Detection

Train classification models once sufficiently reliable labeled data becomes available.

* [ ] Build a labeled dataset
* [ ] Establish a baseline classifier
* [ ] Train Random Forest models
* [ ] Experiment with gradient boosting models
* [ ] Tune model hyperparameters
* [ ] Measure precision
* [ ] Measure recall
* [ ] Measure F1-score
* [ ] Measure ROC-AUC / PR-AUC
* [ ] Analyze the false-positive rate
* [ ] Compare supervised and anomaly-detection approaches
* [ ] Add model versioning and persistence

**Milestone result:** CS2Guard has an evaluated ML model capable of producing behavioral suspicion predictions.

---

## M6 — Demo Analyzer

Turn the machine learning pipeline into a usable offline match-analysis tool.

* [ ] Analyze an entire demo from a single command
* [ ] Analyze every player in the match
* [ ] Generate an overall suspicion score per player
* [ ] Generate separate behavioral scores
* [ ] Rank players by suspicion score
* [ ] Identify suspicious rounds
* [ ] Identify suspicious events
* [ ] Explain which features contributed to a score
* [ ] Visualize suspicious aim sequences
* [ ] Generate a match analysis report
* [ ] Build a CLI for demo analysis

Example:

```bash
cs2guard analyze match.dem
```

Possible output:

```text
Match Analysis
─────────────────────────────────

Player          Suspicion Score
─────────────────────────────────
Player 1             12%
Player 2             19%
Player 3             84%  ⚠
Player 4             21%
Player 5             16%
```

A suspicious player could then be inspected in more detail:

```text
Player 3

Overall Score       84%

Aim Anomaly         91%
Tracking Anomaly    82%
Reaction Anomaly    73%

Suspicious Events
─────────────────
Round 5  - Event #1842
Round 11 - Event #4921
Round 17 - Event #7834
```

**Milestone result:** A user can provide a CS2 demo and receive an interpretable behavioral analysis of the match.

---

## M7 — Temporal Modeling

Investigate whether sequence-based ML models improve behavioral detection.

Instead of only analyzing aggregated features:

```text
Player → Features → Model
```

the system will analyze sequences of consecutive ticks:

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

* [ ] Define fixed-length tick sequences
* [ ] Build a temporal dataset
* [ ] Implement a simple temporal baseline
* [ ] Experiment with 1D CNN models
* [ ] Experiment with LSTM / GRU models
* [ ] Experiment with Transformer-based models
* [ ] Compare temporal and feature-based models
* [ ] Measure inference performance
* [ ] Analyze which sequences trigger predictions
* [ ] Integrate the best model into the Demo Analyzer

**Milestone result:** CS2Guard can analyze player behavior as temporal sequences rather than only aggregated statistics.

---

## M8 — Awareness Analysis

Extend behavioral detection beyond aim to investigate suspicious enemy awareness.

Potential signals include:

* Crosshair alignment with non-visible enemies

* Enemy tracking through geometry

* Prefire timing

* Position anticipation

* Repeated abnormal enemy awareness

* [ ] Determine enemy visibility at each relevant tick

* [ ] Compute crosshair alignment with enemies

* [ ] Detect crosshair tracking of non-visible enemies

* [ ] Analyze pre-aim behavior

* [ ] Analyze prefire timing

* [ ] Account for recently visible enemies

* [ ] Account for teammate information when possible

* [ ] Account for sound-related information when possible

* [ ] Build awareness-related features

* [ ] Define an Awareness Anomaly Score

* [ ] Evaluate false positives on legitimate players

* [ ] Integrate awareness signals into the global suspicion score

The system must account for legitimate information sources such as sound cues, teammate communication, common angles and general game sense.

**Milestone result:** CS2Guard combines aim-related and enemy-awareness signals when evaluating suspicious behavior.

---

## M9 — Real-Time Detection Engine

Adapt the offline machine learning pipeline for streaming gameplay data.

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

* [ ] Define a common data representation for demo and live data
* [ ] Implement a live event buffer
* [ ] Implement sliding temporal windows
* [ ] Convert offline features to incremental features
* [ ] Run ML inference continuously
* [ ] Maintain player state across events
* [ ] Aggregate predictions over time
* [ ] Update player suspicion scores continuously
* [ ] Benchmark feature computation latency
* [ ] Benchmark model inference latency
* [ ] Handle incomplete real-time information
* [ ] Compare offline and online model performance

**Milestone result:** The detection pipeline can operate incrementally on a live stream instead of requiring a complete demo.

---

## M10 — Server-Side Real-Time Anti-Cheat

Integrate the detection engine into a CS2 server-side environment.

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

* [ ] Investigate available CS2 server-side telemetry
* [ ] Build the server data ingestion layer
* [ ] Convert server events into CS2Guard's normalized format
* [ ] Connect live telemetry to the streaming feature engine
* [ ] Run ML inference during matches
* [ ] Maintain a live suspicion score for each player
* [ ] Implement configurable detection thresholds
* [ ] Generate server-side alerts
* [ ] Log suspicious events for later review
* [ ] Store evidence for offline analysis
* [ ] Measure end-to-end detection latency
* [ ] Measure server performance impact
* [ ] Test with multiple simultaneous players
* [ ] Compare real-time results with post-match Demo Analyzer results
* [ ] Build an administrator monitoring interface
* [ ] Evaluate the complete system on controlled matches

**Milestone result:** CS2Guard operates as an experimental real-time, server-side ML behavioral anti-cheat for Counter-Strike 2.

---

# 🏗️ Planned Architecture

```text
CS2Guard/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── labels/
│
├── notebooks/
│   ├── exploration/
│   └── experiments/
│
├── src/
│   └── cs2guard/
│       ├── core/
│       │   ├── game_state/
│       │   └── events/
│       │
│       ├── ingestion/
│       │   ├── demo/
│       │   └── server/
│       │
│       ├── features/
│       │   ├── aim/
│       │   ├── movement/
│       │   ├── combat/
│       │   └── awareness/
│       │
│       ├── detection/
│       │   ├── models/
│       │   ├── inference/
│       │   └── scoring/
│       │
│       ├── evaluation/
│       └── visualization/
│
├── training/
├── models/
├── tests/
│
├── pyproject.toml
├── requirements.txt
└── README.md
```

The architecture separates the source of gameplay data from the behavioral analysis pipeline.

The long-term objective is to allow both demo and server data to use the same internal representation:

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

# 🛠️ Planned Tech Stack

### Core

* Python
* NumPy
* Pandas
* demoparser2

### Machine Learning

* scikit-learn
* XGBoost / LightGBM
* PyTorch

### Data Analysis & Visualization

* Matplotlib
* Jupyter

Additional technologies may be introduced as the real-time component of the project develops.

---

# 📊 Detection Strategy

CS2Guard does not assume that a single suspicious event means that a player is cheating.

Instead, the system progressively aggregates behavioral evidence.

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

For example:

```text
Player

Aim                    0.91
Tracking               0.82
Reaction               0.73
Awareness              0.67
Movement               0.14
                         │
                         ▼
                Suspicion Score
                       0.84
```

The exact scoring strategy will evolve through experimentation and evaluation.

---

# ⚠️ Research Challenges

## False Positives

Highly skilled players can naturally exhibit behaviors that appear statistically unusual.

Therefore:

```text
Anomaly ≠ Cheater
```

A practical detection system must aggregate multiple signals over time and carefully control its false-positive rate.

---

## Dataset Quality

Reliable labels for legitimate and cheating players can be difficult to obtain.

Dataset construction and label quality are therefore treated as major parts of the project rather than simple preprocessing steps.

---

## Player Skill

Gameplay behavior varies significantly depending on player skill.

Future models may need to account for differences between:

* New players
* Average players
* Experienced players
* High-level competitive players

A strong legitimate player should not be classified as suspicious simply because their mechanical performance is unusual compared with an average player.

---

## Context

A suspicious action can often have a legitimate explanation.

For example, aiming toward an enemy behind a wall may result from:

* Sound information
* Teammate communication
* Previous enemy visibility
* Common positioning
* Expected timings
* Prefire
* Game sense

Behavior must therefore be analyzed within its gameplay context.

---

## Offline vs. Online Detection

Information available from a complete demo may not necessarily be available to a real-time server-side detector.

A major research objective of CS2Guard is therefore to determine how much detection performance can be preserved when moving from:

```text
Offline Demo Analysis
          ↓
Real-Time Server Analysis
```

---

## Real-Time Constraints

The server-side system introduces additional requirements:

* Low inference latency
* Efficient feature computation
* Continuous state management
* Multiple simultaneous players
* Limited computational overhead
* Incomplete future information

These constraints will influence both the machine learning models and the software architecture.

---

# 🔬 Research Questions

CS2Guard aims to progressively investigate several questions:

1. Which behavioral features best characterize abnormal aiming behavior?
2. Can suspicious aiming behavior be identified without labeled cheat data?
3. How accurately can supervised models distinguish legitimate and suspicious behavior?
4. Which features contribute most to detection?
5. Do temporal models outperform aggregated statistical features?
6. Can enemy-awareness patterns provide useful signals for detecting wallhack-like behavior?
7. How does player skill affect anomaly detection?
8. How can multiple weak behavioral signals be combined into a reliable suspicion score?
9. How much detection performance is lost when moving from offline analysis to online inference?
10. Can behavioral ML inference operate efficiently enough for real-time server-side deployment?

---

# 🚀 Long-Term Goal

The project progressively moves from behavioral research to a complete real-time detection pipeline:

```text
Demo Parsing
     ↓
Feature Engineering
     ↓
Dataset Construction
     ↓
Anomaly Detection
     ↓
Supervised Detection
     ↓
Demo Analyzer
     ↓
Temporal Modeling
     ↓
Awareness Analysis
     ↓
Streaming Detection
     ↓
Server Integration
     ↓
Real-Time Anti-Cheat
```

The final objective is to investigate whether **server-observable gameplay behavior can provide sufficient information to detect suspicious Counter-Strike 2 players using machine learning**.

---

# 📌 Disclaimer

CS2Guard is an experimental research and educational project.

A high anomaly or suspicion score does **not** constitute proof that a player is cheating. Legitimate players may exhibit unusual behavior, and any practical anti-cheat system must account for uncertainty and false positives.

CS2Guard is not affiliated with or endorsed by Valve Corporation.

---

## 📄 License

License to be determined.
