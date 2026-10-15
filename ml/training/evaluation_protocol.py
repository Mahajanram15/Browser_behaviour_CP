"""
Evaluation Protocol for Behavioral-Integrity ML Experiments (Experiment A).

Defines group-aware validation, task-stratified evaluation, Leave-One-Task-Out (LOTO)
split generators, leakage prevention safeguards, and baseline model benchmarks.

CRITICAL CONSTRAINTS:
1. No synthetic oversampling (e.g., SMOTE) or duplication of sessions.
2. Target label and metadata fields must NEVER enter feature matrix X.
3. Preprocessing/scaling must NEVER be fit on validation/test folds.
4. Models (XGBoost or Baseline) are NOT trained in this module; this defines the
   reproducible evaluation framework and split audits.
"""

from typing import List, Dict, Tuple, Optional, Any, Set
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
import warnings
from sklearn.metrics import (
    balanced_accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)

# ==============================================================================
# 1. Constants & Leakage Safeguards
# ==============================================================================
FORBIDDEN_METADATA_COLUMNS: Set[str] = {
    "label",
    "target",
    "session_id",
    "collection_mode",
    "automation_condition",
    "task_id",
    "participant_id",
    "collection_timestamp",
    "event_count",
}

PRIMARY_METRICS: List[str] = [
    "balanced_accuracy",
    "precision",
    "recall",
    "f1",
    "roc_auc",
    "confusion_matrix",
]


class LeakageError(ValueError):
    """Raised when leakage across folds, targets, or metadata is detected."""
    pass


class LeakageAuditor:
    """
    Validates feature matrices and split partitions to guarantee zero leakage.
    """

    @staticmethod
    def audit_feature_matrix(X: pd.DataFrame) -> None:
        """
        Ensures no target labels or metadata columns are present inside X.
        """
        if not isinstance(X, pd.DataFrame):
            raise TypeError(f"X must be a pandas DataFrame, got {type(X)}")

        present_forbidden = set(X.columns).intersection(FORBIDDEN_METADATA_COLUMNS)
        if present_forbidden:
            raise LeakageError(
                f"Leakage detected! Feature matrix contains forbidden metadata/target columns: {sorted(present_forbidden)}"
            )

        # Check for non-numeric columns
        non_numeric = [col for col in X.columns if not np.issubdtype(X[col].dtype, np.number)]
        if non_numeric:
            raise LeakageError(
                f"Feature matrix contains non-numeric columns that may leak categorical metadata: {non_numeric}"
            )

    @staticmethod
    def audit_split_isolation(
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
        meta_train: Optional[pd.DataFrame] = None,
        meta_test: Optional[pd.DataFrame] = None,
        check_groups: bool = False,
    ) -> Dict[str, Any]:
        """
        Audits train and test splits for row overlap, feature isolation, and group separation.
        """
        # 1. Feature matrix isolation
        LeakageAuditor.audit_feature_matrix(X_train)
        LeakageAuditor.audit_feature_matrix(X_test)

        # 2. Row index disjointness
        train_idx = set(X_train.index)
        test_idx = set(X_test.index)
        index_overlap = train_idx.intersection(test_idx)
        if index_overlap:
            raise LeakageError(f"Row leakage! Overlapping sample indices in train and test: {index_overlap}")

        group_overlap: Set[str] = set()
        if meta_train is not None and meta_test is not None:
            if "participant_id" in meta_train.columns and "participant_id" in meta_test.columns:
                train_groups = set(meta_train["participant_id"].dropna().unique())
                test_groups = set(meta_test["participant_id"].dropna().unique())
                group_overlap = train_groups.intersection(test_groups)

                if check_groups and group_overlap:
                    raise LeakageError(
                        f"Group leakage detected! Participant(s) present in both train and test: {sorted(group_overlap)}"
                    )

        return {
            "disjoint_rows": True,
            "group_overlap_count": len(group_overlap),
            "overlapping_groups": sorted(group_overlap),
        }

    @staticmethod
    def apply_isolated_preprocessing(
        transformer: Any,
        X_train: pd.DataFrame,
        X_test: pd.DataFrame,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Enforces proper transformer fitting: fits exclusively on X_train,
        then transforms X_train and X_test independently.
        """
        # Fit exclusively on train
        X_train_trans = transformer.fit_transform(X_train)
        # Transform test without re-fitting
        X_test_trans = transformer.transform(X_test)
        return X_train_trans, X_test_trans


# ==============================================================================
# 2. Split Definitions & Data Structures
# ==============================================================================
@dataclass
class FoldSplit:
    """
    Metadata and index specification for an evaluation fold.
    """
    fold_id: str
    description: str
    train_indices: np.ndarray
    test_indices: np.ndarray
    train_tasks: List[str]
    test_tasks: List[str]
    train_participants: List[str]
    test_participants: List[str]
    overlapping_participants: List[str]
    n_train_total: int
    n_train_human: int
    n_train_automated: int
    n_test_total: int
    n_test_human: int
    n_test_automated: int
    is_group_disjoint: bool
    is_train_multiclass: bool
    is_test_multiclass: bool
    is_valid: bool
    validity_status: str
    warnings: List[str] = field(default_factory=list)


# ==============================================================================
# 3. Validation Strategy Generators
# ==============================================================================
class EvaluationProtocol:
    """
    Generates reproducible evaluation folds and executes structured metric evaluations.
    """

    @staticmethod
    def generate_loto_folds(
        meta: pd.DataFrame,
        enforce_strict_groups: bool = False,
    ) -> List[FoldSplit]:
        """
        Generates the 3 canonical Leave-One-Task-Out (LOTO) folds:
        - Fold 1: Train on TASK_01 + TASK_02 -> Test on TASK_03
        - Fold 2: Train on TASK_01 + TASK_03 -> Test on TASK_02
        - Fold 3: Train on TASK_02 + TASK_03 -> Test on TASK_01

        Reports sample counts (HUMAN vs AUTOMATED) and audits group / class constraints.
        """
        loto_configs = [
            ("LOTO_TEST_TASK_03", ["TASK_01", "TASK_02"], ["TASK_03"]),
            ("LOTO_TEST_TASK_02", ["TASK_01", "TASK_03"], ["TASK_02"]),
            ("LOTO_TEST_TASK_01", ["TASK_02", "TASK_03"], ["TASK_01"]),
        ]

        folds: List[FoldSplit] = []

        for fold_id, train_tasks, test_tasks in loto_configs:
            train_mask = meta["task_id"].isin(train_tasks)
            test_mask = meta["task_id"].isin(test_tasks)

            train_idx = meta[train_mask].index.to_numpy()
            test_idx = meta[test_mask].index.to_numpy()

            test_parts = set(meta.loc[test_idx, "participant_id"].dropna().unique())
            train_parts = set(meta.loc[train_idx, "participant_id"].dropna().unique())
            overlap = sorted(train_parts.intersection(test_parts))

            # If enforcing strict groups, purge any overlapping participant from train
            if enforce_strict_groups and overlap:
                train_mask = train_mask & (~meta["participant_id"].isin(overlap))
                train_idx = meta[train_mask].index.to_numpy()
                train_parts = set(meta.loc[train_idx, "participant_id"].dropna().unique())
                overlap = sorted(train_parts.intersection(test_parts))

            # Count classes (0 = HUMAN, 1 = AUTOMATED)
            train_labels = meta.loc[train_idx, "label"].to_numpy()
            test_labels = meta.loc[test_idx, "label"].to_numpy()

            n_train_h = int((train_labels == 0).sum())
            n_train_a = int((train_labels == 1).sum())
            n_test_h = int((test_labels == 0).sum())
            n_test_a = int((test_labels == 1).sum())

            is_group_disjoint = len(overlap) == 0
            is_train_multiclass = (n_train_h > 0) and (n_train_a > 0)
            is_test_multiclass = (n_test_h > 0) and (n_test_a > 0)

            # Validity determination
            warnings = []
            validity_status = "VALID"
            is_valid = True

            if not is_train_multiclass:
                validity_status = "INVALID_SINGLE_CLASS_TRAIN"
                is_valid = False
                warnings.append(
                    f"Train split contains only 1 class (Human: {n_train_h}, Automated: {n_train_a}). "
                    "Cannot train binary classifier."
                )

            if not is_group_disjoint:
                warnings.append(
                    f"Group leakage detected: participant(s) {overlap} appear in both train and test. "
                    "Single human participant (p_01) exists across tasks."
                )
                if enforce_strict_groups:
                    validity_status = "INVALID_GROUP_LEAKAGE"
                    is_valid = False
                else:
                    validity_status = "VALID_WITH_GROUP_LEAKAGE_WARNING"

            if not is_test_multiclass:
                warnings.append(
                    f"Test split contains only 1 class (Human: {n_test_h}, Automated: {n_test_a}). "
                    "ROC-AUC is mathematically undefined for single-class test."
                )

            description = (
                f"Train: {train_tasks} ({n_train_h}H, {n_train_a}A) -> "
                f"Test: {test_tasks} ({n_test_h}H, {n_test_a}A)"
            )

            folds.append(
                FoldSplit(
                    fold_id=fold_id,
                    description=description,
                    train_indices=train_idx,
                    test_indices=test_idx,
                    train_tasks=train_tasks,
                    test_tasks=test_tasks,
                    train_participants=sorted(train_parts),
                    test_participants=sorted(test_parts),
                    overlapping_participants=overlap,
                    n_train_total=len(train_idx),
                    n_train_human=n_train_h,
                    n_train_automated=n_train_a,
                    n_test_total=len(test_idx),
                    n_test_human=n_test_h,
                    n_test_automated=n_test_a,
                    is_group_disjoint=is_group_disjoint,
                    is_train_multiclass=is_train_multiclass,
                    is_test_multiclass=is_test_multiclass,
                    is_valid=is_valid,
                    validity_status=validity_status,
                    warnings=warnings,
                )
            )

        return folds

    @staticmethod
    def generate_group_folds(
        meta: pd.DataFrame,
    ) -> List[FoldSplit]:
        """
        Audits strict participant-level Leave-One-Group-Out validation.
        Demonstrates why strict group-disjoint validation is currently pathological
        when only 1 human participant (p_01) exists in the dataset.
        """
        participants = sorted(meta["participant_id"].dropna().unique())
        folds: List[FoldSplit] = []

        for p_id in participants:
            test_mask = meta["participant_id"] == p_id
            train_mask = ~test_mask

            train_idx = meta[train_mask].index.to_numpy()
            test_idx = meta[test_mask].index.to_numpy()

            train_labels = meta.loc[train_idx, "label"].to_numpy()
            test_labels = meta.loc[test_idx, "label"].to_numpy()

            n_train_h = int((train_labels == 0).sum())
            n_train_a = int((train_labels == 1).sum())
            n_test_h = int((test_labels == 0).sum())
            n_test_a = int((test_labels == 1).sum())

            is_train_multiclass = (n_train_h > 0) and (n_train_a > 0)
            is_test_multiclass = (n_test_h > 0) and (n_test_a > 0)

            warnings = []
            if not is_train_multiclass:
                validity_status = "INVALID_SINGLE_CLASS_TRAIN"
                is_valid = False
                warnings.append(
                    f"Testing on participant '{p_id}' removes all Human samples from train (Human: {n_train_h}, Automated: {n_train_a}). "
                    "Impossible to train binary classifier."
                )
            elif not is_test_multiclass:
                validity_status = "TEST_SINGLE_CLASS"
                is_valid = True
                warnings.append(
                    f"Test fold contains only 1 class ({'Human' if n_test_h > 0 else 'Automated'}). ROC-AUC undefined."
                )
            else:
                validity_status = "VALID"
                is_valid = True

            description = f"Leave-Group-Out on '{p_id}' (Train: {n_train_h}H, {n_train_a}A | Test: {n_test_h}H, {n_test_a}A)"

            folds.append(
                FoldSplit(
                    fold_id=f"LOGO_{p_id}",
                    description=description,
                    train_indices=train_idx,
                    test_indices=test_idx,
                    train_tasks=sorted(meta.loc[train_idx, "task_id"].unique()),
                    test_tasks=sorted(meta.loc[test_idx, "task_id"].unique()),
                    train_participants=sorted(meta.loc[train_idx, "participant_id"].unique()),
                    test_participants=[p_id],
                    overlapping_participants=[],
                    n_train_total=len(train_idx),
                    n_train_human=n_train_h,
                    n_train_automated=n_train_a,
                    n_test_total=len(test_idx),
                    n_test_human=n_test_h,
                    n_test_automated=n_test_a,
                    is_group_disjoint=True,
                    is_train_multiclass=is_train_multiclass,
                    is_test_multiclass=is_test_multiclass,
                    is_valid=is_valid,
                    validity_status=validity_status,
                    warnings=warnings,
                )
            )

        return folds


# ==============================================================================
# 4. Metric Calculations & Task-Stratified Slicing
# ==============================================================================
def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: Optional[np.ndarray] = None,
) -> Dict[str, Any]:
    """
    Computes primary evaluation metrics:
    - Balanced Accuracy
    - Precision
    - Recall
    - F1
    - ROC-AUC (only when both classes are present in y_true and probabilities are provided)
    - Confusion Matrix (tn, fp, fn, tp)
    """
    y_true_arr = np.asarray(y_true).astype(int)
    y_pred_arr = np.asarray(y_pred).astype(int)

    # 1. Balanced Accuracy
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        bal_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))

    # 2. Precision, Recall, F1 (Positive class = 1: AUTOMATED, zero_division=0)
    prec = float(precision_score(y_true_arr, y_pred_arr, zero_division=0))
    rec = float(recall_score(y_true_arr, y_pred_arr, zero_division=0))
    f1 = float(f1_score(y_true_arr, y_pred_arr, zero_division=0))

    # 3. Confusion Matrix (guaranteed 2x2 with labels=[0, 1])
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1])
    tn, fp, fn, tp = [int(v) for v in cm.ravel()]

    # 4. ROC-AUC calculation
    unique_classes = np.unique(y_true_arr)
    roc_auc: Optional[float] = None
    roc_auc_status = "NOT_COMPUTED"

    if y_prob is None:
        roc_auc_status = "PROBABILITIES_NOT_PROVIDED"
    elif len(unique_classes) < 2:
        roc_auc_status = "UNDEFINED_SINGLE_CLASS"
    else:
        try:
            # Handle 1D probabilities or 2D probability matrices
            y_prob_arr = np.asarray(y_prob)
            if y_prob_arr.ndim == 2:
                prob_pos = y_prob_arr[:, 1]
            else:
                prob_pos = y_prob_arr
            roc_auc = float(roc_auc_score(y_true_arr, prob_pos))
            roc_auc_status = "COMPUTED"
        except Exception as e:
            roc_auc_status = f"ERROR: {str(e)}"

    return {
        "balanced_accuracy": round(bal_acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "roc_auc": round(roc_auc, 4) if roc_auc is not None else None,
        "roc_auc_status": roc_auc_status,
        "confusion_matrix": {"tn": tn, "fp": fp, "fn": fn, "tp": tp},
    }


def compute_per_task_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    meta: pd.DataFrame,
    y_prob: Optional[np.ndarray] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Slices predictions by task_id ('TASK_01', 'TASK_02', 'TASK_03') and reports
    metrics separately for each task.
    """
    if len(y_true) != len(meta):
        raise ValueError(f"Length mismatch: y_true ({len(y_true)}) vs meta ({len(meta)})")

    task_results: Dict[str, Dict[str, Any]] = {}
    tasks = sorted(meta["task_id"].dropna().unique())

    for task in tasks:
        mask = (meta["task_id"] == task).to_numpy()
        sub_true = np.asarray(y_true)[mask]
        sub_pred = np.asarray(y_pred)[mask]
        sub_prob = np.asarray(y_prob)[mask] if y_prob is not None else None

        task_metrics = calculate_metrics(sub_true, sub_pred, sub_prob)
        task_metrics["n_samples"] = int(mask.sum())
        task_metrics["n_human"] = int((sub_true == 0).sum())
        task_metrics["n_automated"] = int((sub_true == 1).sum())

        task_results[task] = task_metrics

    return task_results


# ==============================================================================
# 5. Baseline Classifier & Research Comparison Specification
# ==============================================================================
class BaselineClassifier:
    """
    Simple reference baseline classifier for empirical comparison against candidate models.
    Supports:
    - 'majority': Predicts the majority class seen during training.
    - 'prior': Predicts classes according to empirical class priors.

    NOTE: Does not train or fit on data unless explicitly invoked during an experiment.
    """

    def __init__(self, strategy: str = "majority"):
        if strategy not in ("majority", "prior"):
            raise ValueError(f"Unknown baseline strategy: {strategy}")
        self.strategy = strategy
        self.majority_class_: Optional[int] = None
        self.priors_: Optional[Dict[int, float]] = None
        self.is_fitted_: bool = False

    def fit(self, X: pd.DataFrame, y: pd.Series):
        """Fits baseline on training targets only (X is ignored)."""
        LeakageAuditor.audit_feature_matrix(X)
        y_arr = np.asarray(y).astype(int)

        vals, counts = np.unique(y_arr, return_counts=True)
        self.majority_class_ = int(vals[np.argmax(counts)])
        total = float(len(y_arr))
        self.priors_ = {int(v): float(c) / total for v, c in zip(vals, counts)}
        self.is_fitted_ = True
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Generates baseline predictions."""
        if not self.is_fitted_:
            raise RuntimeError("BaselineClassifier must be fitted before predict.")
        n = len(X)
        if self.strategy == "majority":
            return np.full(n, self.majority_class_, dtype=int)
        else:
            classes = list(self.priors_.keys())
            probs = [self.priors_[c] for c in classes]
            return np.random.choice(classes, size=n, p=probs)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Returns empirical prior probabilities."""
        if not self.is_fitted_:
            raise RuntimeError("BaselineClassifier must be fitted before predict_proba.")
        n = len(X)
        p1 = self.priors_.get(1, 0.0)
        p0 = self.priors_.get(0, 0.0)
        return np.tile([p0, p1], (n, 1))


@dataclass
class ResearchComparisonSpecification:
    """
    Formal research comparison contract between Candidate XGBoost and Baseline.
    """
    candidate_model: str = "XGBoost (Behavioral-Integrity Experiment A)"
    baseline_model: str = "MajorityClassBaselineClassifier"
    decision_threshold: float = 0.50
    hypotheses: Dict[str, str] = field(default_factory=lambda: {
        "H0": "XGBoost behavioral features show no improvement in Balanced Accuracy over the majority baseline.",
        "H1": "XGBoost behavioral features achieve statistically significant higher Balanced Accuracy and macro F1 over baseline.",
    })
    target_benchmarks: Dict[str, float] = field(default_factory=lambda: {
        "min_balanced_accuracy": 0.85,
        "max_false_positive_rate_human": 0.05,
        "min_f1_score": 0.90,
    })
    status: str = "SPECIFIED_NOT_TRAINED"


# ==============================================================================
# 6. Self-Validation Diagnostic Routine
# ==============================================================================
def audit_evaluation_protocol(
    features_csv: str = "ml/data/features.csv",
    metadata_csv: str = "ml/data/metadata.csv",
):
    """
    Executes a comprehensive audit of evaluation folds and constraints on the 33-session dataset.
    """
    print("=" * 78)
    print("EXPERIMENT A: EVALUATION PROTOCOL AUDIT & FOLD DIAGNOSTICS")
    print("=" * 78)

    meta = pd.read_csv(metadata_csv)
    print(f"Total Dataset Sessions: {len(meta)}")
    print(f"Participants Present  : {sorted(meta['participant_id'].unique())}")
    print(f"Tasks Present         : {sorted(meta['task_id'].unique())}")
    print()

    # 1. LOTO Folds (Standard)
    print("--- 1. LEAVE-ONE-TASK-OUT (LOTO) FOLDS ---")
    loto_folds = EvaluationProtocol.generate_loto_folds(meta, enforce_strict_groups=False)
    for fold in loto_folds:
        print(f"[{fold.fold_id}]")
        print(f"  Description       : {fold.description}")
        print(f"  Train Samples     : {fold.n_train_total} (Human: {fold.n_train_human}, Automated: {fold.n_train_automated})")
        print(f"  Test Samples      : {fold.n_test_total} (Human: {fold.n_test_human}, Automated: {fold.n_test_automated})")
        print(f"  Group Disjoint    : {fold.is_group_disjoint}")
        print(f"  Group Overlap     : {fold.overlapping_participants}")
        print(f"  Validity Status   : {fold.validity_status}")
        if fold.warnings:
            for w in fold.warnings:
                print(f"  WARNING           : {w}")
        print()

    # 2. Strict Group LOTO Folds
    print("--- 2. LOTO WITH STRICT GROUP ISOLATION ENFORCED ---")
    strict_loto_folds = EvaluationProtocol.generate_loto_folds(meta, enforce_strict_groups=True)
    for fold in strict_loto_folds:
        print(f"[{fold.fold_id}]")
        print(f"  Validity Status   : {fold.validity_status} (is_valid={fold.is_valid})")
        print(f"  Train Samples     : {fold.n_train_total} (Human: {fold.n_train_human}, Automated: {fold.n_train_automated})")
        if fold.warnings:
            for w in fold.warnings:
                print(f"  DIAGNOSIS         : {w}")
        print()

    # 3. Group-Aware LOGO (Leave-One-Group-Out)
    print("--- 3. LEAVE-ONE-GROUP-OUT (LOGO) AUDIT ---")
    group_folds = EvaluationProtocol.generate_group_folds(meta)
    p01_fold = [f for f in group_folds if "p_01" in f.test_participants][0]
    print(f"[{p01_fold.fold_id}]")
    print(f"  Testing on Human Participant 'p_01':")
    print(f"  Train Samples     : {p01_fold.n_train_total} (Human: {p01_fold.n_train_human}, Automated: {p01_fold.n_train_automated})")
    print(f"  Test Samples      : {p01_fold.n_test_total} (Human: {p01_fold.n_test_human}, Automated: {p01_fold.n_test_automated})")
    print(f"  Validity Status   : {p01_fold.validity_status} (is_valid={p01_fold.is_valid})")
    for w in p01_fold.warnings:
        print(f"  DIAGNOSIS         : {w}")
    print("=" * 78)


if __name__ == "__main__":
    audit_evaluation_protocol()
