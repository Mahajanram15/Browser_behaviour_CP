"""
Unit Tests for Experiment A Training & Evaluation Engine.
"""

import unittest
from ml.training.train_experiment_a import run_experiment_a_evaluation
from ml.training.feature_config import SELECTED_FEATURES_EXPERIMENT_A


class TestTrainExperimentA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = run_experiment_a_evaluation(
            features_csv="ml/data/features.csv",
            metadata_csv="ml/data/metadata.csv",
            random_state=42,
        )

    def test_dataset_summary(self):
        """Verify dataset counts in evaluation report."""
        summary = self.results["dataset_summary"]
        self.assertEqual(summary["total_sessions"], 45)
        self.assertEqual(summary["human_sessions"], 15)
        self.assertEqual(summary["automated_sessions"], 30)
        self.assertEqual(summary["feature_count"], 64)
        self.assertEqual(summary["tasks"], ["TASK_01", "TASK_02", "TASK_03"])

    def test_loto_folds(self):
        """Verify 3 LOTO folds and sample partitions."""
        folds = self.results["fold_results"]
        self.assertEqual(len(folds), 3)

        for fold in folds:
            self.assertEqual(fold["train_samples"], 30)
            self.assertEqual(fold["test_samples"], 15)
            self.assertEqual(fold["train_human"], 10)
            self.assertEqual(fold["train_automated"], 20)
            self.assertEqual(fold["test_human"], 5)
            self.assertEqual(fold["test_automated"], 10)

            # Check baseline majority performance
            self.assertEqual(fold["baseline"]["balanced_accuracy"], 0.5)
            self.assertEqual(fold["baseline"]["recall"], 1.0)
            self.assertEqual(fold["baseline"]["confusion_matrix"]["tp"], 10)
            self.assertEqual(fold["baseline"]["confusion_matrix"]["fp"], 5)

            # Check XGBoost performance superiority
            self.assertGreaterEqual(fold["xgboost"]["balanced_accuracy"], 0.90)
            self.assertEqual(fold["xgboost"]["recall"], 1.0)

    def test_aggregate_comparison(self):
        """Verify aggregate metrics comparing XGBoost to Baseline."""
        base_agg = self.results["aggregate_baseline"]
        xgb_agg = self.results["aggregate_xgboost"]

        self.assertEqual(base_agg["mean_balanced_accuracy"], 0.5)
        self.assertGreater(xgb_agg["mean_balanced_accuracy"], 0.90)
        self.assertGreater(xgb_agg["mean_macro_f1"], 0.90)
        self.assertGreater(xgb_agg["mean_roc_auc"], 0.90)

    def test_hypothesis_evaluation(self):
        """Verify H0 is rejected and H1 is evaluated with proper criteria breakdown."""
        hypo = self.results["hypothesis_evaluation"]
        self.assertTrue(hypo["H0_rejected"])
        self.assertIn("H1_criteria_breakdown", hypo)
        breakdown = hypo["H1_criteria_breakdown"]
        self.assertTrue(breakdown["balanced_accuracy_gt_0_85"]["met"])
        self.assertTrue(breakdown["macro_f1_gt_0_90"]["met"])
        # Human FPR is 0.0667, exceeding 0.05
        self.assertFalse(breakdown["human_fpr_lte_0_05"]["met"])
        self.assertFalse(hypo["H1_overall_supported"])

    def test_top_feature_importances(self):
        """Verify feature importances are extracted."""
        importances = self.results["top_feature_importances"]
        self.assertGreater(len(importances), 0)
        self.assertIn("mouse_event_count", importances)


if __name__ == "__main__":
    unittest.main()
