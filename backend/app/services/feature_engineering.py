"""
Backend Feature Engineering Service.
Integrates behavioral feature extraction with session lifecycle and PostgreSQL persistence.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from ml.features.extractor import BehavioralFeatureExtractor, FEATURE_COLUMNS

class FeatureEngineeringService:
    """
    Orchestrates session-level feature extraction and database persistence.
    """

    def __init__(self):
        self.extractor = BehavioralFeatureExtractor()

    def extract_features(self, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Extracts 76 deterministic features from raw telemetry events.
        """
        return self.extractor.extract_features(events)

    async def compute_and_save_features(
        self,
        session_id: str,
        events: List[Dict[str, Any]],
        db: Optional[Any] = None
    ) -> Dict[str, float]:
        """
        Computes features from session events and persists to behavior_features table if database is active.
        """
        feature_vector = self.extract_features(events)

        if db is not None:
            try:
                from backend.app.models.behavior import BehaviorFeatureModel
                now = datetime.utcnow()
                
                # Window boundaries
                first_ts = now
                if events:
                    earliest_ms = min(ev.get("client_timestamp", 0) for ev in events)
                    if earliest_ms > 0:
                        first_ts = datetime.utcfromtimestamp(earliest_ms / 1000.0)

                feature_record = BehaviorFeatureModel(
                    session_id=session_id,
                    window_start=first_ts,
                    window_end=now,
                    # Mouse dynamics
                    mouse_velocity_mean=feature_vector.get("mouse_mean_velocity", 0.0),
                    mouse_velocity_std=feature_vector.get("mouse_std_velocity", 0.0),
                    mouse_acceleration_mean=feature_vector.get("mouse_mean_acceleration", 0.0),
                    mouse_direction_changes=int(feature_vector.get("mouse_direction_change_count", 0)),
                    mouse_path_straightness=feature_vector.get("mouse_path_straightness", 0.0),
                    # Click dynamics
                    click_count=int(feature_vector.get("click_count", 0)),
                    click_interval_mean=feature_vector.get("mean_click_interval_ms", 0.0),
                    click_interval_std=feature_vector.get("std_click_interval_ms", 0.0),
                    double_click_count=int(feature_vector.get("double_click_rate", 0.0) * feature_vector.get("click_count", 0)),
                    # Keystroke dynamics
                    typing_speed_cps=feature_vector.get("typing_speed", 0.0),
                    key_hold_mean_ms=feature_vector.get("mean_dwell_ms", 0.0),
                    key_hold_std_ms=feature_vector.get("std_dwell_ms", 0.0),
                    inter_key_interval_mean_ms=feature_vector.get("mean_inter_key_interval_ms", 0.0),
                    backspace_rate=feature_vector.get("backspace_rate", 0.0),
                    paste_count=int(feature_vector.get("paste_rate", 0.0) * feature_vector.get("key_event_count", 0)),
                    # Scroll dynamics
                    scroll_count=int(feature_vector.get("scroll_event_count", 0)),
                    scroll_velocity_mean=feature_vector.get("mean_scroll_velocity", 0.0),
                    scroll_direction_reversals=int(feature_vector.get("scroll_direction_change_count", 0)),
                    # Sequence dynamics
                    time_between_actions_mean_ms=feature_vector.get("mean_click_interval_ms", 0.0),
                    repeated_pattern_ratio=feature_vector.get("route_repetition_ratio", 0.0),
                    created_at=now,
                )
                db.add(feature_record)
                await db.commit()
            except Exception as e:
                if hasattr(db, 'rollback'):
                    await db.rollback()
                print(f"[FeatureEngineering DB Warning] Could not persist features: {e}")

        return feature_vector

feature_engineering_service = FeatureEngineeringService()
