"""
Automated Unit Tests for ML Training Evaluation Protocol (Experiment A).
"""

import unittest
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from ml.training.feature_config import load_experiment_dataset
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


class TestEvaluationProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.X, cls.y, cls.meta = load_experiment_dataset(
            features_csv_path="ml/data/features.csv",
            metadata_csv_path="ml/data/metadata.csv",
            experiment="A",
        )

    def test_leakage_auditor_clean_matrix(self):
        """Clean feature matrix must pass leakage audit."""
        LeakageAuditor.audit_feature_matrix(self.X)

    def test_leakage_auditor_detects_forbidden_columns(self):
        """LeakageAuditor must raise LeakageError if any forbidden column is present."""
        for col in ["label", "session_id", "task_id", "participant_id", "target"]:
            dirty_X = self.X.copy()
            dirty_X[col] = 0
            with self.assertRaises(LeakageError, msg=f"Failed to detect forbidden column {col}"):
                LeakageAuditor.audit_feature_matrix(dirty_X)

    def test_leakage_auditor_split_row_overlap(self):
        """LeakageAuditor must catch overlapping row indices between train and test."""
        X_train = self.X.iloc[:20]
        X_test = self.X.iloc[15:25]  # Indices 15-19 overlap
        with self.assertRaises(LeakageError):
            LeakageAuditor.audit_split_isolation(X_train, X_test)

    def test_isolated_preprocessing(self):
        """Transformer must be fit only on train and transform applied to test."""
        scaler = StandardScaler()
        X_train = self.X.iloc[:22]
        X_test = self.X.iloc[22:]

        X_train_s, X_test_s = LeakageAuditor.apply_isolated_preprocessing(scaler, X_train, X_test)
        self.assertEqual(X_train_s.shape, X_train.shape)
        self.assertEqual(X_test_s.shape, X_test.shape)
        # Verify scaler mean was computed from train, not test
        np.testing.assert_allclose(scaler.mean_, X_train.mean().values)

    def test_metric_calculations_both_classes(self):
        """Metrics with both classes must compute all primary metrics including ROC-AUC."""
        y_true = np.array([0, 0, 1, 1, 1, 1])
        y_pred = np.array([0, 1, 1, 1, 1, 1])
        y_prob = np.array([0.1, 0.7, 0.8, 0.9, 0.85, 0.95])

        metrics = calculate_metrics(y_true, y_pred, y_prob)

        for m in PRIMARY_METRICS:
            self.assertIn(m, metrics)

        self.assertEqual(metrics["roc_auc_status"], "COMPUTED")
        self.assertIsInstance(metrics["roc_auc"], float)
        self.assertGreater(metrics["roc_auc"], 0.5)
        self.assertEqual(metrics["confusion_matrix"], {"tn": 1, "fp": 1, "fn": 0, "tp": 4})

    def test_metric_calculations_single_class_test(self):
        """When y_true contains only one class, ROC-AUC must be None with status flag."""
        y_true = np.array([1, 1, 1, 1])
        y_pred = np.array([1, 1, 1, 1])
        y_prob = np.array([0.8, 0.9, 0.85, 0.95])

        metrics = calculate_metrics(y_true, y_pred, y_prob)
        self.assertIsNone(metrics["roc_auc"])
        self.assertEqual(metrics["roc_auc_status"], "UNDEFINED_SINGLE_CLASS")
        self.assertEqual(metrics["confusion_matrix"], {"tn": 0, "fp": 0, "fn": 0, "tp": 4})

    def test_per_task_metric_slicing(self):
        """Metrics should be sliced and reported per task."""
        y_pred = self.y.values  # perfect mock predictions
        task_metrics = compute_per_task_metrics(self.y.values, y_pred, self.meta)

        self.assertIn("TASK_01", task_metrics)
        self.assertIn("TASK_02", task_metrics)
        self.assertIn("TASK_03", task_metrics)

        for task, res in task_metrics.items():
            self.assertEqual(res["n_samples"], 15)
            self.assertEqual(res["n_human"], 5)
            self.assertEqual(res["n_automated"], 10)
            self.assertEqual(res["balanced_accuracy"], 1.0)

    def test_loto_folds_generation(self):
        """Verify 3 LOTO folds and exact sample counts on the 45-session dataset."""
        folds = EvaluationProtocol.generate_loto_folds(self.meta, enforce_strict_groups=False)
        self.assertEqual(len(folds), 3)

        expected_configs = {
            "LOTO_TEST_TASK_03": (["TASK_01", "TASK_02"], ["TASK_03"]),
            "LOTO_TEST_TASK_02": (["TASK_01", "TASK_03"], ["TASK_02"]),
            "LOTO_TEST_TASK_01": (["TASK_02", "TASK_03"], ["TASK_01"]),
        }

        for fold in folds:
            self.assertIn(fold.fold_id, expected_configs)
            train_tasks, test_tasks = expected_configs[fold.fold_id]
            self.assertEqual(fold.train_tasks, train_tasks)
            self.assertEqual(fold.test_tasks, test_tasks)

            # Sample counts (30 train = 10H + 20A; 15 test = 5H + 10A)
            self.assertEqual(fold.n_train_total, 30)
            self.assertEqual(fold.n_train_human, 10)
            self.assertEqual(fold.n_train_automated, 20)
            self.assertEqual(fold.n_test_total, 15)
            self.assertEqual(fold.n_test_human, 5)
            self.assertEqual(fold.n_test_automated, 10)

            # Multiclass presence
            self.assertTrue(fold.is_train_multiclass)
            self.assertTrue(fold.is_test_multiclass)

            # Group overlap: participants exist across tasks
            self.assertIn("p_01", fold.overlapping_participants)
            self.assertFalse(fold.is_group_disjoint)
            self.assertEqual(fold.validity_status, "VALID_WITH_GROUP_LEAKAGE_WARNING")

    def test_strict_group_isolation_pathology_detected(self):
        """
        When strict group isolation is enforced, LOTO folds must be flagged as invalid
        because removing overlapping participants purges all participants from train.
        """
        strict_folds = EvaluationProtocol.generate_loto_folds(self.meta, enforce_strict_groups=True)
        for fold in strict_folds:
            self.assertFalse(fold.is_valid)
            self.assertEqual(fold.validity_status, "INVALID_SINGLE_CLASS_TRAIN")
            self.assertEqual(fold.n_train_human, 0)

    def test_logo_p01_fold(self):
        """Testing on p_01 retains other human participants in train."""
        group_folds = EvaluationProtocol.generate_group_folds(self.meta)
        p01_fold = [f for f in group_folds if "p_01" in f.test_participants][0]
        self.assertTrue(p01_fold.is_valid)
        self.assertEqual(p01_fold.validity_status, "TEST_SINGLE_CLASS")
        self.assertEqual(p01_fold.n_train_human, 12)  # p_02, p_03, p_04, p_05
        self.assertEqual(p01_fold.n_test_human, 3)

    def test_baseline_classifier_majority(self):
        """Baseline classifier majority strategy behaves deterministically."""
        clf = BaselineClassifier(strategy="majority")
        clf.fit(self.X, self.y)
        preds = clf.predict(self.X)
        self.assertEqual(clf.majority_class_, 1)  # 30 automated vs 15 human
        self.assertTrue(np.all(preds == 1))

        probs = clf.predict_proba(self.X)
        self.assertEqual(probs.shape, (len(self.X), 2))
        np.testing.assert_allclose(probs[:, 1], 30.0 / 45.0)
        np.testing.assert_allclose(probs[:, 0], 15.0 / 45.0)

    def test_research_comparison_specification(self):
        """Verify comparison specification contracts."""
        spec = ResearchComparisonSpecification()
        self.assertEqual(spec.status, "SPECIFIED_NOT_TRAINED")
        self.assertEqual(spec.baseline_model, "MajorityClassBaselineClassifier")
        self.assertIn("H0", spec.hypotheses)
        self.assertIn("H1", spec.hypotheses)


if __name__ == "__main__":
    unittest.main()
