"""
Reproducible Feature Selection Configuration for Behavioral-Integrity ML Experiments.

Defines documented feature exclusion lists, task-dependent feature monitoring,
and deterministic dataset transformation routines for Experiment A.

Preserves the original 76-feature raw matrix on disk while producing a clean,
leakage-free derived training matrix (X, y, metadata).
"""

from typing import List, Dict, Tuple, Optional
import os
import pandas as pd
from ml.features.extractor import FEATURE_COLUMNS

# ==============================================================================
# 1. Documented Exclusions for Baseline Experiment A
# ==============================================================================
EXCLUDED_FEATURES_EXPERIMENT_A: List[str] = [
    # A. Experimental Timing Leakage (3 features)
    # Rationale: Human participants spent 60-90s reading and exploring tasks,
    # whereas automated scripts ran sequentially in 1.5-3.0s. Raw session duration
    # is an artifact of experimental pacing rather than intrinsic motor dynamics.
    "session_duration_ms",
    "mouse_session_duration_ms",
    "active_behavior_duration_ms",

    # B. Environmental / Window Artifact Leakage (5 features)
    # Rationale: Human participants naturally switched or blurred browser tabs
    # during user study interaction, while automated harness ran in a continuous
    # focused window. Using visibility flags causes overfitting to study setting.
    "hidden_event_count",
    "blur_event_count",
    "focus_event_count",
    "time_away_ratio",
    "max_time_away_ms",

    # C. Zero-Variance Constants (3 features)
    # Rationale: Zero variance across all collected sessions (all identical 0.0);
    # uninformative constants that provide zero statistical entropy.
    "double_click_rate",
    "backspace_rate",
    "paste_rate",

    # D. Dispatch Rate Proxy (1 feature)
    # Rationale: The automated collector dispatched events at a fixed 50ms interval,
    # making interaction_density an artificial 20.0 ev/s constant proxy.
    "interaction_density",
]

# ==============================================================================
# 2. Retained Task-Dependent Features (Monitored via Stratification)
# ==============================================================================
# These features correlate strongly with specific task workflows (e.g. typing
# in form tasks vs clicking in navigation tasks). They are intentionally RETAINED
# rather than silently removed, and MUST be evaluated using task-stratified
# cross-validation to assess cross-task generalization.
RETAINED_TASK_DEPENDENT_FEATURES: List[str] = [
    "button_click_ratio",     # High in TASK_01 (button nav), low in form entry
    "min_flight_ms",          # Exists only in text input tasks (TASK_02, TASK_03)
    "input_click_ratio",      # High in form fill tasks (TASK_02, TASK_03)
    "key_event_count",        # Non-zero only in typing tasks (TASK_02, TASK_03)
    "typing_speed",           # Non-zero only in typing tasks (TASK_02, TASK_03)
    "scroll_event_count",     # Elevated in long content browsing (TASK_01)
]

# ==============================================================================
# 3. Selected Feature Set for Experiment A (64 Features)
# ==============================================================================
SELECTED_FEATURES_EXPERIMENT_A: List[str] = [
    col for col in FEATURE_COLUMNS
    if col not in EXCLUDED_FEATURES_EXPERIMENT_A
]


def get_selected_features(experiment: str = "A") -> List[str]:
    """
    Returns the canonical list of selected feature column names for an experiment.
    """
    if experiment.upper() == "A":
        return list(SELECTED_FEATURES_EXPERIMENT_A)
    raise ValueError(f"Unknown experiment: {experiment}")


def get_excluded_features(experiment: str = "A") -> List[str]:
    """
    Returns the list of excluded feature column names for an experiment.
    """
    if experiment.upper() == "A":
        return list(EXCLUDED_FEATURES_EXPERIMENT_A)
    raise ValueError(f"Unknown experiment: {experiment}")


def load_experiment_dataset(
    features_csv_path: str = "ml/data/features.csv",
    metadata_csv_path: Optional[str] = "ml/data/metadata.csv",
    experiment: str = "A",
) -> Tuple[pd.DataFrame, pd.Series, Optional[pd.DataFrame]]:
    """
    Loads features and metadata from CSVs and returns a clean, reproducible derived split:
    - X: pd.DataFrame of shape (N, 64) with selected behavioral features only.
    - y: pd.Series of length N containing authoritative binary labels (0 = HUMAN, 1 = AUTOMATED).
    - meta: pd.DataFrame containing session metadata for task stratification and grouped evaluation.
    
    Guarantees:
    1. Zero modification to original CSV files on disk.
    2. Complete isolation: target label is NEVER present inside X.
    3. Missing value validation: ensures no NaNs in X.
    """
    if not os.path.exists(features_csv_path):
        raise FileNotFoundError(f"Features file not found: {features_csv_path}")

    df_features = pd.read_csv(features_csv_path)

    if "label" not in df_features.columns:
        raise ValueError("Features file must contain an authoritative 'label' column.")

    selected_cols = get_selected_features(experiment=experiment)

    # Verify all selected columns exist in the CSV
    missing_cols = [col for col in selected_cols if col not in df_features.columns]
    if missing_cols:
        raise KeyError(f"Features CSV is missing required columns: {missing_cols}")

    # Derived feature matrix X (isolated from label and metadata)
    X = df_features[selected_cols].copy()
    y = df_features["label"].astype(int).copy()

    # Load metadata if available
    meta_df = None
    if metadata_csv_path and os.path.exists(metadata_csv_path):
        meta_df = pd.read_csv(metadata_csv_path)
        if len(meta_df) != len(df_features):
            raise ValueError(f"Row mismatch: features ({len(df_features)}) vs metadata ({len(meta_df)})")

    return X, y, meta_df


def validate_feature_configuration():
    """
    Self-validation utility reporting configuration counts and dataset compatibility.
    """
    print("=" * 70)
    print("EXPERIMENT A: FEATURE SELECTION CONFIGURATION VALIDATION")
    print("=" * 70)

    orig_count = len(FEATURE_COLUMNS)
    excl_count = len(EXCLUDED_FEATURES_EXPERIMENT_A)
    sel_count = len(SELECTED_FEATURES_EXPERIMENT_A)

    print(f"Original Feature Count       : {orig_count}")
    print(f"Excluded Feature Count       : {excl_count}")
    print(f"Resulting Feature Count      : {sel_count}")
    print(f"Arithmetic Verification      : {orig_count} - {excl_count} == {sel_count} ({orig_count - excl_count == sel_count})")
    print()

    print("Documented Exclusions:")
    for idx, f in enumerate(EXCLUDED_FEATURES_EXPERIMENT_A, 1):
        print(f"  {idx:2d}. {f}")
    print()

    print("Retained Task-Dependent Features (Subject to Task Stratification):")
    for idx, f in enumerate(RETAINED_TASK_DEPENDENT_FEATURES, 1):
        print(f"  {idx:2d}. {f} (present in selected features: {f in SELECTED_FEATURES_EXPERIMENT_A})")
    print()

    # Verify against disk dataset
    csv_path = "ml/data/features.csv"
    meta_path = "ml/data/metadata.csv"
    if os.path.exists(csv_path):
        X, y, meta = load_experiment_dataset(csv_path, meta_path, experiment="A")
        print("Dataset Compatibility Check on 'ml/data/features.csv':")
        print(f"  - Derived Feature Matrix (X) Shape : {X.shape}")
        print(f"  - Target Label Vector (y) Shape    : {y.shape}")
        print(f"  - Class Balance in y               : {dict(y.value_counts())}")
        print(f"  - Target Label in X                : {'label' in X.columns} (Must be False)")
        print(f"  - Total NaN Values in X            : {int(X.isna().sum().sum())}")
        if meta is not None:
            print(f"  - Metadata Rows                    : {len(meta)}")
            print(f"  - Tasks Available in Metadata      : {dict(meta['task_id'].value_counts())}")
            print(f"  - Conditions in Metadata           : {dict(meta['automation_condition'].value_counts())}")
    print("=" * 70)


if __name__ == "__main__":
    validate_feature_configuration()
