# CS2Guard

**Machine Learning-Based Behavioral Cheat Detection for Counter-Strike 2**

CS2Guard is an experimental machine learning project designed to detect suspicious player behavior in Counter-Strike 2.

The project starts with **offline analysis of CS2 demo files** to extract gameplay data, engineer behavioral features, build datasets, and train detection models.

The long-term goal is to evolve the project into a **real-time server-side anti-cheat** capable of continuously analyzing player behavior during matches without relying on intrusive client-side monitoring.

> **Status:** 🚧 In Development
> **Development:** 🤖 AI-Assisted

## Quick Start

From the repository root, install with Python 3.11 or newer and run the tests (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest -q
```

To analyze a demo, provide a `.dem` file and a trusted M5 `.joblib` model with its adjacent `.json` metadata. Adapt the input paths to your files:

```powershell
.\.venv\Scripts\cs2guard.exe analyze '.\demo_analyzer\data\raw\train_sources\demo\test.dem' --model '.\demo_analyzer\models\supervised\random_forest_v1.joblib' --output '.\demo_analyzer\data\processed\manual_analysis'
```

Open `demo_analyzer/data/processed/manual_analysis/report.md` for rankings and PNG links; `report.json` contains all scored windows. Without `--output`, reports go to `<demo stem>_analysis/` in the working directory.

A fresh clone includes model metadata, but no trained model or demos: `.joblib` and `.dem` files are ignored by Git. Installation and tests require neither. Inference requires both and never trains a model; see [model prerequisites](docs/demo_analyzer_memory.md#reproducible-validation) for the separate training procedure and dataset requirement.

## Contents

* [Project Goals](#-project-goals)
* [Project Approach](#-project-approach)
* [Quick Start](#quick-start)
* [Roadmap](#️-roadmap)
* [Project Architecture](#️-project-architecture)
* [Tech Stack](#️-tech-stack)
* [Detection Strategy](#-detection-strategy)
* [Research Challenges](#️-research-challenges)
* [Documentation / Technical Memory](#documentation--technical-memory)

---

## 🤖 AI-Assisted Development

AI tools assist with code, tests, documentation and research. Architecture, experiments and integration remain under human review and validation.

---

## 🎯 Project Goals

Investigate whether server-observable gameplay can reveal suspicious behavior without intrusive client-side monitoring:

* Aim movement, crosshair placement and target tracking
* Reaction time, angular velocity and acceleration
* Shooting, player movement, enemy awareness and prefire patterns

Development starts with offline demo research and model training, then targets live server-side detection.

---

## 🧠 Project Approach

### Stage 1 — Offline Demo Analysis

The offline analyzer parses recorded matches, extracts behavioral features and evaluates ML models without real-time constraints.

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

### Stage 2 — Real-Time Server-Side Detection

The planned server-side system adapts the offline pipeline to live telemetry, reusing features and models where possible.

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

## Documentation / Technical Memory

* [Demo Analyzer Project Memory](docs/demo_analyzer_memory.md): implementation, experiments, metrics and validation protocols.
* [Server-Side Project Memory](docs/server_anticheat_memory.md): future real-time architecture and research.

---

# 🗺️ Roadmap

## M1 — Demo Parsing

Build the foundation for extracting structured gameplay data from CS2 demo files.

* [x] Set up the Python project structure
* [x] Integrate a CS2 demo parser
* [x] Load and parse `.dem` files
* [x] Extract match metadata
* [x] Extract players and teams
* [x] Extract rounds
* [x] Extract tick-level player positions
* [x] Extract view angles (yaw / pitch)
* [x] Extract weapon information
* [x] Extract shots, hits, and kills
* [x] Define normalized `Match`, `Player`, `Round`, `Tick`, and `Event` structures
* [x] Add tests for demo parsing

---

## M2 — Aim Feature Engineering

Transform raw gameplay data into measurable aiming behavior.

* [x] Compute crosshair direction
* [x] Compute crosshair-to-target angular distance
* [x] Compute angular velocity
* [x] Compute angular acceleration
* [x] Detect target acquisition
* [x] Measure reaction time
* [x] Measure tracking error
* [x] Measure aim corrections and overshoot
* [x] Detect potential aim snaps
* [x] Associate shots with aiming sequences
* [x] Visualize aim trajectories
* [x] Validate features on selected demo sequences

---

## M3 — Dataset Builder

Create a reproducible pipeline for generating machine-learning-ready datasets from multiple matches.

* [x] Process multiple demo files automatically
* [x] Generate event-level samples
* [x] Generate player-level samples
* [x] Generate temporal windows
* [x] Store extracted features
* [x] Handle missing or invalid data
* [x] Normalize numerical features
* [x] Add support for legitimate / suspicious labels
* [x] Create train / validation / test splits
* [x] Prevent data leakage between matches and players
* [x] Generate dataset statistics
* [x] Define a canonical CS2Guard dataset schema
* [x] Support and normalize external datasets such as CS2CD to the canonical schema

Match-level isolation is enforced for M5 evaluation. Player isolation depends on available identities; CS2CD anonymization prevents guaranteeing disjoint real players across matches.

### External Datasets

The **CS2CD** adapter maps anonymized gameplay and player-level cheat labels to the canonical schema. See [integration details and limitations](docs/datasets/cs2cd.md).

---

## M4 — Anomaly Detection

Build the first ML-based behavioral detector without requiring large amounts of labeled cheating data.

* [x] Establish statistical baselines for legitimate behavior
* [x] Implement Isolation Forest
* [x] Experiment with Local Outlier Factor
* [x] Experiment with One-Class SVM
* [x] Compare anomaly detection approaches
* [x] Generate anomaly scores for individual events
* [x] Generate anomaly scores for players
* [x] Analyze false positives
* [x] Identify the most influential features
* [x] Define an initial suspicion scoring strategy

---

## M5 — Supervised Detection

Train classification models once sufficiently reliable labeled data becomes available.

* [x] Build a labeled dataset
* [x] Establish a baseline classifier
* [x] Train Random Forest models
* [x] Experiment with gradient boosting models
* [x] Tune model hyperparameters
* [x] Measure precision
* [x] Measure recall
* [x] Measure F1-score
* [x] Measure ROC-AUC / PR-AUC
* [x] Analyze the false-positive rate
* [x] Compare supervised and anomaly-detection approaches
* [x] Add model versioning and persistence

On historical CS2CD held-out matches, Random Forest achieves player-match **ROC-AUC 0.7779 / PR-AUC 0.6840**, versus **0.6323 / 0.4624** for LOF. See [M5 results](docs/demo_analyzer_memory.md#result-4) for metrics and threshold trade-offs.

---

## M6 — Demo Analyzer

Turn the machine learning pipeline into a usable offline match-analysis tool.

* [x] Analyze an entire demo from a single command
* [x] Analyze every player in the match, retaining insufficient-data players without a score
* [x] Generate an overall suspicion score per player using the M5 window-score mean
* [x] Generate separate descriptive behavioral indicators with units and availability
* [x] Rank players by suspicion score with deterministic tie ordering
* [x] Identify rounds to inspect from scored windows, retaining unknown round associations
* [x] Identify events to inspect without claiming a validated cheat threshold
* [x] Explain measured features, global importance and signed local RF/tree probability contributions
* [x] Visualize aim sequences selected for inspection
* [x] Generate a JSON and Markdown match analysis report
* [x] Build a CLI for demo analysis

### M6 usage and validation

Use the command in [Quick Start](#quick-start) with a trained M5 bundle. Reports include player rankings, review sequences, JSON/Markdown and aim plots.

**Validation:** M6 is technically complete, with **330 automated tests passing at the latest recorded audit**. Evaluation covers three technical demo recordings and nine presumed-legitimate external demos.

Scores are uncalibrated model outputs; detection accuracy on independently confirmed cheaters remains unvalidated.

See [Demo Analyzer Project Memory](docs/demo_analyzer_memory.md#m6--demo-analyzer) for detailed tests, experiments and scientific limitations.

M7–M10 below are planned; their milestone results describe intended capabilities.

---

## M7 — Temporal Modeling

Investigate whether sequence-based ML models improve behavioral detection.

Models will analyze consecutive ticks:

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

Interpret awareness in context: sound, teammates, common angles and game sense can explain apparent anticipation.

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

# 🏗️ Project Architecture

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

Demo and future server adapters target a shared game-state representation and analysis pipeline:

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

# 🛠️ Tech Stack

## Currently used

### Core

* Python
* NumPy
* pandas
* demoparser2

### Machine Learning

* scikit-learn
* joblib (model persistence)

Gradient boosting uses scikit-learn's `HistGradientBoostingClassifier`.

### Data Analysis & Visualization

* Matplotlib
* pytest (development tests)

## Planned / Under Investigation

* PyTorch and temporal models (M7)
* Live telemetry ingestion and streaming inference (M9–M10)
* XGBoost / LightGBM and Jupyter remain candidates from the original stack; they are not integrated dependencies.

---

# 📊 Detection Strategy

M6 averages M5 window scores per player. The longer-term strategy combines multiple behavioral signals over time:

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

Additional behavioral scores and their combination remain future research.

---

# ⚠️ Research Challenges

* **False positives and skill:** unusual mechanics can be legitimate; compare players across skill levels and aggregate evidence over time.
* **Dataset quality:** reliable labels and independent evaluation populations are difficult to obtain.
* **Gameplay context:** sound, teammate information, previous visibility and expected timings can explain suspicious-looking actions.
* **Offline to online:** live inference must handle incomplete information, player state and concurrent players with low latency and limited server overhead.

```text
Anomaly ≠ Cheater
```

---

# 🔬 Research Questions

1. Which aim and awareness features distinguish suspicious behavior from skill and legitimate context?
2. How do anomaly, supervised and temporal models compare, and which features explain their predictions?
3. How can multiple weak signals be combined while controlling false positives?
4. How much accuracy survives the move to live telemetry, and can inference meet server latency constraints?

---

# 🚀 Long-Term Goal

Investigate whether gameplay telemetry can support an experimental real-time, server-side anti-cheat, progressing through M1–M10 above.

---

# 📌 Disclaimer

CS2Guard is an experimental research and educational project.

A high anomaly or suspicion score does **not** constitute proof that a player is cheating. Legitimate players may exhibit unusual behavior, and any practical anti-cheat system must account for uncertainty and false positives.

CS2Guard is not affiliated with or endorsed by Valve Corporation.
