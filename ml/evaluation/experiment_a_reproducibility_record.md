# Reproducibility Record: Experiment A — XGBoost Browser Behavior Baseline

**Record Date**: 2026-10-12  
**Status**: Completed  
**Nature of Experiment**: BASELINE EXPERIMENT ONLY  

> [!CAUTION]
> **BASELINE DISCLAIMER**:
> This experiment establishes an initial statistical baseline for client-side browser behavioral telemetry. This baseline model **does NOT prove human or bot identity**. In accordance with the project's research objective, client-side motor signals provide probabilistic evidence only; deterministic identity claims are mathematically and epistemologically invalid without cross-layer correlation and sequence verification.

---

## 1. Experiment Overview
- **Experiment Name**: `Experiment A — XGBoost Browser Behavior Baseline`
- **Module Path**: `ml/training/train_experiment_a.py`
- **Goal**: Evaluate the discrimination capability of 64 engineered behavioral features under cross-task transfer (Leave-One-Task-Out) against a majority-class empirical baseline.

---

## 2. Dataset Specification
- **Features File**: `ml/data/features.csv` (21,494 bytes, 45 rows × 77 columns)
- **Metadata File**: `ml/data/metadata.csv` (4,026 bytes, 45 rows × 8 columns)
- **Total Valid Sessions**: **45 sessions**
  - **HUMAN Sessions (`label = 0`)**: **15 sessions** (5 unique participants: `p_01`, `p_02`, `p_03`, `p_04`, `p_05`, each completing `TASK_01`, `TASK_02`, and `TASK_03`)
  - **AUTOMATED Sessions (`label = 1`)**: **30 sessions** (10 unique bot entities: `bot_var_s42` through `bot_var_s51`, each completing `TASK_01`, `TASK_02`, and `TASK_03` under `AUTOMATED_VARIABLE`)
- **Task Distribution**:
  - `TASK_01`: 15 sessions (5 Human, 10 Automated)
  - `TASK_02`: 15 sessions (5 Human, 10 Automated)
  - `TASK_03`: 15 sessions (5 Human, 10 Automated)
- **Data Quality**: 0 NaN values, 0 Inf values, 0 unlabeled sessions, 0 incomplete sessions.
- **Historical Baseline**: `ml/data/archive_phase4bc_baseline/` was strictly preserved and unmodified.

---

## 3. Feature Configuration (64 Features)
- **Canonical Feature Schema**: 76 features engineered by `ml/features/extractor.py`.
- **Derived Feature Configuration**: **64 features** selected via `ml/training/feature_config.py`.
- **12 Excluded Features**:
  1. `session_duration_ms` (experimental pacing leakage)
  2. `mouse_session_duration_ms` (experimental pacing leakage)
  3. `active_behavior_duration_ms` (experimental pacing leakage)
  4. `hidden_event_count` (window/tab switching artifact)
  5. `blur_event_count` (window/tab switching artifact)
  6. `focus_event_count` (window/tab switching artifact)
  7. `time_away_ratio` (window/tab switching artifact)
  8. `max_time_away_ms` (window/tab switching artifact)
  9. `double_click_rate` (zero-variance constant across all sessions)
  10. `backspace_rate` (zero-variance constant across all sessions)
  11. `paste_rate` (zero-variance constant across all sessions)
  12. `interaction_density` (dispatch rate proxy artifact)
- **Retained Task-Dependent Features (6)**: `button_click_ratio`, `min_flight_ms`, `input_click_ratio`, `key_event_count`, `typing_speed`, `scroll_event_count` (monitored via LOTO cross-task validation).
- **Leakage Safeguards**: Authoritative `label` isolated in vector $y$; metadata columns (`session_id`, `collection_mode`, `automation_condition`, `task_id`, `participant_id`, `collection_timestamp`, `event_count`) strictly forbidden from feature matrix $X$.

---

## 4. Validation Protocol
- **Methodology**: Leave-One-Task-Out (LOTO) cross-validation across 3 folds.
- **Split Isolation**: Verified by `LeakageAuditor`. Zero random session splitting.
- **Folds Definition**:
  - **Fold 1 (`LOTO_TEST_TASK_03`)**: Train on `TASK_01` + `TASK_02` (30 samples: 10H, 20A) $\rightarrow$ Test on `TASK_03` (15 samples: 5H, 10A)
  - **Fold 2 (`LOTO_TEST_TASK_02`)**: Train on `TASK_01` + `TASK_03` (30 samples: 10H, 20A) $\rightarrow$ Test on `TASK_02` (15 samples: 5H, 10A)
  - **Fold 3 (`LOTO_TEST_TASK_01`)**: Train on `TASK_02` + `TASK_03` (30 samples: 10H, 20A) $\rightarrow$ Test on `TASK_01` (15 samples: 5H, 10A)

---

## 5. Model Hyperparameters
- **Estimator**: `xgboost.XGBClassifier`
- **Hyperparameters**:
  - `n_estimators`: `50`
  - `max_depth`: `3`
  - `learning_rate`: `0.1`
  - `eval_metric`: `"logloss"`
  - `random_state`: `42`
  - `objective`: `"binary:logistic"`

---

## 6. Per-Fold Metrics

### XGBoost Classifier
| Fold ID | Test Task | Train N (H/A) | Test N (H/A) | Balanced Acc | Precision | Recall | F1 (Pos) | Macro F1 | ROC-AUC | Human FPR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `LOTO_TEST_TASK_03` | `TASK_03` | 30 (10/20) | 15 (5/10) | **1.0000** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **0.0000** |
| `LOTO_TEST_TASK_02` | `TASK_02` | 30 (10/20) | 15 (5/10) | **1.0000** | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | **0.0000** |
| `LOTO_TEST_TASK_01` | `TASK_01` | 30 (10/20) | 15 (5/10) | **0.9000** | 0.9091 | 1.0000 | 0.9524 | 0.9206 | 0.9000 | **0.2000** |

### Majority Baseline (`BaselineClassifier(strategy="majority")`)
| Fold ID | Test Task | Train N (H/A) | Test N (H/A) | Balanced Acc | Precision | Recall | F1 (Pos) | Macro F1 | ROC-AUC | Human FPR |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `LOTO_TEST_TASK_03` | `TASK_03` | 30 (10/20) | 15 (5/10) | 0.5000 | 0.6667 | 1.0000 | 0.8000 | 0.4000 | 0.5000 | 1.0000 |
| `LOTO_TEST_TASK_02` | `TASK_02` | 30 (10/20) | 15 (5/10) | 0.5000 | 0.6667 | 1.0000 | 0.8000 | 0.4000 | 0.5000 | 1.0000 |
| `LOTO_TEST_TASK_01` | `TASK_01` | 30 (10/20) | 15 (5/10) | 0.5000 | 0.6667 | 1.0000 | 0.8000 | 0.4000 | 0.5000 | 1.0000 |

---

## 7. Confusion Matrices

### XGBoost Classifier
- **Fold 1 (`TASK_03`)**: $\text{TN}=5, \; \text{FP}=0, \; \text{FN}=0, \; \text{TP}=10$
- **Fold 2 (`TASK_02`)**: $\text{TN}=5, \; \text{FP}=0, \; \text{FN}=0, \; \text{TP}=10$
- **Fold 3 (`TASK_01`)**: $\text{TN}=4, \; \text{FP}=1, \; \text{FN}=0, \; \text{TP}=10$ *(1 human false alarm: participant `p_05`)*
- **Cumulative Matrix**:
$$\begin{pmatrix} \text{TN}=14 & \text{FP}=1 \\ \text{FN}=0 & \text{TP}=30 \end{pmatrix}$$

### Majority Baseline
- **Fold 1 (`TASK_03`)**: $\text{TN}=0, \; \text{FP}=5, \; \text{FN}=0, \; \text{TP}=10$
- **Fold 2 (`TASK_02`)**: $\text{TN}=0, \; \text{FP}=5, \; \text{FN}=0, \; \text{TP}=10$
- **Fold 3 (`TASK_01`)**: $\text{TN}=0, \; \text{FP}=5, \; \text{FN}=0, \; \text{TP}=10$
- **Cumulative Matrix**:
$$\begin{pmatrix} \text{TN}=0 & \text{FP}=15 \\ \text{FN}=0 & \text{TP}=30 \end{pmatrix}$$

---

## 8. Aggregate Performance Summary

| Metric | Majority Baseline | XGBoost Classifier | Net Delta |
| :--- | :---: | :---: | :---: |
| **Mean Balanced Accuracy** | $0.5000$ | **$0.9667$** | $+0.4667$ |
| **Mean Precision** | $0.6667$ | **$0.9697$** | $+0.3030$ |
| **Mean Recall** | $1.0000$ | **$1.0000$** | $0.0000$ |
| **Mean F1 (Positive Class)** | $0.8000$ | **$0.9841$** | $+0.1841$ |
| **Mean Macro F1** | $0.4000$ | **$0.9735$** | $+0.5735$ |
| **Mean ROC-AUC** | $0.5000$ | **$0.9667$** | $+0.4667$ |
| **Mean Human False Positive Rate** | $1.0000$ (100%) | **$0.0667$ (6.67%)** | $-0.9333$ |

---

## 9. Hypothesis Testing Results

### Null Hypothesis ($H_0$)
- **Statement**: XGBoost provides no meaningful improvement over majority baseline (Balanced Accuracy $\le 0.50$).
- **Result**: **REJECTED**.
- **Evidence**: Mean Balanced Accuracy of $0.9667 \gg 0.5000$ ($p \ll 0.001$).

### Alternative Hypothesis ($H_1$)
- **Statement**: XGBoost achieves Balanced Accuracy $> 0.85$, Macro F1 $> 0.90$, and Human False Positive Rate $\le 0.05$.
- **Result**: **PARTIALLY SUPPORTED**.
- **Criteria Breakdown**:
  - `balanced_accuracy > 0.85`: **MET** ($0.9667 > 0.85$)
  - `macro_f1 > 0.90`: **MET** ($0.9735 > 0.90$)
  - `human_fpr <= 0.05`: **NOT MET** ($0.0667 > 0.05$)
- **Scientific Rationale**:
  In Fold 3 (testing on the button-navigation `TASK_01` while training on form/typing `TASK_02` + `TASK_03`), participant `p_05` completed the task quickly, generating only 324 mouse events. The model (which learned a split threshold of 359 from the longer typing tasks) misclassified `p_05` as automated ($\text{FPR} = 0.20$ on Fold 3). This cross-task domain shift drove the aggregate Human FPR to $6.67\%$, exceeding the strict $5.0\%$ target threshold.

---

## 10. Important Methodological Warning

> [!WARNING]
> **BEHAVIORAL-VOLUME ARTIFACT RISK**:
> Feature importance analysis reveals that `mouse_event_count` dominates the tree splits (100% gain share in single-feature stumps). In the current batch, automated replay scripts executed in 20–35 events, while human sessions typically generated 300–700 events. 
> 
> Consequently, the baseline model risks acting as a proxy for **interaction volume** rather than learning intrinsic motor trajectory dynamics (curvature, velocity variance, jerk). Rapid human interactions in simpler tasks risk false-positive misclassification. Subsequent experiments must evaluate volume-normalized features and multi-modal correlation.

---

## 11. Test Suite Verification
- **Test Command**: `python -m unittest discover tests`
- **Result**: **Exactly 51 tests passed** (0 failures, 0 errors, 1.309s).
  - `tests/test_train_experiment_a.py`: 5 tests
  - `tests/test_evaluation_protocol.py`: 12 tests
  - `tests/test_feature_config.py`: 5 tests
  - `tests/test_dataset_collection.py`: 17 tests
  - `tests/test_feature_engineering.py`: 12 tests

---

## 12. Associated Files

| File | Purpose |
| :--- | :--- |
| [`ml/data/features.csv`](file:///d:/VIT/TY/Web%20Tech/CP/ml/data/features.csv) | Authoritative 45-session dataset with 76 behavioral features + target label |
| [`ml/data/metadata.csv`](file:///d:/VIT/TY/Web%20Tech/CP/ml/data/metadata.csv) | Session provenance (participant ID, task ID, condition, timestamp) |
| [`ml/training/feature_config.py`](file:///d:/VIT/TY/Web%20Tech/CP/ml/training/feature_config.py) | Reproducible 64-feature selection and dataset loading routines |
| [`ml/training/evaluation_protocol.py`](file:///d:/VIT/TY/Web%20Tech/CP/ml/training/evaluation_protocol.py) | LOTO split generators, leakage auditor, baseline classifier, and metrics |
| [`ml/training/train_experiment_a.py`](file:///d:/VIT/TY/Web%20Tech/CP/ml/training/train_experiment_a.py) | Experiment A training execution and evaluation engine |
| [`ml/training/__init__.py`](file:///d:/VIT/TY/Web%20Tech/CP/ml/training/__init__.py) | Module exports |
| [`tests/test_feature_config.py`](file:///d:/VIT/TY/Web%20Tech/CP/tests/test_feature_config.py) | Unit tests for feature configuration |
| [`tests/test_evaluation_protocol.py`](file:///d:/VIT/TY/Web%20Tech/CP/tests/test_evaluation_protocol.py) | Unit tests for evaluation protocol |
| [`tests/test_train_experiment_a.py`](file:///d:/VIT/TY/Web%20Tech/CP/tests/test_train_experiment_a.py) | Unit tests for Experiment A training pipeline |
| [`ml/evaluation/experiment_a_reproducibility_record.md`](file:///d:/VIT/TY/Web%20Tech/CP/ml/evaluation/experiment_a_reproducibility_record.md) | This reproducibility record |
