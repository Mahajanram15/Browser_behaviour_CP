"""
Tests for ML Training Feature Selection Configuration (Experiment A).
"""

import unittest
import pandas as pd
from ml.features.extractor import FEATURE_COLUMNS
from ml.training.feature_config import (
    EXCLUDED_FEATURES_EXPERIMENT_A,
    SELECTED_FEATURES_EXPERIMENT_A,
    RETAINED_TASK_DEPENDENT_FEATURES,
    get_selected_features,
    get_excluded_features,
    load_experiment_dataset,
)


class TestFeatureConfigExperimentA(unittest.TestCase):
    def test_canonical_counts(self):
        """Verify feature counts and set arithmetic."""
        self.assertEqual(len(FEATURE_COLUMNS), 76)
        self.assertEqual(len(EXCLUDED_FEATURES_EXPERIMENT_A), 12)
        self.assertEqual(len(SELECTED_FEATURES_EXPERIMENT_A), 64)
        self.assertEqual(
            len(FEATURE_COLUMNS) - len(EXCLUDED_FEATURES_EXPERIMENT_A),
            len(SELECTED_FEATURES_EXPERIMENT_A),
        )

    def test_excluded_features_exist_in_canonical_schema(self):
        """Verify all excluded features are valid columns in FEATURE_COLUMNS."""
        for feat in EXCLUDED_FEATURES_EXPERIMENT_A:
            self.assertIn(feat, FEATURE_COLUMNS, f"Excluded feature {feat} not in canonical FEATURE_COLUMNS")

    def test_no_overlap(self):
        """Verify disjoint sets between selected and excluded."""
        overlap = set(EXCLUDED_FEATURES_EXPERIMENT_A).intersection(set(SELECTED_FEATURES_EXPERIMENT_A))
        self.assertEqual(len(overlap), 0, f"Unexpected overlap: {overlap}")

    def test_retained_task_dependent_features_are_present(self):
        """Verify all monitored task-dependent features are retained in selected set."""
        for feat in RETAINED_TASK_DEPENDENT_FEATURES:
            self.assertIn(feat, SELECTED_FEATURES_EXPERIMENT_A)
            self.assertNotIn(feat, EXCLUDED_FEATURES_EXPERIMENT_A)

    def test_load_experiment_dataset(self):
        """Verify dataset loading, label isolation, and absence of NaNs."""
        X, y, meta = load_experiment_dataset("ml/data/features.csv", "ml/data/metadata.csv", experiment="A")
        
        # Dimensions
        self.assertEqual(X.shape, (45, 64))
        self.assertEqual(len(y), 45)
        self.assertEqual(len(meta), 45)

        # Label isolation: authoritative target must not be in feature matrix
        self.assertNotIn("label", X.columns)
        self.assertNotIn("session_id", X.columns)
        self.assertEqual(set(X.columns), set(SELECTED_FEATURES_EXPERIMENT_A))

        # Data integrity: no missing/NaN values in derived feature matrix
        self.assertEqual(X.isna().sum().sum(), 0)

        # Label distribution (15 Human, 30 Automated)
        self.assertEqual(int((y == 0).sum()), 15)
        self.assertEqual(int((y == 1).sum()), 30)


if __name__ == "__main__":
    unittest.main()
