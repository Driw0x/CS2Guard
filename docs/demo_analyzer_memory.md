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

The Demo Analyzer corresponds to the **v0.x** development phase of CS2Guard.

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

The full dataset build writes each processed match directly to the final CSV outputs instead of keeping all previously processed matches in memory. This reduces peak memory usage during large builds.

A lightweight checkpoint file is updated after each completed match. If the build is interrupted, it can be resumed with `--resume` without rebuilding matches that were already completed. If an interruption occurs during file writing, the output files are rolled back to their previous recorded sizes before the interrupted match is processed again.

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

A full-scale dataset build was also successfully completed using both native demo files and CS2CD data.

The final canonical dataset contains:

* 2 data sources (`demo` and `cs2cd`);
* 320 matches;
* 3,133 players;
* 523,083 events;
* 229,149,465 ticks;
* 405,663 temporal windows;
* 405,663 aim feature samples.

This large-scale build also validated the incremental storage and checkpoint system under realistic dataset volumes.

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
* writing completed matches incrementally to the final dataset files to avoid accumulating all source data in memory;
* using a lightweight per-match checkpoint and `--resume` mechanism for interrupted long-running builds;
* rolling back partially written output files before resuming an interrupted match;
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

# M4 — Anomaly Detection

## Objective

The objective of M4 was to build the first machine-learning detector able to identify unusual aiming behavior without requiring the detector itself to be trained on cheat labels.

M4 uses the aim features generated by the previous milestones and evaluates several unsupervised anomaly-detection approaches.

Conceptually:

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

Labels from CS2CD are used only for evaluation and calibration after anomaly scores have been generated. They are not provided as input features to the unsupervised models.

## Input Features

M4 uses six numerical aim features:

* `mean_angular_speed`;
* `max_angular_speed`;
* `std_angular_speed`;
* `mean_angular_acceleration`;
* `max_angular_acceleration`;
* `std_angular_acceleration`.

Identifiers, source metadata and labels are excluded from the model input.

Before model experimentation, the full feature dataset was validated:

* 405,663 aim feature samples;
* no missing values in the six model features;
* no infinite values in the six model features.

The feature distributions are strongly asymmetric and contain legitimate extreme values, so high velocity or acceleration alone is not treated as evidence of cheating.

## Legitimate Behavior Baseline

A statistical baseline was established from the 282,022 windows labeled `legitimate`.

The legitimate baseline includes the mean, standard deviation, median and upper percentiles of each aim feature.

The 99th percentiles are approximately:

* `mean_angular_speed`: 175.17;
* `max_angular_speed`: 692.76;
* `std_angular_speed`: 191.97;
* `mean_angular_acceleration`: 5,219.80;
* `max_angular_acceleration`: 25,087.75;
* `std_angular_acceleration`: 6,250.98.

Legitimate samples can still exceed these values by a large margin. The baseline is therefore used as statistical context rather than as a set of direct cheat thresholds.

## Isolation Forest

Isolation Forest was implemented as the first anomaly-detection baseline.

The six features are standardized before inference, and the model produces:

* a window-level anomaly score;
* a binary anomaly prediction;
* player-level aggregated scores.

On the full dataset:

* windows: 405,663;
* player-match observations: 3,138;
* anomalous windows: 41,133.

At player level, suspicious players received higher average anomaly scores than legitimate players:

```text
legitimate mean   = -0.082159
suspicious mean   = -0.064996
```

This indicates that the aim features contain a measurable anomaly signal, although the separation remains limited.

## Local Outlier Factor

Local Outlier Factor was evaluated using the same standardized feature representation.

On the full dataset:

* windows: 405,663;
* player-match observations: 3,138;
* anomalous windows: 1,216.

LOF produced highly asymmetric raw scores. Most windows remain close to a LOF score of approximately 1, while a small number of isolated samples receive extremely large scores.

At player level:

```text
mean anomaly score

legitimate mean   = 266.428996
suspicious mean   = 494.548139

median

legitimate        = 1.038084
suspicious        = 1.049517
```

The anomalous-window ratio was also higher for suspicious players:

```text
legitimate mean ratio   = 0.002257
suspicious mean ratio   = 0.007781
```

These results show that suspicious players contain more locally unusual aim behavior, while also demonstrating that raw LOF values are sensitive to a small number of extreme samples.

## One-Class SVM

One-Class SVM with an RBF kernel was also evaluated.

To keep the experiment computationally practical, the model is trained on a deterministic sample of at most 20,000 feature windows and then used to score the complete dataset.

The baseline uses:

```text
kernel = rbf
gamma = scale
nu = 0.05
```

On the complete dataset:

* windows: 405,663;
* player-match observations: 3,138;
* anomalous windows: 15,295.

Player-level mean and median anomaly scores were both higher for suspicious players:

```text
                 mean       median
legitimate      -14.34      -16.01
suspicious       -7.97      -13.87
```

## Model Comparison

The three approaches were compared using ROC-AUC at player level.

The evaluated player aggregations were:

* `mean_anomaly_score`;
* `max_anomaly_score`;
* `anomalous_window_ratio`.

The best results were:

```text
LOF / mean_anomaly_score                ROC-AUC = 0.648464
Isolation Forest / mean_anomaly_score   ROC-AUC = 0.632018
One-Class SVM / mean_anomaly_score      ROC-AUC = 0.615009
```

The complete comparison showed that `mean_anomaly_score` performed best for all three models.

LOF was therefore retained as the strongest M4 anomaly-detection baseline.

The ROC-AUC remains moderate, so M4 does not establish that anomaly detection alone is sufficient for reliable cheat classification.

## False-Positive Analysis

The highest-scoring legitimate players were inspected using their most anomalous LOF windows.

A common pattern was that only a very small number of windows produced extremely large LOF scores.

These windows did not necessarily exceed the legitimate 99th percentile for any individual feature.

This indicates that LOF primarily detects unusual multivariate combinations of aim features rather than simple single-feature extremes.

This is an important limitation for interpretation:

```text
Anomalous behavior ≠ cheating
```

A legitimate player can occupy a locally sparse region of feature space and receive a high anomaly score.

## Feature Ablation

Feature influence was evaluated by removing one input feature at a time and recomputing the LOF player-level ROC-AUC.

Baseline:

```text
ROC-AUC = 0.648464
```

Results:

```text
Removed feature                  ROC-AUC    Baseline drop
std_angular_acceleration         0.642331    +0.006133
max_angular_acceleration         0.648252    +0.000212
max_angular_speed                0.649006    -0.000542
mean_angular_acceleration        0.649695    -0.001231
mean_angular_speed               0.652057    -0.003593
std_angular_speed                0.652337    -0.003873
```

`std_angular_acceleration` was the most influential individual feature in this experiment.

However, the differences are small. M4 therefore keeps all six features and treats anomaly detection as primarily dependent on multivariate feature combinations rather than on a single dominant measurement.

## Shot-Level Anomaly Scores

Each temporal aim window is centered on an individual shot.

The LOF output can therefore be exposed directly as a shot-level anomaly score while preserving the link to the original temporal window through `window_id`.

The generated shot-level output contains:

* 405,663 scored shot events;
* 405,663 unique windows;
* 1,216 events classified as anomalous by LOF.

The raw event-level LOF mean is strongly influenced by extreme outliers. Event scores are therefore useful for locating unusual aim sequences, but player-level aggregation remains more appropriate for the initial suspicion score.

## Player-Level Anomaly Scores

Anomaly scores are aggregated per match and player.

The player-level output includes:

* number of analyzed windows;
* mean anomaly score;
* maximum anomaly score;
* anomalous-window ratio.

The full dataset contains:

* 3,138 player-match observations;
* 3,133 unique `player_id` values;
* 1,801 legitimate labeled player-match observations;
* 1,307 suspicious labeled player-match observations;
* 30 unlabeled player-match observations from native demo data.

The difference between 3,138 player-match observations and 3,133 unique player IDs is expected because some player identifiers appear in more than one match-level observation.

## Initial Suspicion Score

M4 introduces an initial player suspicion score derived from the LOF mean anomaly score.

Because raw LOF values can become extremely large, the raw anomaly score is not used directly as the final interpretable value.

Instead:

```text
LOF mean anomaly score
        ↓
Percentile relative to legitimate players
        ↓
Suspicion score in [0, 100]
```

A score of 95 means that the player's LOF mean anomaly score is higher than approximately 95% of the legitimate calibration population.

It does not mean that the player has a 95% probability of cheating.

On the labeled dataset:

```text
                 mean       median
legitimate       50.03       50.03
suspicious       64.85       73.74
```

Several legitimate players still receive scores close to 100, confirming that the suspicion score must not be interpreted as proof of cheating or as an automatic enforcement threshold.

## Implementation Structure

M4 introduces the anomaly-detection layer:

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

Supporting scripts provide:

* legitimate baseline analysis;
* anomaly-model execution;
* model comparison;
* false-positive inspection;
* feature ablation;
* suspicion-score generation;
* shot-level anomaly-score generation.

## Testing

M4 is covered by automated tests for:

* Isolation Forest execution;
* Local Outlier Factor execution;
* LOF feature subsets used for ablation;
* One-Class SVM execution;
* missing feature validation;
* invalid numerical feature validation;
* suspicion-score generation.

At the end of M4, the complete automated test suite passes.

The three anomaly-detection models were also executed on the complete 405,663-window dataset.

## Technical Decisions

Important decisions made during M4 include:

* using only behavioral aim features as unsupervised model inputs;
* excluding identifiers, source metadata and labels from anomaly-model features;
* using CS2CD labels only for evaluation and calibration;
* standardizing features before anomaly-detection experiments;
* comparing Isolation Forest, Local Outlier Factor and One-Class SVM;
* training One-Class SVM on a deterministic sample to keep the experiment computationally practical;
* using ROC-AUC for cross-model comparison because raw anomaly-score scales differ substantially;
* evaluating scores at player level rather than treating every temporal window as an independent player;
* retaining LOF as the strongest M4 baseline with a player-level ROC-AUC of 0.648464;
* preserving all six aim features after ablation because individual feature effects were small;
* treating high anomaly scores as unusual behavior rather than direct evidence of cheating;
* exposing temporal-window scores as shot-level event scores;
* converting the LOF player score into a legitimate-relative percentile for the initial 0–100 suspicion score;
* avoiding a ban or cheat-classification threshold during M4.

## Result

M4 is complete and validated.

CS2Guard can now assign anomaly scores to individual shot-centered aim events and aggregate those signals into player-level anomaly and suspicion scores.

Among the evaluated unsupervised approaches, Local Outlier Factor produced the strongest player-level separation:

```text
ROC-AUC = 0.648464
```

The result demonstrates that suspicious and legitimate players exhibit measurable differences in the current aim-feature space, but the separation is not strong enough to treat anomaly detection as a standalone cheat classifier.

The Demo Analyzer has progressed from:

> "How can behavioral features be converted into a reproducible dataset?"

to:

> "Can unusual aiming behavior be detected automatically, and how can that evidence be aggregated into an interpretable player-level suspicion signal?"

M4 provides the anomaly-detection baseline required for the supervised experiments planned in M5.

---

# Future Milestones

Future sections will document the next Demo Analyzer milestones as they are implemented.

The current milestone is **M5 — Supervised Detection**.

The objective is to preserve not only **what CS2Guard does**, but also the reasoning and technical decisions that led to the final implementation.
