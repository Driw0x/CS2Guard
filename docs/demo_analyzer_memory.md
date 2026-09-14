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

# Future Milestones

Future sections will document the next Demo Analyzer milestones as they are implemented.

The current milestone is **M6 — Demo Analyzer**.

The objective is to preserve not only **what CS2Guard does**, but also the reasoning and technical decisions that led to the final implementation.
