"""
ML Training Package.
Provides reproducible dataset preparation, feature selection, evaluation protocols,
and model training routines.
"""

from ml.training.feature_config import (
    EXCLUDED_FEATURES_EXPERIMENT_A,
    SELECTED_FEATURES_EXPERIMENT_A,
    RETAINED_TASK_DEPENDENT_FEATURES,
    get_selected_features,
    get_excluded_features,
    load_experiment_dataset,
)

from ml.training.evaluation_protocol import (
    FORBIDDEN_METADATA_COLUMNS,
    PRIMARY_METRICS,
    LeakageError,
    LeakageAuditor,
    FoldSplit,
    EvaluationProtocol,
    calculate_metrics,
    compute_per_task_metrics,
    BaselineClassifier,
    ResearchComparisonSpecification,
)

from ml.training.train_experiment_a import run_experiment_a_evaluation

__all__ = [
    "EXCLUDED_FEATURES_EXPERIMENT_A",
    "SELECTED_FEATURES_EXPERIMENT_A",
    "RETAINED_TASK_DEPENDENT_FEATURES",
    "get_selected_features",
    "get_excluded_features",
    "load_experiment_dataset",
    "FORBIDDEN_METADATA_COLUMNS",
    "PRIMARY_METRICS",
    "LeakageError",
    "LeakageAuditor",
    "FoldSplit",
    "EvaluationProtocol",
    "calculate_metrics",
    "compute_per_task_metrics",
    "BaselineClassifier",
    "ResearchComparisonSpecification",
    "run_experiment_a_evaluation",
]

