"""
Unit Test Suite for Controlled Labeled Dataset Collection.
Validates:
1. Correct HUMAN label assignment (0)
2. Correct AUTOMATED label assignment (1)
3. Target label is separated and not included in the 76 behavioral features
4. Decoupling of ML features (features.csv) from collection metadata (metadata.csv)
5. Multi-task support across TASK_01, TASK_02, TASK_03
6. Session isolation (no cross-session contamination)
7. Zero keyboard content / PII leakage
8. Dataset CSV export and schema integrity
9. Quality reporting with class balance, task breakdown, and rejected session tracking
"""

import os
import shutil
import tempfile
import unittest
import pandas as pd

from ml.features.extractor import FEATURE_COLUMNS
from ml.features.pipeline import DatasetPipeline
from ml.data_collection.tasks import TASKS, get_task, get_all_task_ids
from ml.data_collection.automated_collector import AutomatedSessionGenerator


class TestDatasetCollection(unittest.TestCase):

    def setUp(self):
        self.pipeline = DatasetPipeline()
        self.collector = AutomatedSessionGenerator()
        self.temp_dir = tempfile.mkdtemp(prefix="test_dataset_")

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_tasks_defined_and_retrievable(self):
        """Verify canonical tasks (TASK_01, TASK_02, TASK_03) are registered with valid step sequences."""
        task_ids = get_all_task_ids()
        self.assertIn("TASK_01", task_ids)
        self.assertIn("TASK_02", task_ids)
        self.assertIn("TASK_03", task_ids)
        self.assertEqual(len(task_ids), 3)

        for tid in task_ids:
            task = get_task(tid)
            self.assertEqual(task.task_id, tid)
            self.assertGreater(len(task.steps), 0)
            self.assertTrue(len(task.target_routes) > 0)

    def test_human_label_assignment(self):
        """Verify sessions marked HUMAN receive authoritative label 0."""
        sessions = {
            "sess_human_01": [
                {"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 100, "y": 200, "distance_px": 10, "velocity_px_s": 250}},
                {"event_type": "mouse_click", "client_timestamp": 1400, "event_data": {"x": 100, "y": 200, "button": 0, "target_category": "button"}},
            ]
        }
        metadata = {
            "sess_human_01": {
                "session_id": "sess_human_01",
                "collection_mode": "HUMAN",
                "task_id": "TASK_01",
                "collection_timestamp": 1000
            }
        }

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        self.assertEqual(len(features_df), 1)
        self.assertEqual(features_df["label"].iloc[0], 0)
        self.assertEqual(metadata_df["label"].iloc[0], 0)
        self.assertEqual(metadata_df["collection_mode"].iloc[0], "HUMAN")
        self.assertEqual(report["total_human_sessions"], 1)
        self.assertEqual(report["total_automated_sessions"], 0)

    def test_automated_label_assignment(self):
        """Verify sessions marked AUTOMATED receive authoritative label 1."""
        events = self.collector.generate_task_events("TASK_01")
        sessions = {"sess_auto_01": events}
        metadata = {
            "sess_auto_01": {
                "session_id": "sess_auto_01",
                "collection_mode": "AUTOMATED",
                "task_id": "TASK_01",
                "collection_timestamp": 1000
            }
        }

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        self.assertEqual(len(features_df), 1)
        self.assertEqual(features_df["label"].iloc[0], 1)
        self.assertEqual(metadata_df["label"].iloc[0], 1)
        self.assertEqual(metadata_df["collection_mode"].iloc[0], "AUTOMATED")
        self.assertEqual(report["total_human_sessions"], 0)
        self.assertEqual(report["total_automated_sessions"], 1)

    def test_label_not_included_as_feature(self):
        """
        Verify label is NEVER considered a behavioral feature.
        The 76 feature columns must contain only behavioral statistics.
        """
        self.assertNotIn("label", FEATURE_COLUMNS)
        self.assertNotIn("session_id", FEATURE_COLUMNS)
        self.assertNotIn("collection_mode", FEATURE_COLUMNS)
        self.assertNotIn("task_id", FEATURE_COLUMNS)
        self.assertNotIn("is_automated", FEATURE_COLUMNS)
        self.assertNotIn("user_agent", FEATURE_COLUMNS)
        self.assertNotIn("ip_hash", FEATURE_COLUMNS)
        self.assertEqual(len(FEATURE_COLUMNS), 76)

    def test_collection_metadata_separation(self):
        """Verify features.csv and metadata.csv are exported separately with strictly decoupled schemas."""
        sessions = {
            "sess_h1": [
                {"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 50, "y": 60, "distance_px": 5, "velocity_px_s": 150}},
            ],
            "sess_a1": self.collector.generate_task_events("TASK_02")
        }
        metadata = {
            "sess_h1": {"session_id": "sess_h1", "collection_mode": "HUMAN", "task_id": "TASK_01", "collection_timestamp": 1000, "label": 0},
            "sess_a1": {"session_id": "sess_a1", "collection_mode": "AUTOMATED", "task_id": "TASK_02", "collection_timestamp": 2000, "label": 1},
        }

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        paths = self.pipeline.export_dataset(features_df, metadata_df, output_dir=self.temp_dir)

        features_path = paths["features_csv"]
        metadata_path = paths["metadata_csv"]
        self.assertTrue(os.path.exists(features_path))
        self.assertTrue(os.path.exists(metadata_path))

        # Check features.csv: strictly 76 features + 1 target label = 77 columns
        loaded_features = pd.read_csv(features_path)
        self.assertEqual(len(loaded_features), 2)
        self.assertIn("label", loaded_features.columns)
        self.assertNotIn("session_id", loaded_features.columns)
        self.assertNotIn("collection_mode", loaded_features.columns)
        self.assertNotIn("task_id", loaded_features.columns)
        self.assertEqual(loaded_features.shape[1], 77)

        # Check metadata.csv: contains research traceability fields
        loaded_metadata = pd.read_csv(metadata_path)
        self.assertEqual(len(loaded_metadata), 2)
        self.assertIn("session_id", loaded_metadata.columns)
        self.assertIn("collection_mode", loaded_metadata.columns)
        self.assertIn("task_id", loaded_metadata.columns)
        self.assertIn("collection_timestamp", loaded_metadata.columns)
        self.assertIn("label", loaded_metadata.columns)
        # Behavioral features must NOT be in metadata
        self.assertNotIn("mouse_mean_velocity", loaded_metadata.columns)

    def test_multi_task_support(self):
        """Verify dataset collection supports multiple tasks with both classes represented under each task."""
        sessions = {}
        metadata = {}

        tasks = ["TASK_01", "TASK_02", "TASK_03"]
        for tid in tasks:
            # Human session
            h_id = f"sess_human_{tid}"
            sessions[h_id] = [
                {"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 10, "y": 20, "distance_px": 5, "velocity_px_s": 200}},
                {"event_type": "key_meta", "client_timestamp": 1200, "event_data": {"dwell_ms": 90, "flight_ms": 110}},
            ]
            metadata[h_id] = {"session_id": h_id, "collection_mode": "HUMAN", "task_id": tid, "collection_timestamp": 1000, "label": 0}

            # Automated session
            a_id = f"sess_auto_{tid}"
            sessions[a_id] = self.collector.generate_task_events(tid)
            metadata[a_id] = {"session_id": a_id, "collection_mode": "AUTOMATED", "task_id": tid, "collection_timestamp": 2000, "label": 1}

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        self.assertEqual(report["usable_sessions"], 6)
        self.assertEqual(report["total_human_sessions"], 3)
        self.assertEqual(report["total_automated_sessions"], 3)
        self.assertEqual(report["class_balance"], "0.5:0.5")

        by_task = report["sessions_by_task"]
        self.assertEqual(by_task.get("TASK_01"), 2)
        self.assertEqual(by_task.get("TASK_02"), 2)
        self.assertEqual(by_task.get("TASK_03"), 2)

    def test_session_isolation(self):
        """Verify sessions are isolated and events never cross-contaminate between sessions."""
        events_s1 = [
            {"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 0, "y": 0, "distance_px": 100, "velocity_px_s": 500}},
            {"event_type": "mouse_move", "client_timestamp": 1200, "event_data": {"x": 100, "y": 0, "distance_px": 100, "velocity_px_s": 500}},
        ]
        events_s2 = [
            {"event_type": "scroll", "client_timestamp": 2000, "event_data": {"scroll_x": 0, "scroll_y": 500, "delta_y": 500, "velocity_px_s": 1000}},
        ]

        sessions = {"s1": events_s1, "s2": events_s2}
        metadata = {
            "s1": {"collection_mode": "HUMAN", "task_id": "TASK_01", "label": 0},
            "s2": {"collection_mode": "AUTOMATED", "task_id": "TASK_01", "label": 1}
        }

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        f_s1 = features_df.iloc[0]
        f_s2 = features_df.iloc[1]

        # s1 had only mouse movements, no scrolls
        self.assertEqual(f_s1["mouse_event_count"], 2.0)
        self.assertEqual(f_s1["scroll_event_count"], 0.0)

        # s2 had only scroll, no mouse movements
        self.assertEqual(f_s2["mouse_event_count"], 0.0)
        self.assertEqual(f_s2["scroll_event_count"], 1.0)

    def test_no_keyboard_content_leakage(self):
        """Verify no raw keystroke characters, strings, or text leak into feature matrix or metadata."""
        # Simulated keystroke events following SDK specification
        keystrokes = [
            {
                "event_type": "key_meta",
                "client_timestamp": 1000,
                "event_data": {
                    "dwell_ms": 75,
                    "flight_ms": 95,
                    "inter_key_interval_ms": 170,
                    "is_backspace": False,
                    "is_paste": False
                }
            },
            {
                "event_type": "key_meta",
                "client_timestamp": 1170,
                "event_data": {
                    "dwell_ms": 80,
                    "flight_ms": 110,
                    "inter_key_interval_ms": 190,
                    "is_backspace": True,
                    "is_paste": False
                }
            }
        ]

        sessions = {"sess_keystroke_test": keystrokes}
        metadata = {"sess_keystroke_test": {"collection_mode": "HUMAN", "task_id": "TASK_02", "label": 0}}

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)

        # Ensure no character keys exist anywhere in columns or values
        disallowed_terms = ["char", "character", "key_name", "letter", "password", "text", "query_text", "value"]
        for col in features_df.columns:
            for term in disallowed_terms:
                self.assertNotIn(term, col.lower())

        for col in metadata_df.columns:
            for term in disallowed_terms:
                self.assertNotIn(term, col.lower())

    def test_deterministic_mode_unchanged(self):
        """Verify AUTOMATED_DETERMINISTIC retains perfectly rigid baseline kinematics."""
        events = self.collector.generate_task_events("TASK_01", condition="AUTOMATED_DETERMINISTIC", base_time_ms=1000)
        mouse_moves = [e for e in events if e["event_type"] == "mouse_move"]
        self.assertGreater(len(mouse_moves), 0)

        # Baseline: zero direction changes, zero acceleration, constant velocity (500 px/s)
        for m in mouse_moves:
            self.assertEqual(m["event_data"]["direction_change_deg"], 0.0)
            self.assertEqual(m["event_data"]["acceleration_px_s2"], 0.0)
            self.assertEqual(m["event_data"]["velocity_px_s"], 500.0)

        # Baseline typing for TASK_02: 50ms dwell, 70ms flight
        key_events = self.collector.generate_task_events("TASK_02", condition="AUTOMATED_DETERMINISTIC", base_time_ms=1000)
        keystrokes = [e for e in key_events if e["event_type"] == "key_meta"]
        self.assertGreater(len(keystrokes), 0)
        for k in keystrokes:
            self.assertEqual(k["event_data"]["dwell_ms"], 50)
            self.assertEqual(k["event_data"]["flight_ms"], 70)

    def test_variable_mode_reproducible_with_same_seed(self):
        """Verify AUTOMATED_VARIABLE is 100% reproducible when run with the identical random seed."""
        ev1 = self.collector.generate_task_events("TASK_01", base_time_ms=5000, condition="AUTOMATED_VARIABLE", seed=42)
        ev2 = self.collector.generate_task_events("TASK_01", base_time_ms=5000, condition="AUTOMATED_VARIABLE", seed=42)
        self.assertEqual(ev1, ev2, "Identical seed must yield identical event telemetry")

        # Different seed must produce different telemetry
        ev3 = self.collector.generate_task_events("TASK_01", base_time_ms=5000, condition="AUTOMATED_VARIABLE", seed=43)
        self.assertNotEqual(ev1, ev3, "Different seeds must yield distinct event telemetry")

    def test_variable_mode_produces_non_zero_behavioral_variation(self):
        """Verify AUTOMATED_VARIABLE introduces non-zero curvature, direction changes, and velocity variations."""
        events_t1 = self.collector.generate_task_events("TASK_01", base_time_ms=5000, condition="AUTOMATED_VARIABLE", seed=42)
        features_t1 = self.pipeline.extractor.extract_features(events_t1)

        # Non-zero direction changes and acceleration
        self.assertGreater(features_t1["mouse_direction_change_count"], 0)
        self.assertGreater(features_t1["mouse_mean_acceleration"], 0)
        self.assertGreater(features_t1["mouse_max_acceleration"], 0)

        # Variable typing for TASK_02
        events_t2 = self.collector.generate_task_events("TASK_02", base_time_ms=5000, condition="AUTOMATED_VARIABLE", seed=42)
        keystrokes = [e for e in events_t2 if e["event_type"] == "key_meta"]
        dwells = [k["event_data"]["dwell_ms"] for k in keystrokes]
        flights = [k["event_data"]["flight_ms"] for k in keystrokes]

        # Ensure dwell and flight are NOT uniform constants
        self.assertGreater(len(set(dwells)), 1, "Dwell timings must vary")
        self.assertGreater(len(set(flights)), 1, "Flight timings must vary")
        # Ensure within reasonable bounds
        for d in dwells:
            self.assertTrue(35 <= d <= 85)
        for f in flights:
            self.assertTrue(45 <= f <= 110)

        # Variable scroll for TASK_01
        scrolls = [e for e in events_t1 if e["event_type"] == "scroll"]
        scroll_dists = [s["event_data"]["delta_y"] for s in scrolls]
        scroll_intervals = [s["event_data"]["time_since_last_scroll_ms"] for s in scrolls]
        self.assertGreater(len(set(scroll_dists)), 1, "Scroll distances must vary")
        self.assertGreater(len(set(scroll_intervals)), 1, "Scroll intervals must vary")

    def test_authoritative_labels_both_automation_conditions(self):
        """Verify both AUTOMATED_DETERMINISTIC and AUTOMATED_VARIABLE strictly receive label 1."""
        ev_det = self.collector.generate_task_events("TASK_01", condition="AUTOMATED_DETERMINISTIC")
        ev_var = self.collector.generate_task_events("TASK_01", condition="AUTOMATED_VARIABLE", seed=42)

        sessions = {"sess_det": ev_det, "sess_var": ev_var}
        metadata = {
            "sess_det": {"collection_mode": "AUTOMATED", "automation_condition": "AUTOMATED_DETERMINISTIC", "task_id": "TASK_01"},
            "sess_var": {"collection_mode": "AUTOMATED", "automation_condition": "AUTOMATED_VARIABLE", "task_id": "TASK_01"},
        }

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        self.assertEqual(len(features_df), 2)
        self.assertEqual(features_df["label"].iloc[0], 1)
        self.assertEqual(features_df["label"].iloc[1], 1)
        self.assertEqual(metadata_df["label"].iloc[0], 1)
        self.assertEqual(metadata_df["label"].iloc[1], 1)
        self.assertEqual(metadata_df["automation_condition"].iloc[0], "AUTOMATED_DETERMINISTIC")
        self.assertEqual(metadata_df["automation_condition"].iloc[1], "AUTOMATED_VARIABLE")

    def test_metadata_separation_with_automation_condition_and_participant_id(self):
        """
        Verify metadata fields (automation_condition, participant_id) are stored ONLY in metadata.csv
        and NEVER leak into features.csv or FEATURE_COLUMNS.
        """
        sessions = {
            "s_h": [{"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 10, "y": 20, "distance_px": 5, "velocity_px_s": 200}}],
            "s_det": self.collector.generate_task_events("TASK_01", condition="AUTOMATED_DETERMINISTIC"),
            "s_var": self.collector.generate_task_events("TASK_01", condition="AUTOMATED_VARIABLE", seed=42),
        }
        metadata = {
            "s_h": {"collection_mode": "HUMAN", "automation_condition": "NONE", "participant_id": "p_alpha", "task_id": "TASK_01", "label": 0},
            "s_det": {"collection_mode": "AUTOMATED", "automation_condition": "AUTOMATED_DETERMINISTIC", "participant_id": "bot_det_01", "task_id": "TASK_01", "label": 1},
            "s_var": {"collection_mode": "AUTOMATED", "automation_condition": "AUTOMATED_VARIABLE", "participant_id": "bot_var_s42", "task_id": "TASK_01", "label": 1},
        }

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        paths = self.pipeline.export_dataset(features_df, metadata_df, output_dir=self.temp_dir)

        features_path = paths["features_csv"]
        metadata_path = paths["metadata_csv"]

        loaded_features = pd.read_csv(features_path)
        loaded_metadata = pd.read_csv(metadata_path)

        # features.csv must contain exactly 76 features + 1 label column = 77 columns
        self.assertEqual(loaded_features.shape[1], 77)
        self.assertIn("label", loaded_features.columns)
        self.assertNotIn("automation_condition", loaded_features.columns)
        self.assertNotIn("participant_id", loaded_features.columns)
        self.assertNotIn("collection_mode", loaded_features.columns)
        self.assertNotIn("session_id", loaded_features.columns)

        # metadata.csv must contain all provenance fields
        self.assertIn("automation_condition", loaded_metadata.columns)
        self.assertIn("participant_id", loaded_metadata.columns)
        self.assertIn("session_id", loaded_metadata.columns)
        self.assertIn("collection_mode", loaded_metadata.columns)
        self.assertIn("label", loaded_metadata.columns)

        # Verify values in metadata.csv
        conds = list(loaded_metadata["automation_condition"])
        self.assertIn("NONE", conds)
        self.assertIn("AUTOMATED_DETERMINISTIC", conds)
        self.assertIn("AUTOMATED_VARIABLE", conds)

        pids = list(loaded_metadata["participant_id"])
        self.assertIn("p_alpha", pids)
        self.assertIn("bot_det_01", pids)
        self.assertIn("bot_var_s42", pids)

        # Check quality report tracking
        self.assertEqual(report["sessions_by_automation_condition"]["AUTOMATED_DETERMINISTIC"], 1)
        self.assertEqual(report["sessions_by_automation_condition"]["AUTOMATED_VARIABLE"], 1)
        self.assertEqual(report["unique_participants_or_entities"], 3)

    def test_rejected_session_tracking(self):
        """Verify empty or invalid sessions are not silently discarded but recorded with failure reasons."""
        sessions = {
            "valid_sess": [{"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 1, "y": 2, "distance_px": 1, "velocity_px_s": 10}}],
            "empty_sess": []
        }
        metadata = {
            "valid_sess": {"collection_mode": "HUMAN", "task_id": "TASK_01", "label": 0},
            "empty_sess": {"collection_mode": "HUMAN", "task_id": "TASK_01", "label": 0}
        }

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        self.assertEqual(report["total_sessions_input"], 2)
        self.assertEqual(report["usable_sessions"], 1)
        self.assertEqual(report["skipped_sessions"], 1)
        self.assertEqual(len(report["skipped_details"]), 1)
        self.assertEqual(report["skipped_details"][0]["session_id"], "empty_sess")
        self.assertEqual(report["skipped_details"][0]["reason"], "EMPTY_SESSION_NO_EVENTS")

    def test_all_three_tasks_available_in_variable_mode(self):
        """Verify TASK_01, TASK_02, and TASK_03 all execute cleanly in AUTOMATED_VARIABLE mode."""
        for tid in ["TASK_01", "TASK_02", "TASK_03"]:
            events = self.collector.generate_task_events(tid, condition="AUTOMATED_VARIABLE", seed=77)
            self.assertGreater(len(events), 15, f"{tid} must produce valid event telemetry")
            features = self.pipeline.extractor.extract_features(events)
            self.assertEqual(len(features), 76)
            for k, val in features.items():
                self.assertFalse(pd.isna(val), f"Feature {k} had NaN in {tid}")


    def test_unlabeled_or_unspecified_session_rejected(self):
        """Verify sessions with collection_mode UNSPECIFIED or label None are quarantined."""
        events = [{"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 1, "y": 2, "distance_px": 1, "velocity_px_s": 10}}]
        sessions = {
            "zombie_sess": events,
            "valid_human": events
        }
        metadata = {
            "zombie_sess": {"collection_mode": "UNSPECIFIED", "task_id": "TASK_01", "label": None},
            "valid_human": {"collection_mode": "HUMAN", "task_id": "TASK_01", "label": 0, "status": "COMPLETED"}
        }

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        self.assertEqual(report["total_sessions_input"], 2)
        self.assertEqual(report["usable_sessions"], 1)
        self.assertEqual(report["skipped_sessions"], 1)
        self.assertEqual(report["skipped_details"][0]["session_id"], "zombie_sess")
        self.assertEqual(report["skipped_details"][0]["reason"], "REJECTED_UNLABELED_OR_UNSPECIFIED_SESSION")
        self.assertEqual(features_df["label"].iloc[0], 0)
        self.assertEqual(metadata_df["session_id"].iloc[0], "valid_human")

    def test_incomplete_session_rejected_when_status_available(self):
        """Verify non-COMPLETED sessions are quarantined if status is provided."""
        events = [{"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 1, "y": 2, "distance_px": 1, "velocity_px_s": 10}}]
        sessions = {
            "active_sess": events,
            "completed_sess": events
        }
        metadata = {
            "active_sess": {"collection_mode": "HUMAN", "task_id": "TASK_01", "label": 0, "status": "ACTIVE"},
            "completed_sess": {"collection_mode": "HUMAN", "task_id": "TASK_01", "label": 0, "status": "COMPLETED"}
        }

        features_df, metadata_df, report = self.pipeline.process_sessions(sessions, metadata)
        self.assertEqual(report["total_sessions_input"], 2)
        self.assertEqual(report["usable_sessions"], 1)
        self.assertEqual(report["skipped_sessions"], 1)
        self.assertEqual(report["skipped_details"][0]["session_id"], "active_sess")
        self.assertEqual(report["skipped_details"][0]["reason"], "REJECTED_SESSION_NOT_COMPLETED")
        self.assertEqual(metadata_df["session_id"].iloc[0], "completed_sess")


if __name__ == "__main__":
    unittest.main()

