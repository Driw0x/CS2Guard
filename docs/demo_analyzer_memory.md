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

The current implementation computes statistics over selected temporal windows, not a sliding rolling-statistics series. These temporal features summarize short aim sequences and provide more stable information for later analysis.

The temporal calculations are designed around demo tick data; their interpretation must remain aware of CS2's tick/subtick recording behavior.

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

# M5 — Supervised Detection

## Objective

The objective of M5 was to evaluate supervised classification once reliable legitimate and suspicious labels became available through the canonical dataset.

M5 reuses the same six aim features evaluated during M4, but unlike anomaly detection, supervised models are explicitly trained using the available CS2CD labels.

Conceptually:

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

A central requirement of M5 is to preserve match-level isolation between training and evaluation data so that windows from the same match cannot appear in both sets.

## Labeled Dataset

A dedicated supervised dataset is generated from the canonical aim-feature dataset.

Only samples with a valid label are retained:

```text
legitimate
suspicious
```

Unlabeled native-demo samples are excluded from supervised training.

The supervised dataset contains:

* 397,487 labeled samples;
* 317 matches;
* 3,108 players;
* 6 numerical aim features.

The label distribution is:

```text
legitimate    282,022
suspicious    115,465
```

The six model features are the same as those used during M4:

* `mean_angular_speed`;
* `max_angular_speed`;
* `std_angular_speed`;
* `mean_angular_acceleration`;
* `max_angular_acceleration`;
* `std_angular_acceleration`.

Identifiers such as `match_id`, `player_id`, `window_id` and the label itself are preserved for dataset management and evaluation but are not provided as model inputs.

## Train / Test Split

The supervised dataset is split using match-level grouping.

Instead of randomly distributing individual windows between train and test sets, all samples belonging to the same match remain in the same partition.

This prevents a model from being trained on windows from a match that also appears in the held-out test set.

The fixed split uses:

```text
Train
306,315 samples
253 matches

Test
91,172 samples
64 matches
```

The training label distribution is:

```text
legitimate    215,434
suspicious     90,881
```

The test label distribution is:

```text
legitimate     66,588
suspicious     24,584
```

The split uses a fixed random state so that all M5 experiments are evaluated using the same held-out matches.

## Baseline Classifiers

M5 first establishes two baseline classifiers.

### Dummy Classifier

A `DummyClassifier` using the training class prior provides a trivial reference.

On the held-out test set:

```text
accuracy = 0.7304
```

The model predicts no suspicious samples at the default decision rule:

```text
Precision = 0.0000
Recall    = 0.0000
F1-score  = 0.0000
ROC-AUC   = 0.5000
PR-AUC    = 0.2696
FPR       = 0.0000
```

The PR-AUC corresponds to the positive-class prevalence in the held-out test set and therefore provides a useful baseline for later models.

### Logistic Regression

Logistic Regression is used as the first learned supervised baseline.

The classifier is placed after a `StandardScaler` inside a scikit-learn pipeline so that feature scaling is fitted only on the training data.

Initial results are:

```text
accuracy  = 0.7306
Precision = 0.5102
Recall    = 0.0214
F1-score  = 0.0410
ROC-AUC   = 0.5547
PR-AUC    = 0.3230
FPR       = 0.0076
```

The accuracy is almost identical to the Dummy baseline, while recall remains extremely low.

This demonstrates why accuracy alone is not sufficient for evaluating the anti-cheat classification problem.

## Random Forest

Random Forest was introduced as the first nonlinear supervised model.

The initial configuration uses:

```text
n_estimators     = 100
max_depth        = 20
min_samples_leaf = 5
```

The initial held-out results are:

```text
accuracy  = 0.7340
Precision = 0.5336
Recall    = 0.1078
F1-score  = 0.1794
ROC-AUC   = 0.5933
PR-AUC    = 0.3813
FPR       = 0.0348
```

Random Forest improves substantially over Logistic Regression in recall, F1-score and PR-AUC, indicating that nonlinear interactions between the aim features contain useful supervised information.

## Histogram Gradient Boosting

`HistGradientBoostingClassifier` was evaluated as a second nonlinear supervised model.

It was selected instead of the classic `GradientBoostingClassifier` because the histogram-based implementation is better suited to the approximately 300,000 training samples used by M5.

The initial configuration uses:

```text
learning_rate  = 0.1
max_iter       = 100
max_leaf_nodes = 31
```

Initial held-out results are:

```text
accuracy  = 0.7356
Precision = 0.5593
Recall    = 0.0915
F1-score  = 0.1572
ROC-AUC   = 0.5934
PR-AUC    = 0.3791
FPR       = 0.0266
```

The initial Gradient Boosting model has slightly higher precision and a lower false-positive rate than the initial Random Forest, while Random Forest has higher recall, F1-score and PR-AUC.

## Evaluation Metrics

M5 introduces a common evaluation layer for all supervised models.

The evaluated metrics include:

* precision;
* recall;
* F1-score;
* ROC-AUC;
* PR-AUC;
* false-positive rate;
* confusion-matrix counts.

The suspicious class is treated as the positive class:

```text
0 = legitimate
1 = suspicious
```

PR-AUC is implemented using average precision rather than direct trapezoidal integration of the precision-recall curve.

This ensures that a constant-score classifier produces a baseline corresponding to the positive-class prevalence.

For the held-out test dataset:

```text
positive prevalence ≈ 0.2696
```

and the Dummy classifier therefore produces:

```text
PR-AUC = 0.2696
```

## Hyperparameter Tuning

Random Forest and Histogram Gradient Boosting were tuned using randomized search.

The held-out 64-match test set is not used during hyperparameter selection.

Instead, tuning operates only on the 253 training matches using grouped cross-validation.

Conceptually:

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

PR-AUC / average precision is used as the primary tuning metric because suspicious samples are less frequent than legitimate samples and because ranking suspicious behavior is more informative than raw accuracy.

### Random Forest Tuning

The best Random Forest cross-validation result is:

```text
Best CV PR-AUC = 0.4471
```

with:

```text
n_estimators     = 150
min_samples_leaf = 5
max_features     = sqrt
max_depth        = 15
class_weight     = None
```

### Histogram Gradient Boosting Tuning

The best Histogram Gradient Boosting result is:

```text
Best CV PR-AUC = 0.4457
```

with:

```text
max_leaf_nodes    = 63
max_iter          = 150
learning_rate     = 0.1
l2_regularization = 1.0
class_weight      = balanced
```

Internal early stopping is disabled during grouped cross-validation so that an additional random validation split cannot reintroduce match-level leakage.

Random Forest achieved the slightly better cross-validation PR-AUC and was retained as the primary M5 supervised model candidate.

## Tuned Model Evaluation

After tuning, both selected configurations are retrained on the complete 253-match training set and evaluated once on the held-out 64-match test set.

### Tuned Random Forest

The tuned Random Forest produces:

```text
Precision = 0.5669
Recall    = 0.0929
F1-score  = 0.1596
ROC-AUC   = 0.5932
PR-AUC    = 0.3818
FPR       = 0.0262
```

Compared with the untuned Random Forest, the tuned model becomes more conservative:

```text
Precision increases
FPR decreases
Recall decreases
```

### Tuned Histogram Gradient Boosting

The tuned Histogram Gradient Boosting model produces:

```text
Precision = 0.3437
Recall    = 0.4488
F1-score  = 0.3893
ROC-AUC   = 0.5950
PR-AUC    = 0.3827
FPR       = 0.3164
```

The balanced class weighting strongly increases suspicious-sample recall, but this comes with a much larger false-positive rate.

This demonstrates that a model with a useful ranking score does not necessarily have an appropriate default classification threshold.

## False-Positive and Threshold Analysis

M5 therefore evaluates the tuned models over multiple probability thresholds.

The analyzed thresholds range from:

```text
0.10
to
0.90
```

For each threshold, CS2Guard measures:

```text
precision
recall
F1-score
false-positive rate
false positives
true positives
```

The analysis demonstrates the expected trade-off:

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

For example, the tuned Random Forest at threshold `0.50` produces:

```text
Precision = 0.5669
Recall    = 0.0929
F1-score  = 0.1596
FPR       = 0.0262
```

The tuned Histogram Gradient Boosting model reaches a similar false-positive region around threshold `0.70`:

```text
Precision = 0.5666
Recall    = 0.0967
F1-score  = 0.1652
FPR       = 0.0273
```

By contrast, its default threshold of `0.50` produces:

```text
Recall = 0.4488
FPR    = 0.3164
```

This shows that substantially higher recall currently requires an unacceptable increase in false positives.

No final enforcement or cheat-classification threshold is selected during M5.

The held-out test set is used to characterize model behavior, not to repeatedly optimize a production threshold.

## Supervised vs. Anomaly Detection

M5 also introduces a direct held-out comparison between supervised learning and the anomaly-detection approach developed during M4.

The original M4 experiments and the supervised M5 event-level metrics were not directly comparable because they used different evaluation conditions and aggregation levels.

A new common evaluation therefore uses:

```text
same 253 training matches
same 64 held-out test matches
same six aim features
same player-match aggregation
```

Local Outlier Factor is evaluated in novelty mode.

It is fitted only on training features and then used to score held-out samples, without using cheat labels during fitting.

Supervised event probabilities and LOF anomaly scores are then aggregated by match and player.

The common held-out evaluation contains:

```text
637 player-match observations
```

Results are:

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

The supervised approaches therefore substantially outperform the held-out LOF baseline on the current labeled aim-feature dataset.

Random Forest and Histogram Gradient Boosting remain very close to each other.

Random Forest is retained as the primary M5 model because it achieved the best PR-AUC during grouped cross-validation and the highest held-out player-level PR-AUC.

The result does not imply that anomaly detection is obsolete.

Unsupervised scoring can still remain useful when labels are unavailable, for exploratory analysis, or as an additional signal in later suspicion-score aggregation.

## Model Persistence and Versioning

M5 introduces persistence for trained supervised models.

The selected Random Forest can be saved as a versioned model bundle:

```text
models/supervised/
├── random_forest_v1.joblib
└── random_forest_v1.json
```

The `.joblib` file contains the trained scikit-learn model.

The JSON metadata records information required to identify and reproduce the model, including:

* model name;
* version;
* input features;
* label mapping;
* hyperparameters;
* random state;
* training sample and match counts;
* held-out test sample and match counts;
* event-level evaluation metrics;
* player-level ROC-AUC and PR-AUC.

The model metadata keeps:

```text
decision_threshold = None
```

because M5 does not select a final operational threshold.

The model is therefore persisted primarily as a probabilistic suspicion-scoring model rather than as an automatic cheat-enforcement classifier.

## Implementation Structure

M5 introduces a dedicated supervised-learning layer:

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

The main implementation responsibilities are separated into:

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

Supporting scripts provide:

* labeled-dataset generation;
* baseline and model training;
* hyperparameter tuning;
* tuned-model evaluation;
* threshold analysis;
* supervised-versus-anomaly comparison;
* model persistence.

## Testing

M5 extends the automated test suite to cover:

* labeled-dataset construction;
* invalid labels and numerical values;
* match-level train / test isolation;
* supervised feature and target preparation;
* baseline classifier creation and training;
* Random Forest creation and training;
* Histogram Gradient Boosting creation and training;
* tuned-model creation and training;
* precision, recall, F1-score, ROC-AUC and PR-AUC evaluation;
* PR-AUC behavior for a constant classifier;
* configurable threshold evaluation;
* invalid threshold handling;
* threshold analysis;
* grouped cross-validation without match overlap;
* Random Forest tuning;
* Histogram Gradient Boosting tuning;
* player-level score aggregation;
* held-out LOF scoring;
* supervised-versus-anomaly comparison;
* model persistence and reload behavior.

The supervised test suite passes at the end of M5.

Real experiments were also executed on the complete labeled dataset and the fixed held-out match split.

## Technical Decisions

Important decisions made during M5 include:

* reusing the six M4 aim features so that supervised and anomaly-detection experiments remain comparable;
* excluding unlabeled samples from supervised training;
* preserving identifiers for grouping while excluding them from model inputs;
* splitting train and test data by match rather than by individual window;
* keeping a fixed held-out 64-match test set throughout M5;
* fitting preprocessing only on training data;
* using DummyClassifier as the trivial performance reference;
* using Logistic Regression as the first learned supervised baseline;
* evaluating Random Forest and Histogram Gradient Boosting as nonlinear tabular models;
* using precision, recall, F1-score, ROC-AUC and PR-AUC rather than relying on accuracy;
* using average precision for PR-AUC;
* using grouped cross-validation for hyperparameter tuning;
* optimizing hyperparameters using PR-AUC rather than accuracy;
* disabling internal Histogram Gradient Boosting early stopping during grouped tuning;
* analyzing decision thresholds separately from model ranking performance;
* treating false-positive rate as a critical anti-cheat evaluation metric;
* avoiding selection of a production enforcement threshold from the held-out test set;
* comparing supervised and unsupervised approaches on the same held-out matches and player-level aggregation;
* retaining Random Forest as the primary M5 supervised model;
* keeping Histogram Gradient Boosting as a strong alternative model;
* persisting the selected model together with reproducibility metadata;
* keeping the persisted M5 model threshold-free so that later Demo Analyzer logic can determine how scores should be aggregated and interpreted.

## Result

M5 is complete and validated.

CS2Guard can now train, tune, evaluate and persist supervised behavioral classifiers using labeled aim-feature data.

The initial event-level results demonstrate that classification remains difficult when each shot-centered window is treated independently.

However, player-level aggregation on the held-out test matches produces substantially stronger separation.

The primary M5 Random Forest reaches:

```text
ROC-AUC = 0.7779
PR-AUC  = 0.6840
```

at player-match level.

For comparison, held-out Local Outlier Factor reaches:

```text
ROC-AUC = 0.6323
PR-AUC  = 0.4624
```

This demonstrates that the available cheat labels provide substantial additional information beyond purely unsupervised anomaly detection.

At the same time, threshold analysis confirms that detection performance and false-positive control remain in tension.

The supervised model is therefore treated as a source of behavioral suspicion evidence rather than as proof that a player is cheating.

The Demo Analyzer has progressed from:

> "Can unusual aiming behavior be detected automatically?"

to:

> "Can labeled behavioral data improve suspicious-player ranking, and can the resulting model be evaluated and persisted without introducing avoidable data leakage?"

M5 provides the supervised detection model required for the usable offline Demo Analyzer planned in M6.

---

# M6 — Demo Analyzer

## Scope and reference state

The audit and implementation on 2026-10-14 preserve the README roadmap: M6 is offline demo analysis. Server-side streaming remains M9/M10; `server_side/` is unchanged.
The initial branch was `main`, with no tracked local changes. The project uses a setuptools `src` layout and canonical `cs2guard_demo` imports.
All Python sources, the 20 historical scripts, tests, package/test configuration, architecture documentation and persisted M5 metadata were inspected.
Model artifacts, datasets and research outputs were retained.

The existing `.venv` uses Python 3.13.1, pytest 9.1.1, NumPy 2.5.2, pandas 3.0.5, scikit-learn 1.9.1, demoparser2 0.42.0, Matplotlib 3.11.1 and joblib 1.6.0.
The system Python lacks demoparser2; commands therefore use the project environment.
The installed persisted model is a 150-tree RandomForestClassifier, with classes `[0, 1]` and the six expected feature names in their training order.
It loads without a compatibility warning. Its model and JSON files remain unchanged.

The baseline before any code changes was **179 passed, 0 failed, 0 skipped**.
An earlier default sandbox run had **163 passed and 16 fixture setup errors**, caused by an inaccessible system temporary directory, not application failures.
A repository-local `--basetemp` established the clean baseline. This workaround was later removed at the user's request; final tests use native pytest system temporary directories with approved filesystem access.

## Confirmed audit findings and actions

Paths in this table are relative to `demo_analyzer/` unless stated otherwise.

| File / symbol | Problem | Evidence | Action | Risk |
|---|---|---|---|---|
| `src/cs2guard_demo/parser/events.py`, `utils/logger.py` | Dead placeholders | Empty files, no Python/documentation references, no exported implementation | Deleted only these two files | Low |
| `parser/demo_parser.py` pandas import; `scripts/parse_demo.py`, `visualize_aim.py` `ROOT_DIR` | Unused import/variables | AST and reference checks show declaration only | Removed | Low |
| `DemoParser` shots/hits/kills/ticks/players/teams/rounds | Empty backend frames raise `KeyError` | Controlled backend returns `DataFrame()` without columns | Preserve empty output schemas/lists | Low; nonempty behavior unchanged |
| `DatasetBuilder.build_temporal_windows`, `build_canonical_temporal_windows` | Duplicate shot/tick rows corrupt windows | Repeated shot duplicates one `window_id`; repeated tick can satisfy row count without complete timeline | Deduplicate shots, reject ambiguous tick windows | Medium; invalid/duplicate input behavior deliberately corrected |
| Same window builders | Repeated full-tick scans | Entire tick frame filtered per shot | Group and sort once, select bounds using `searchsorted` | Low; exact feature results tested |
| `dataset/builder.py`, `dataset/adapters/demo.py` | Infinity replacement crashes in installed pandas | Regression fixture reproduces `IndexError: pop index out of range` with `pd.NA` | Replace infinity with NaN before existing exclusion | Low; exclusion semantics preserved |
| `dataset/adapters/cs2cd.py` | Infinite telemetry survives normalization | Synthetic NaN/Inf data | Remove invalid required telemetry | Low |
| `scripts/build_dataset.py::append_dataframe` | CSV headers differ between sources; empty chunks affect later header | Different optional fields and ordering in Demo/CS2CD fixtures | Stable existing-field union, skip empty chunks, reject unknown fields/incompatible resume headers | Medium; legacy interrupted CSVs may need rebuilding |
| `scripts/build_dataset.py::build_demo_chunk/build_cs2cd_chunk` | Identical feature pipeline | Only adapter construction differs | Reuse `build_chunk(builder, adapter)` | Low |
| `dataset/statistics.py::generate_dataset_statistics` | Canonical datasets count zero players | Function reads only `steamid`, absent from canonical schema | Prefer `player_id`, retain legacy fallback | Low |
| `dataset/labels.py`, `statistics.py`, `detection/anomaly.py`, `scripts/analyze_false_positives.py` | Duplicate labels/six-feature lists | Identical constants in multiple modules | Import existing schema/normalization constants | Low; order checked |
| `scripts/validate_demo.py` | Empty windows raise `KeyError: window_id` | Test runs actual script `main()` with empty data | Reuse conditional window count | Low |
| `supervised/comparison.py::aggregate_player_scores` | Series aligns by unrelated pandas index | Dataset index `[10,11]`, scores index `[0,1]` yield NaN | Positional `np.asarray(scores)` assignment | Low; ndarray scripts unchanged |
| `supervised/evaluation.py::evaluate_predictions` | Single-class targets return undefined metrics | One-class ROC-AUC/FPR produce NaN | Explicit error unless both 0/1 classes exist | Low; valid historical metrics unchanged |
| `scripts/train_supervised.py`, `evaluate_tuned_supervised.py::print_metrics` | Identical metric printing | Same fields/formats | Reuse existing evaluation module function | Low; output checked |
| `visualization/aim.py::plot_aim_trajectory` | No saved output for M6 | Figure closes without export | Optional `output_path` and `distance_label`; default behavior unchanged | Low |
| M1–M5 test cases | Genuine duplicate work | Event test repeats exact multi-demo fixture; detector/training tests repeat setup/assertions | Merge event assertions; parameterize model cases | Low; independent coverage retained |

The following similarities were reviewed and **retained**, rather than treated as confirmed dead code:

| Symbol / family | Reason to retain |
|---|---|
| Legacy DatasetBuilder event/window API vs DemoAdapter canonical API | Different identity schemes, output structures and public callers; merging would introduce conversions |
| M4 vs M5 player aggregation | M4 uses six identity keys and mean/max/anomaly ratio; M5 uses match/player and mean score |
| Transductive M4 LOF vs held-out M5 novelty LOF | Different evaluation tasks; training-only scaler in held-out path is essential |
| M2 acquisition/tracking/reaction/correction/snap helpers | Public exports, independent tested behaviors and experimental visualization callers |
| Historical scripts and persisted research artifacts | Distinct experiments, documented usage and reproducibility value |
| Similar adapter fixtures | Source formats and normalization responsibilities differ |
| Full parser player roster, including possible warmup participants | Historical semantics may be useful; M6 retains players and marks absent evidence instead of silently discarding them |

Scientific formulas, angular wrapping, tick units, population standard deviations (`ddof=0`), scaler fitting, feature ordering, model parameters, grouped splitting, LOF score signs and ECDF calibration remain unchanged for valid historical data.
No production threshold or new calibration is introduced. Invalid duplicate/non-finite windows and undefined metrics now fail or are excluded explicitly.

## Coverage and test consolidation

| Functional area | Coverage checked | Before | After |
|---|---|---:|---:|
| M1 parser | Valid normalized payloads, players/events/rounds/ticks, latest match start, missing files, backend errors, empty data, Match with/without ticks | 7 | 14 |
| M2 geometry and plots | ±180° wrapping, directions/distances, speed/acceleration/time, acquisition/response, tracking/corrections/overshoot/snaps, shot association, invalid inputs, real PNG export | 95 | 96 |
| M3 datasets/adapters/scripts | Canonical IDs/labels, multi-match windows, finite data, exact numeric features, irregular tick time, duplicates/incomplete windows, normalization, splits without match leakage, statistics, stable CSV/resume rollback | 42 | 61 |
| M4 anomalies | IF/LOF/OCSVM training/scoring, feature ordering/casting, finite values, score direction, reproducibility, identity aggregation, ECDF ties/calibration errors | 7 | 18 |
| M5 supervised | Baselines/RF/HGB/tuned models, finite normalized probabilities, grouped CV/split reproducibility, thresholds, metrics, player means, positional scores, held-out LOF, persistence and feature order | 28 | 46 |
| M6 analysis | Controlled end-to-end M1–M5 integration, all-player roster, exact means/ranking, rounds/events, plots/reports, model compatibility, partial/empty data, exact tree contributions and CLI | 0 | 39 |
| **Total** | **No skipped tests** | **179** | **274** |

M1–M5 gain **57 cases** and remove **one exact duplicate**, for **235 cases** after consolidation.
`test_event_level_samples` is merged into `test_process_multiple_demos`, retaining all assertions.
Three detector tests become one parameterized test covering the same three detectors; four training tests become one parameterized test covering the same four paths.
M6 adds 39 cases in `test_analysis.py`. `test_build_dataset_script.py` is the only other new test file.
The 91 existing M2 feature tests are retained; similar-looking cases cover different algorithms or boundaries.

New tests first exposed the pandas infinity crash and canonical player-statistics omission; both were fixed and verified.
One newly added RF persistence assertion initially used exact equality and failed at `1.11e-16`; tolerance `1e-12` now accounts for parallel floating-point tree summation.
Two M6 expectations were updated after adding explicit partial-data counters. No historical successful test was weakened to hide a product regression.

Automated tests remain small and synthetic. No suite test requires a demo download, external CS2CD data or costly full-dataset training.
CS2CD anonymization still prevents guaranteeing real-player disjointness across different matches; match-level disjointness is tested.
Historical full-dataset model experiments were not repeated.

## Implementation and scientific interpretation

Three package files implement M6: `analysis.py`, `cli.py`, `__main__.py`; `pyproject.toml` registers `cs2guard = cs2guard_demo.cli:main`.
Matplotlib, already used and installed for M2, is declared as a runtime dependency because reports require it.
Missing setuptools build support in the existing environment initially blocked a no-build-isolation install; the ordinary isolated build installs only the build requirements already declared by the project.
No additional modeling, reporting or CLI dependency is introduced.

The pipeline reuses DemoAdapter/DemoParser, DatasetBuilder, M2 geometry/plots, M4 `prepare_features`, M5 bundle loading and M5 player aggregation.
It checks nonempty `.dem` input, adjacent metadata, feature names/order/dimensions, class mapping, probability output shape/range and optional recorded extraction settings.
It never fits a model during analysis. Historical extraction settings are fixed at 32 ticks and 64 Hz, matching the training scripts; missing metadata settings are explicitly documented as a compatibility limitation.

Every parser-roster player, telemetry/event actor and event victim is retained. Players without finite complete shot windows have null scores and an explanation.
Players with windows are ordered by descending M5 mean, then canonical ID; unscored players follow without a rank.
The full JSON retains every scored window and six measured features. Round association uses the shot tick; absent completed-round context remains null and crossing windows are flagged.
Events in the same actor/weapon/round during the following two ticks provide nearby inspection context, not causal proof of a shot-to-hit relationship.

The three highest-scoring windows per player are selected for inspection, even when all scores are low. This is a display limit, not a validated suspicion threshold.
Round inspection priority is the maximum window score in each completed round, not a calibrated round probability.
Speed and acceleration indicators are arithmetic means of window feature means, in degrees/s and degrees/s²; they are not combined with model outputs.
Tracking measurements use M2 only when an observed victim has concurrent telemetry. Otherwise the plot explicitly references the shot aim direction.
Reaction has no observed visibility stimulus and remains unavailable.
Global RF feature importance and raw window values explain the available measurements.
For the persisted M5 RF and native decision trees, local contributions also decompose the existing prediction:
each split contributes the child-minus-parent class-1 probability to its feature. The root baseline plus these signed changes telescopes to the leaf probability.
Changes and baselines are averaged across forest trees; player contributions are averaged across windows, exactly matching M5 score aggregation.
Input conversion uses the same float32 precision as scikit-learn tree inference. Reconstruction is asserted to tolerance `1e-12`.
This is an arithmetic explanation of the unchanged model, not a new detector or calibration. It depends on split order and is neither causal attribution nor SHAP.
Unsupported estimator families explicitly retain null local contributions; their measured features and global importance remain separate.
There is no new behavioral anomaly submodel, arbitrary weighted score, ECDF calibration on unlabeled players or cheating conclusion.

`report.json` is machine-readable; `report.md` provides ranking, behavioral values, round priorities, review sequence bounds/events/features, image links and interpretation limits.
CLI exit 0 means at least one player has a score; usable partial analyses are explicitly labelled `partial`.
`complete` requires windows for every roster player, all eligible shots scored, and no missing/crossing round context. `partial` retains usable scores while exposing those gaps; `insufficient_data` means no player can be scored.
Exit 2 means invalid input, missing/incompatible model, parsing/output failure or no scored window. No-data reports retain null scores rather than fabricated zeros.

## Reproducible validation

The [README Quick Start](../README.md#quick-start) covers Python 3.11+ installation and basic analysis. The detailed acceptance protocol is retained here; the README keeps the eleven M6 checklist items.

Inference requires a trusted M5 `.joblib` bundle and adjacent `.json` metadata; model bytes and demos are ignored by Git and are not shipped in a fresh clone. Installation and automated tests require neither.
If a bundle must be built separately, the historical command below trains M5 from the existing `demo_analyzer/data/processed/supervised_dataset.csv`; it is not part of inference:

```powershell
Set-Location demo_analyzer
..\.venv\Scripts\python.exe scripts/save_supervised_model.py
Set-Location ..
```

Commands executed from the repository root:

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

Final complete suite: **274 passed, 0 failed, 0 skipped**. `pip check`, syntax compilation, canonical imports and CLI help pass.
All **75 Python files** parse; **26 non-namespace implementation modules** and **20 scripts** import successfully. No configured lint/type-check tool exists.
Historical training scripts were imported and covered through library tests, not executed on the full dataset. They retain their expected `demo_analyzer/` working directory and data prerequisites.
The multi-source builder's help and rollback/header paths are exercised, without overwriting research datasets.

### Initial acceptance protocol

These checks map to the eleven README criteria in their original order. The recorded initial results and later corrections remain in the sections below. Automated checks use a controlled parser, actual M1–M5 code, a small persisted classifier and real PNG output.

For targeted checks, run from the repository root after installing the project with its `dev` extra:

```powershell
$python = '.\.venv\Scripts\python.exe'
$analysis = 'demo_analyzer/tests/test_analysis.py'
```

| Criterion | Targeted automated command | Acceptance check |
|---|---|---|
| 1. Single command | `& $python -m pytest -q $analysis -k 'end_to_end or cli_analysis'` | Fixture scores, JSON/Markdown and PNGs agree; inference never fits a model. |
| 2. Every player | `& $python -m pytest -q $analysis -k 'end_to_end or insufficient_data or single_player'` | All five fixture players remain present; unavailable scores are null with reasons. |
| 3. Overall scores | `& $python -m pytest -q $analysis -k 'end_to_end or probability_uses or incompatible_model or invalid_model'` | Fixture window scores are 0/1 and player means 0.5/1; invalid inputs are rejected. |
| 4. Behavioral indicators | `& $python -m pytest -q $analysis -k end_to_end` | Physical units, measurements and unavailable indicators are explicit. |
| 5. Ranking | `& $python -m pytest -q $analysis -k ranking` | Ties and reordered input preserve ranking; unscored players follow scored players. |
| 6. Round inspection | `& $python -m pytest -q $analysis -k 'end_to_end or single_player'` | Bounds, round IDs, null associations and boundary flags match the fixture. |
| 7. Event inspection | `& $python -m pytest -q $analysis -k 'end_to_end or single_player'` | Shot IDs, bounds and nearby events agree; unrelated events are excluded; selection is capped at three per player. |
| 8. Explanations | `& $python -m pytest -q $analysis -k 'end_to_end or contributions'` | Baseline plus signed contributions reconstructs window/player scores for RF and native trees; other model families remain unavailable. |
| 9. Visualizations | `& $python -m pytest -q $analysis demo_analyzer/tests/test_aim_visualization.py -k 'end_to_end or export'` | Nonconstant PNGs have positive dimensions and an accurate victim/shot-direction reference. |
| 10. Match report | `& $python -m pytest -q $analysis -k 'end_to_end or insufficient_data'` | Saved JSON equals returned data; Markdown image links resolve and missing data stays visible. |
| 11. CLI | `& $python -m pytest -q $analysis -k cli` | Help and scoring succeed; invalid input, missing model and zero scored windows exit 2. |

After the analysis command above, inspect the generated report without rerunning inference:

```powershell
$LASTEXITCODE # Check immediately after cs2guard analyze.
$out = '.\demo_analyzer\data\processed\m6_validation'
$report = Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $out 'report.json') | ConvertFrom-Json
$report.summary
$report.players | Format-Table rank,player_id,player_name,score,window_count,status
$report.players[0].behavioral_scores | ConvertTo-Json -Depth 5
$report.rounds | Format-Table number,start_tick,end_tick,window_count,max_window_score
$report.review_events | Select-Object player_id,round_number,shot_tick,start_tick,end_tick,score
$report.review_events[0] | ConvertTo-Json -Depth 8
$report.feature_importance
$report.players[0].model_contributions
$report.windows[0].model_contributions
$report.limitations
$report.review_events.visualization | Format-Table path,reference,sample_count
Test-Path (Join-Path $out 'report.json')
Test-Path (Join-Path $out 'report.md')
Get-ChildItem -LiteralPath $out -Filter '*.png'
Invoke-Item (Join-Path $out 'report.md')
.\.venv\Scripts\cs2guard.exe analyze '.\missing.dem' --model '.\demo_analyzer\models\supervised\random_forest_v1.joblib' --output $out
$LASTEXITCODE # Expected: 2 and an explicit "Analysis failed" message.
```

Compare these fields against the recorded local-demo results below: finite 0–1 player means, canonical IDs, descending ranks, explicit unavailable indicators, round-context counts, score reconstruction and report/PNG consistency. The initial run used shot-direction references only; later observed-victim plots belong to the robustness audit.

### Real local demo

The installed `cs2guard` command actually runs on `demo_analyzer/data/raw/train_sources/demo/test.dem` (312,377,735 bytes) with the unchanged M5 RF bundle.
The analysis is repeated during implementation; displayed player means and ranking agree to six decimal places.
The final report status is **partial** because some windows lack completed-round context or cross a boundary; all ten players nevertheless have scores.

| Recorded item | Result |
|---|---:|
| Players / scored players | 10 / 10 |
| Normalized telemetry rows | 1,624,992 |
| Normalized events | 2,966 |
| Scored 32-tick windows | 2,272 |
| Completed rounds | 21 |
| Unscored eligible shots | 0 |
| Windows with no completed-round association | 42 |
| Windows crossing a round boundary | 36 |
| Saved PNG review plots | 30 |
| Highest / lowest player mean | 0.263435 / 0.237090 |

Every player's saved score is checked against the mean of its saved window scores to tolerance `1e-12`.
Root baseline plus signed path contributions is also checked against all 2,272 RF window probabilities; maximum error is `4.44e-16`.
The saved JSON contributions reconstruct all 2,282 window/player scores with maximum error `5.55e-16`.
Ranking, canonical player IDs, 32-tick bounds, valid round bounds and actor/weapon/round event associations are checked against the generated JSON.
All 30 PNGs exist, have positive dimensions and nonconstant pixels. A real plot is visually inspected; its trace, tick axis, degree units, shot marker and shot-direction reference are readable.
All selected real sequences use the shot-direction fallback. Observed-victim tracking is verified in the controlled end-to-end fixture, but not demonstrated among these real selected candidates.
The JSON and Markdown are retained locally under `demo_analyzer/data/processed/m6_validation/`, excluded from Git as generated outputs.
The missing-demo CLI case is also executed and exits 2 with an explicit error.

### Temporary directory correction

The `.pytest_tmp*` folders originated from this task's explicit `--basetemp=demo_analyzer/.pytest_tmp*` commands and older manual test runs.
`pytest.ini`, `pyproject.toml` and all repository scripts contain no such override. Fixtures use native `tmp_path`.
All subsequent test commands omit `--basetemp` and use pytest's native temporary storage (`E:\Temp` on this host).
The sandbox's remapped temporary directory is inaccessible for pytest cleanup; approved execution access solves that environment problem without changing fixtures or project features.
After confirming task test sessions finished and checking actual Python/pytest process command lines, ten `.pytest_tmp*` directories are removed exclusively within the verified repository paths.
No other data is deleted. `.gitignore` additionally protects `.pytest_tmp*/` against accidental tracking; this is a guard, not the fix.
Complete native pytest execution is followed by a directory check: **zero `.pytest_tmp*` directories at repository root or under `demo_analyzer/`**.

## Remaining validation limits

The software pipeline is implemented and tested; M6 is **not declared entirely validated**.
Calibrated behavioral probabilities and a validated operational threshold do not exist in M1–M5 and are not invented here.
Local RF/tree path contributions reconstruct predictions, but do not establish causal importance or support non-tree estimator families.
Ordinary-demo accuracy requires independent labels and validation of the CS2CD-to-demo domain shift. Model metadata omits extraction/version details, so structural compatibility does not establish scientific validity.
Real target tracking and fully associated round context remain partially demonstrated as described above.
No new full-dataset training, held-out model comparison or live server validation is claimed. No commit or push is performed.

# M6 — Targeted robustness validation (2026-10-14)

This follow-up validates the existing implementation, preserving all earlier local edits and the original `m6_validation/` outputs. Generated evidence lives under `demo_analyzer/data/processed/m6_robustness_20261014/`: `reference/`, three `before/` analyses, three `after/` analyses, a repeated `test.dem` analysis in `repeat/`, and independent checks in `audit/<demo stem>/`. Each audit includes `validation.json`, `raw_round_events.json`, and CSV/JSON inventories of every unassigned and crossing window. `corrections.diff` isolates this task's changes to three implementation files from the pre-existing implementation.

## A. Diagnosis

For `test.dem`, the exact `partial` condition is 42 windows without a completed-round association and 36 windows crossing a boundary. All ten players are scored; all 2,272 eligible shots generate complete finite windows. No eligible shot or generated feature row is omitted. Missing tracking and absent visibility stimuli do not determine this status.

All 42 unassigned shots lie strictly after a `round_end` and before the next `round_start`. The gap is independently confirmed by the parsed `round_officially_ended` events, which coincide with the next start; duplicate official-end events are present in the raw parser output. Thirty-six windows contain the completed round's final ticks followed by post-result ticks; six windows lie entirely inside a transition. No window contains two different active rounds. The 36 crossing windows are a subset of the 42, not an additional set. Shots occur 3–434 ticks after the preceding end. No missing start/end event explains these 42 cases.

The six entirely transitional windows are LuchoG at shot tick 27003; Syzel at 107079, 107085 and 130735; and squeezie at 26993 and 27011. The CSV inventory records every player's canonical and source IDs, name, window bounds, shot tick, reconstructed seconds (`tick / 64`, not wall-clock timestamps), preceding round/end, following round/start and score. Completed-round IDs are normalized sequentially after `begin_new_match`; raw event `round` values differ between start and end events and are not substituted into these IDs. The first retained interval begins at the latest `begin_new_match`, tick 5787, immediately after the first live start at 5786.

The completed-interval contract is inclusive `[start_tick, end_tick]`. A post-result shot has no active completed-round association under this contract. Its preceding/following round context is recorded in the diagnostic inventory; `round_number` remains null rather than silently expanding the contract. All 42 scores remain in their player's arithmetic mean.

Historical M3 windows contain 32 unique consecutive player ticks ending at the shot (31 tick intervals, 0.484375 seconds at the historical 64 Hz). They do not filter by round. The 36 end-crossing windows follow this definition and include post-result aim samples. Their largest angular step exactly across the end is 3.390503569 degrees; the largest position step is 3.359422697 game units. These measurements do not demonstrate spawn discontinuities or corrupt features. Changing this population would change the M5 input definition and require a separate compatibility/evaluation study; no such change or retraining is justified here.

Two defects affect real outputs:

* `weapon_fire` uses names such as `weapon_ak47`, while `player_hurt`/`player_death` use `ak47`. Exact comparison excluded every hit/kill from all scored windows, including all selected plots. Removing only the optional prefix during M6 comparison restores the observed contacts without changing the stored weapons or M3/M5 features.
* Printing Unicode player names to redirected Windows `cp1252` stdout raises `UnicodeEncodeError` after reports are written. Both additional real demos originally exit 1 for this reason. Unencodable console characters now use backslash escapes; JSON/Markdown keep the full Unicode identities.

Synthetic regressions also demonstrate a boundary flag missed when both window endpoints are unknown but a completed round lies inside; a missing subsequent `round_start` reuses a previous round start, creating overlapping intervals; and duplicate end events shift normalized round numbers. Boundary detection now checks actual interval boundaries. Parsing deduplicates end ticks and requires a subsequent start strictly after the preceding end. These parser edge cases do not change the three real demos' completed intervals.

## B. Changes

* `analysis.py`: optional weapon-prefix comparison, boundary detection, explicit reasons for unavailable tracking, and counted round limitations in JSON/Markdown. No score, feature, candidate-selection or window definition changes.
* `cli.py`: safe encoding of console player names.
* `parser/demo_parser.py`: two-line round-pairing correction described above.
* `test_analysis.py` and `test_demo_parser.py`: 18 additional synthetic cases. Two existing tests gain assertions for reporting and extreme finite tree inputs.
* README and this memory: record the new evidence while retaining the historical validation results.
* `.gitignore`: exclude this validation's generated reports, images, logs and reference snapshots.

Existing positional M5 aggregation, ranking with an ID tie break, class-column selection, feature ordering, finite-value rejection, tree float32 traversal and descriptive/scientific labels already work correctly.

## C. Tests and environment

Baseline: **274 passed in 22.07 s**. Six regression cases fail against the saved original implementation: Unicode stdout, both weapon-prefix directions, an interior boundary with unknown endpoints, a missing round start and a duplicate end. After correction, the final targeted M1/M2/M6 run passes **76 tests in 20.68 s**; the complete M1–M6 suite passes **292 tests in 22.59 s**, with no failures or skips. Targeted runs include all M6 end-to-end integration tests. New cases also cover inclusive event bounds, windows with no round context, and missing/single/duplicate victim telemetry. Existing tie, input-order, identity, positional aggregation, invalid-model and deterministic fixture tests remain intact.

The first sandbox run yields 207 passed / 67 fixture errors because pytest cannot use the remapped temporary directory. Setting process-local `TEMP` and `TMP` to the native system directory `E:\Temp` resolves this without changing fixtures or pytest configuration. No `.pytest_tmp*` directory is created. The Python launcher also prints `Failed to find real location of E:\Python\python.exe` on stderr in this execution environment, including successful commands; the three corrected CLI exits are nevertheless 0. No parser exception is recovered or hidden.

All 36 importable package modules import successfully. Syntax compilation, `pip check`, installed/module CLI help, invalid-demo CLI exit 2 and `git diff --check` pass. No configured lint/type-check command exists. No dependency installation, model training, download, commit or push occurs.

## D. Real analyses

All three locally available `.dem` files are analyzed before and after correction. None is downloaded or modified.

| Demo | Scored / detected players | Generated / scored windows | Completed rounds | No round | Crossing | Player scores min / mean / max | Selected / PNG | Tracking plots | CLI after | Seconds before / after |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| `test.dem` | 10 / 10 | 2272 / 2272 | 21 | 42 | 36 | 0.237090 / 0.251237 / 0.263435 | 30 / 30 | 4 | 0 | 143.85 / 37.75 |
| `2026-09-01_19-31-10_17_de_inferno_team_Kay_vs_team_YY.dem` | 10 / 11 | 3104 / 3104 | 23 | 129 | 42 | 0.235112 / 0.250149 / 0.259392 | 30 / 30 | 7 | 0 | 52.10 / 50.56 |
| `2026-09-02_19-03-20_18_de_ancient_team_alxska-_vs_team_Palmoleeve.dem` | 10 / 10 | 2800 / 2800 | 24 | 106 | 58 | 0.240015 / 0.249423 / 0.261043 | 30 / 30 | 9 | 0 | 60.58 / 40.06 |

Every status remains `partial`; both JSON and Markdown are present and consistent. All normalized eligible shots have scored windows; no score is NaN or infinite. Inferno retains Steam ID `76561198125674008` with telemetry but zero eligible shots and a null score. Inferno's unassigned windows consist of 38 between completed rounds, four after the last completed end but before the next start, and 87 in a final round starting at tick 188682 with no end event. Ancient's 106 unassigned windows are between completed intervals. Every real crossing is an end boundary; no real window crosses the next round's start. Timings include different concurrent validation work and are not a performance benchmark.

## E. Independent before/after checks

All 8,176 windows are rebuilt from normalized raw telemetry and events. Their six feature values match the saved reports exactly. The persisted RF predicts these raw inputs again: maximum difference from reported window scores is `2.78e-16`; independently calculated player means differ by at most `2.78e-17`. Baseline plus feature-path contributions reconstructs every window/player score within `6.11e-16`. No unexpected before/after difference exceeds `1e-12`: identities, window bounds, completed intervals, scores, rank, candidate IDs and contributions are conserved.

For `test.dem`, linkage changes from 2,272 shots only to 2,272 shots plus 320 hit and 148 kill associations. Across all windows, 347 have a linked observed victim with enough concurrent telemetry; four occur in the top-three-per-player selection. The other 1,925 windows, including 26 selected sequences, have no contact satisfying the existing attacker/weapon/round/two-tick conditions. Inferno has 515 available tracking windows (seven selected); Ancient has 507 (nine selected). No real linked target lacks sufficient concurrent telemetry, and no later available victim is excluded by the first-contact choice in these runs. Synthetic missing/duplicate victim cases retain an explicit shot-direction fallback.

The data passed to M2 are checked for every one of the 90 final plots: actor, target, sample ticks, bounds, title and angular geometry. Independent float64 geometry differs by at most `1.12e-6` degrees from the current mixed float32/float64 calculation; no M2 formula is changed. All plots are 1100×600 RGBA with nonconstant data, correct image links and finite values. Four representative plots are visually inspected across the three demos, including observed-victim and shot-direction references. Only the expected 4/7/9 tracking PNGs differ from baseline. Reaction remains unavailable without observed visibility stimuli. Tracking uses body-position geometry, without visibility, eye-height or hitbox reconstruction; a hit just after the shot can legitimately fall outside the pre-shot plot.

| `test.dem` player, unchanged rank | Windows | Mean before / after (six decimals) | No round / crossing | Additive contribution of unassigned / crossing windows to player mean |
|---|---:|---|---|---|
| 1 MDMiro | 159 | 0.263435 / 0.263435 | 2 / 2 | 0.002642 / 0.002642 |
| 2 KeaZy | 120 | 0.260880 / 0.260880 | 2 / 2 | 0.004495 / 0.004495 |
| 3 LuchoG | 188 | 0.258100 / 0.258100 | 9 / 8 | 0.013038 / 0.011063 |
| 4 YEL7OWORE | 375 | 0.256915 / 0.256915 | 2 / 2 | 0.001172 / 0.001172 |
| 5 samu777- | 258 | 0.256882 / 0.256882 | 6 / 6 | 0.005533 / 0.005533 |
| 6 NthraX | 250 | 0.252927 / 0.252927 | 11 / 11 | 0.012024 / 0.012024 |
| 7 -s4ndor | 286 | 0.244495 / 0.244495 | 0 / 0 | 0 / 0 |
| 8 squeezie | 225 | 0.244215 / 0.244215 | 4 / 2 | 0.004866 / 0.002441 |
| 9 Syzel | 139 | 0.237428 / 0.237428 | 6 / 3 | 0.009635 / 0.004724 |
| 10 Draw0x | 272 | 0.237090 / 0.237090 | 0 / 0 | 0 / 0 |

An additive contribution is the sum of the subset's scores divided by the player's total window count, not the subset mean. The overlapping subsets must not be added together.

The repeated installed-CLI run of `test.dem` finishes in 33.63 s. Deep comparison of every report field finds no semantic difference at absolute tolerance `1e-12`; all 30 PNGs are byte-identical. JSON is not byte-identical: parallel RF floating-point summation (`n_jobs=-1`) changes window scores by at most `2.22e-16`. No report field is omitted from this repeat comparison, and ranking remains unchanged. Exact binary reproducibility of floating scores is not claimed.

SHA-256 manifests before and after match for all three source demos, model metadata and model bytes. The RF model hash remains `322ea64dddf12164824a5269371429ae87f714f7a2c0bf89c2eb10185cc09d11`.

## F. Manual reproduction

From the repository root, use the existing environment and native system temporary directory:

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

Expected: 76 targeted / 292 total tests; CLI exit 0 for every local demo; counts and scores in the table above; unchanged model hash; no `.pytest_tmp*` directories. Inspect the generated Markdown, PNGs and the exact per-window CSV evidence referenced above. To repeat a demo, call the same installed CLI into another unique directory and compare JSON recursively with numeric absolute tolerance `1e-12`; all other fields must match.

## G. Validation status and limits

* Technical M6 validity: validated for the existing inference contract and tested errors.
* Data and association integrity: partial. Known transitions and an unfinished round remain explicitly outside completed-round coverage. Nearby contacts are temporal context, not causal shot attribution.
* Multiple-demo robustness: validated on all three available local demos, not on arbitrary recording formats or populations.
* Scientific score validity on ordinary demos: not validated. Independent labels, domain-shift evaluation, appropriate calibration data and extraction-version metadata remain absent. No new operational threshold, probability of cheating, verdict or retraining is introduced. Removing `weapon_` does not infer undocumented aliases such as silenced-weapon differences in hurt events.

# M6 — Presumed-legitimate external evaluation

`cs2guard_demo.validation` evaluates local demos under
`demo_analyzer/data/raw/held_out/legitimate/` with the existing frozen RF bundle.
It calls M6 directly, retaining scores, features, player identities, quality counts
and RF path contributions. The optional `review_plots=False` argument suppresses
per-player aim PNGs for this study; ordinary M6 calls retain their existing plots.
No feature, window, scoring, training or calibration contract changes.

The protocol is saved **before** external inference: model/metadata SHA-256,
exact source hashes and a source ZIP, Git state, Python/dependency versions,
32-tick/64-Hz settings, ordered features, arithmetic-mean aggregation, labels,
bootstrap settings and the historical descriptive threshold grid **0.10–0.90**.
The comparator is `>=`, as in M5; **0.50 is not an operational threshold**.
Outputs live under ignored `demo_analyzer/data/processed/validation_legitimate/`, with separate
content-addressed match attempts and study directories. Repeating the command
reuses reports only after receipt/hash, identities, finite values, counts and
player-mean checks. Invalid attempts and previous studies remain available.

Labels default to `presumed_legitimate`, based solely on the user's declaration.
Optional `--manifest` JSON maps relative demo paths to provenance and player
overrides. Unknown players remain in descriptive outputs and are excluded from
flag denominators. A confirmed label requires an individual override with evidence:

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

The principal unit is the **player-match**. Descriptive summaries retain missing
values, sample standard deviations and exploratory tail percentiles. Fixed-seed
95% percentile bootstrap intervals resample matches, preserving within-match
dependence; a second analysis resamples connected matches sharing persistent IDs.
With fewer than two independent components, that interval is unavailable.
Wilson intervals are explicitly IID sensitivity references, not corrected bounds.
Zero/all flag bootstrap intervals are degenerate and cannot establish a population
FPR. The metric is `presumed_legitimate_flag_rate`, not a confirmed FPR.

Existing `supervised_dataset.csv` supplies legitimate CS2CD feature distributions,
including a separately reported full reference and the exact historical M5 test
split. The persisted model scores that test reference without fitting. Window
features/scores and equal-weight player-match means are reported separately.
No historical dataset is regenerated or downloaded if the input is absent.
Exact native-demo duplicates are excluded; filename/identity overlaps with the
three historical M6 reports are recorded. CS2CD anonymization and unavailable
independent session identifiers still prevent complete independence guarantees.

From the repository root, run or resume the entire study with the same command:

```powershell
.\.venv\Scripts\python.exe -m cs2guard_demo.validation
```

Read the most recent study and open its report/figures:

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

Scientific conclusions require the recorded real-study results below. This
negative-only study cannot measure external recall, ROC-AUC or PR-AUC, validate
calibration, identify cheaters or demonstrate generalization.

## Real external study — 2026-10-14

All **nine** available new demos were analyzed: **90 scored/detected player-match
observations**, **57 observable Steam identities**, **29,010 scored windows**, no
failed/excluded demos and no unscored players. All 90 labels are presumed legitimate
from the user's declaration; none is independently confirmed or marked unknown.
All reports are `partial`: **685 windows lack completed-round context** and
**415 cross a round boundary**, retained under the historical extraction contract.
Scored players have 114–858 windows (median 304.5).

Player-match score mean is **0.249250**, median **0.244984**, sample SD **0.014424**,
minimum/maximum **0.225987/0.295459**, Q25/Q75 **0.238631/0.255644** and
P90/P95/P99 **0.267843/0.279872/0.289260**. Tail percentiles remain exploratory
with 90 observations. Match means range **0.242817–0.256175**. Ten identities recur
in multiple matches; their observed within-player score ranges are
**0.001584–0.041159**, descriptive evidence only.

The mean-score 95% match-bootstrap interval is **[0.246899, 0.251793]**, conditional
on treating nine matches as independent. **All nine matches form one connected
component through repeated players**, including one identity present in every
match. The dependence-preserving connected bootstrap therefore has **no estimable
interval**. The narrow match-bootstrap interval must not be interpreted as reliable
population precision.

At fixed thresholds **0.10 and 0.20**, flags are **90/90 player-matches and 9/9
matches**. At **0.30–0.90, including 0.50**, flags are **0/90 and 0/9**. No label or
data exclusions enter these denominators. Zero/all flag bootstrap intervals are
degenerate. At zero flags, IID Wilson sensitivity references are **[0, 4.09%]** for
90 observations and **[0, 29.91%]** for nine matches; neither adjusts for the actual
shared-player dependence. Zero observed flags establishes neither zero FPR nor
cheater sensitivity.

No exact duplicate occurs among the nine files or against the three historical M6
demos. **Six Steam identities overlap the historical technical reports**. These
recordings are new matches, not a wholly new player cohort; filename/session and
CS2CD anonymization uncertainties remain. M3 discovery is restricted to
`train_sources`; this evaluation writes elsewhere and never invokes training.
The existing M5 input contains **397,487 CS2CD windows only** and no observable
external match/player-ID overlap; anonymization still limits real-person checks.

CS2CD comparison uses **282,022 legitimate windows / 1,801 player-matches** for
the full descriptive feature reference, and **66,588 legitimate windows / 402
player-matches over 64 historical test matches** for frozen-RF score comparisons.
Window feature median shifts are small relative to reference IQR
(approximately **−0.099 to +0.010 IQR**); equal-weight player-match feature means
give **−0.060 to +0.040 IQR**. External player scores are lower and less dispersed:
mean/median **0.249250/0.244984**, versus **0.284594/0.274929** for legitimate CS2CD
test observations. Similar medians do not imply identical tails: window P99 maximum
speed is **829.28 versus 692.76 degrees/s**, and P99 speed SD is **231.30 versus
191.97 degrees/s**. These are descriptive distribution differences, not significance
tests, operational improvements or evidence of detection degradation.

The highest player score is **0.295459**, from 525 windows with **98.86%** completed
round coverage (six unassigned and five crossing windows). Five highest observations
retain feature extrema and signed RF path contributions in the report; none is
identified as cheating. Four aggregate PNG figures were visually inspected.

Automated baseline: **292 passed** after correcting inaccessible sandbox temporary
storage with process-local `TEMP`/`TMP`. Complete suite after adding the external
evaluation tests: **330 passed** (38 new cases); syntax compilation and `pip check`
passed. Tests cover empty/invalid inputs, duplicates, manifests, missing/nonfinite
values, rates/ties, clustered resampling, reference comparisons, preserved reports,
resume, failure isolation and frozen-model integrity. Artifacts include JSON/CSV
statistics, a Markdown report, four figures, frozen source/protocol evidence and
per-demo M6 reports. Model and metadata remain unchanged; no commit or push.
Real resume reused all nine verified match reports and reproduced statistics
exactly. Independent model reload/inference on all 29,010 saved feature rows gave
a maximum score difference of **2.776e-16**; maximum RF contribution reconstruction
error was **6.661e-16**, both below **1e-12**. This check does not independently
repeat source parsing. Final evidence is in
`demo_analyzer/data/processed/validation_legitimate/run-0ae2814792ffd726/verification.json`;
`latest.json` points to the study report and figures.

**Evidence classification:** technical processing completed; validation labels
remain presumed; score concentration is observed on this sample; threshold flags
are measured descriptively; distribution differences are observable; external
cheater detection, calibration and generalization remain **unvalidated**.

# Future Milestones

M7–M10 remain future work. M6 validation limitations above remain visible rather than being converted into unsupported scientific claims.
