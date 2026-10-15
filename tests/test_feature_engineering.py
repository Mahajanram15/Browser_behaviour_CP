"""
Comprehensive Test Suite for Behavioral Feature Engineering Pipeline.
Validates extraction correctness, numerical safety (no NaN/Inf), edge cases, determinism, and privacy guarantees.
Uses standard Python unittest for zero-dependency execution.
"""

import math
import unittest
from ml.features.extractor import BehavioralFeatureExtractor, FEATURE_COLUMNS
from ml.features.pipeline import DatasetPipeline


class TestFeatureEngineering(unittest.TestCase):

    def setUp(self):
        self.extractor = BehavioralFeatureExtractor()
        self.pipeline = DatasetPipeline()

    def test_feature_columns_count(self):
        """Verify exactly 76 canonical features are defined."""
        self.assertEqual(len(FEATURE_COLUMNS), 76)
        self.assertEqual(len(set(FEATURE_COLUMNS)), 76)

    def test_zero_event_session(self):
        """Empty session must return all 76 features with clean 0.0 values, zero NaNs or Infs."""
        features = self.extractor.extract_features([])
        self.assertEqual(len(features), 76)
        for col in FEATURE_COLUMNS:
            self.assertIn(col, features)
            val = features[col]
            self.assertIsInstance(val, (int, float))
            self.assertFalse(math.isnan(val))
            self.assertFalse(math.isinf(val))
            self.assertEqual(val, 0.0)

    def test_mouse_feature_extraction(self):
        """Verify mathematical correctness of mouse movement features."""
        events = [
            {
                "event_type": "mouse_move",
                "client_timestamp": 1000,
                "event_data": {"x": 0, "y": 0, "distance_px": 0, "time_delta_ms": 0, "velocity_px_s": 0, "acceleration_px_s2": 0, "direction_change_deg": 0}
            },
            {
                "event_type": "mouse_move",
                "client_timestamp": 1050,
                "event_data": {"x": 30, "y": 40, "distance_px": 50, "time_delta_ms": 50, "velocity_px_s": 1000, "acceleration_px_s2": 20, "direction_change_deg": 15}
            },
            {
                "event_type": "mouse_move",
                "client_timestamp": 1100,
                "event_data": {"x": 60, "y": 80, "distance_px": 50, "time_delta_ms": 50, "velocity_px_s": 1000, "acceleration_px_s2": 0, "direction_change_deg": 0}
            }
        ]

        features = self.extractor.extract_features(events)
        self.assertEqual(features["mouse_event_count"], 3.0)
        self.assertEqual(features["mouse_total_distance_px"], 100.0)
        self.assertGreater(features["mouse_mean_velocity"], 0)
        self.assertEqual(features["mouse_direction_change_count"], 1.0)
        self.assertEqual(features["mouse_path_straightness"], 1.0)

    def test_click_feature_extraction(self):
        """Verify click intervals and target category ratios."""
        events = [
            {
                "event_type": "mouse_click",
                "client_timestamp": 2000,
                "event_data": {"x": 100, "y": 200, "button": 0, "click_type": "single", "time_since_last_click_ms": 0, "target_category": "button"}
            },
            {
                "event_type": "mouse_click",
                "client_timestamp": 2500,
                "event_data": {"x": 100, "y": 200, "button": 0, "click_type": "single", "time_since_last_click_ms": 500, "target_category": "link"}
            },
            {
                "event_type": "mouse_click",
                "client_timestamp": 2700,
                "event_data": {"x": 100, "y": 200, "button": 0, "click_type": "double", "time_since_last_click_ms": 200, "target_category": "button"}
            }
        ]

        features = self.extractor.extract_features(events)
        self.assertEqual(features["click_count"], 3.0)
        self.assertEqual(features["button_click_ratio"], round(2 / 3, 4))
        self.assertEqual(features["link_click_ratio"], round(1 / 3, 4))
        self.assertEqual(features["double_click_rate"], round(1 / 3, 4))
        self.assertEqual(features["min_click_interval_ms"], 200.0)
        self.assertEqual(features["max_click_interval_ms"], 500.0)

    def test_keyboard_feature_extraction(self):
        """Verify keystroke dwell, flight, inter-key, backspace, and paste statistics."""
        events = [
            {
                "event_type": "key_meta",
                "client_timestamp": 3000,
                "event_data": {"dwell_ms": 80, "flight_ms": 120, "inter_key_interval_ms": 200, "is_backspace": False, "is_paste": False}
            },
            {
                "event_type": "key_meta",
                "client_timestamp": 3200,
                "event_data": {"dwell_ms": 100, "flight_ms": 140, "inter_key_interval_ms": 240, "is_backspace": True, "is_paste": False}
            },
            {
                "event_type": "key_meta",
                "client_timestamp": 3450,
                "event_data": {"dwell_ms": 0, "flight_ms": 0, "inter_key_interval_ms": 0, "is_backspace": False, "is_paste": True}
            }
        ]

        features = self.extractor.extract_features(events)
        self.assertEqual(features["key_event_count"], 3.0)
        self.assertEqual(features["backspace_rate"], round(1 / 3, 4))
        self.assertEqual(features["paste_rate"], round(1 / 3, 4))
        self.assertEqual(features["min_dwell_ms"], 80.0)
        self.assertEqual(features["max_dwell_ms"], 100.0)
        self.assertEqual(features["mean_dwell_ms"], 90.0)

    def test_scroll_feature_extraction(self):
        """Verify scroll velocities, direction ratios, and bursts."""
        events = [
            {
                "event_type": "scroll",
                "client_timestamp": 4000,
                "event_data": {"scroll_x": 0, "scroll_y": 100, "delta_x": 0, "delta_y": 100, "velocity_px_s": 500, "direction": "down", "time_since_last_scroll_ms": 0}
            },
            {
                "event_type": "scroll",
                "client_timestamp": 4150,
                "event_data": {"scroll_x": 0, "scroll_y": 200, "delta_x": 0, "delta_y": 100, "velocity_px_s": 600, "direction": "down", "time_since_last_scroll_ms": 150}
            },
            {
                "event_type": "scroll",
                "client_timestamp": 4500,
                "event_data": {"scroll_x": 0, "scroll_y": 150, "delta_x": 0, "delta_y": -50, "velocity_px_s": 300, "direction": "up", "time_since_last_scroll_ms": 350}
            }
        ]

        features = self.extractor.extract_features(events)
        self.assertEqual(features["scroll_event_count"], 3.0)
        self.assertEqual(features["downward_scroll_ratio"], round(2 / 3, 4))
        self.assertEqual(features["upward_scroll_ratio"], round(1 / 3, 4))
        self.assertEqual(features["scroll_direction_change_count"], 1.0)

    def test_navigation_feature_extraction(self):
        """Verify route repetition, unique routes, and dwell metrics."""
        events = [
            {
                "event_type": "navigation",
                "client_timestamp": 5000,
                "event_data": {"path": "/demo/landing", "referrer": "/", "dwell_time_ms": 3000, "sequence_number": 1}
            },
            {
                "event_type": "navigation",
                "client_timestamp": 8000,
                "event_data": {"path": "/demo/catalog", "referrer": "/demo/landing", "dwell_time_ms": 5000, "sequence_number": 2}
            },
            {
                "event_type": "navigation",
                "client_timestamp": 13000,
                "event_data": {"path": "/demo/landing", "referrer": "/demo/catalog", "dwell_time_ms": 2000, "sequence_number": 3}
            }
        ]

        features = self.extractor.extract_features(events)
        self.assertEqual(features["navigation_count"], 3.0)
        self.assertEqual(features["unique_route_count"], 2.0)
        self.assertEqual(features["repeated_route_count"], 1.0)
        self.assertEqual(features["route_repetition_ratio"], round(1 / 3, 4))
        self.assertEqual(features["mean_page_dwell_ms"], round((3000 + 5000 + 2000) / 3, 4))

    def test_visibility_feature_extraction(self):
        """Verify visibility states and time-away metrics."""
        events = [
            {
                "event_type": "visibility",
                "client_timestamp": 6000,
                "event_data": {"state": "hidden", "duration_away_ms": 0}
            },
            {
                "event_type": "visibility",
                "client_timestamp": 8000,
                "event_data": {"state": "visible", "duration_away_ms": 2000}
            }
        ]

        features = self.extractor.extract_features(events)
        self.assertEqual(features["visibility_event_count"], 2.0)
        self.assertEqual(features["hidden_event_count"], 1.0)
        self.assertEqual(features["total_time_away_ms"], 2000.0)
        self.assertEqual(features["mean_time_away_ms"], 2000.0)

    def test_zero_duration_and_extreme_edge_cases(self):
        """Verify that identical timestamps or zero-duration sessions never cause division by zero or NaN."""
        events = [
            {"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 10, "y": 10, "distance_px": 0, "time_delta_ms": 0, "velocity_px_s": 0}},
            {"event_type": "mouse_click", "client_timestamp": 1000, "event_data": {"x": 10, "y": 10, "button": 0, "time_since_last_click_ms": 0}},
            {"event_type": "key_meta", "client_timestamp": 1000, "event_data": {"dwell_ms": 0, "flight_ms": 0}},
        ]

        features = self.extractor.extract_features(events)
        self.assertEqual(len(features), 76)
        for k, v in features.items():
            self.assertFalse(math.isnan(v), f"NaN encountered in {k}")
            self.assertFalse(math.isinf(v), f"Inf encountered in {k}")

    def test_privacy_guarantee_no_key_or_text_leak(self):
        """
        STRICT PRIVACY TEST:
        Verifies that no text, input values, passwords, or key names ever appear in the extracted features.
        """
        secret_payload = {
            "event_type": "key_meta",
            "client_timestamp": 1000,
            "event_data": {
                "dwell_ms": 85,
                "flight_ms": 110,
                "inter_key_interval_ms": 195,
                "is_backspace": False,
                "is_paste": False,
                "key": "SUPER_SECRET_PASSWORD",
                "value": "credit_card_number_1234",
                "typed_text": "sensitive_query"
            }
        }

        features = self.extractor.extract_features([secret_payload])
        serialized = str(features)

        self.assertNotIn("SUPER_SECRET_PASSWORD", serialized)
        self.assertNotIn("credit_card_number_1234", serialized)
        self.assertNotIn("sensitive_query", serialized)
        self.assertNotIn("key", features)
        self.assertNotIn("value", features)
        self.assertNotIn("typed_text", features)

    def test_determinism_repeated_extractions(self):
        """Verify that identical inputs produce bit-for-bit identical feature dictionaries."""
        events = [
            {"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 10, "y": 20, "distance_px": 5, "velocity_px_s": 100, "direction_change_deg": 10}},
            {"event_type": "mouse_click", "client_timestamp": 1200, "event_data": {"x": 10, "y": 20, "button": 0, "click_type": "single", "target_category": "button"}},
            {"event_type": "key_meta", "client_timestamp": 1400, "event_data": {"dwell_ms": 70, "flight_ms": 90, "inter_key_interval_ms": 160}},
            {"event_type": "scroll", "client_timestamp": 1600, "event_data": {"scroll_x": 0, "scroll_y": 50, "delta_y": 50, "velocity_px_s": 200, "direction": "down"}},
            {"event_type": "navigation", "client_timestamp": 2000, "event_data": {"path": "/demo/home", "dwell_time_ms": 2000}},
            {"event_type": "visibility", "client_timestamp": 2500, "event_data": {"state": "visible", "duration_away_ms": 0}}
        ]

        f1 = self.extractor.extract_features(events)
        f2 = self.extractor.extract_features(events)
        f3 = self.extractor.extract_features(events)

        self.assertEqual(f1, f2)
        self.assertEqual(f2, f3)

    def test_dataset_pipeline_processing_and_quality_report(self):
        """Verify dataset aggregation, quality audit calculation, and export."""
        sessions = {
            "sess_001": [
                {"event_type": "mouse_move", "client_timestamp": 1000, "event_data": {"x": 10, "y": 20, "distance_px": 5, "velocity_px_s": 100}},
                {"event_type": "mouse_click", "client_timestamp": 1200, "event_data": {"x": 10, "y": 20, "button": 0, "target_category": "button"}},
            ],
            "sess_002": [
                {"event_type": "key_meta", "client_timestamp": 1000, "event_data": {"dwell_ms": 80, "flight_ms": 100}},
            ],
            "sess_empty": []
        }
        labels = {"sess_001": 0, "sess_002": 1}

        df, report = self.pipeline.process_sessions(sessions, labels)

        self.assertEqual(len(df), 2)
        self.assertEqual(report["usable_sessions"], 2)
        self.assertEqual(report["skipped_sessions"], 1)
        self.assertEqual(report["nan_count_total"], 0)
        self.assertEqual(report["inf_count_total"], 0)
        self.assertTrue(report["is_train_ready"])
        self.assertIn("label", df.columns)
        self.assertEqual(set(df["label"].unique()), {0, 1})


if __name__ == "__main__":
    unittest.main()
