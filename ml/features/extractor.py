"""
Deterministic Feature Extraction Engine for Browser Behavioral Telemetry.
Transforms raw privacy-preserving behavior_events into a validated numerical feature vector.
"""

from typing import List, Dict, Any, Optional
import math
import numpy as np

# Canonical feature list ordering (76 features across 7 behavioral groups)
FEATURE_COLUMNS: List[str] = [
    # A. Mouse Features (16)
    "mouse_event_count",
    "mouse_session_duration_ms",
    "mouse_total_distance_px",
    "mouse_mean_velocity",
    "mouse_std_velocity",
    "mouse_max_velocity",
    "mouse_mean_acceleration",
    "mouse_std_acceleration",
    "mouse_max_acceleration",
    "mouse_direction_change_count",
    "mouse_direction_change_rate",
    "mouse_mean_direction_change",
    "mouse_pause_count",
    "mouse_mean_pause_ms",
    "mouse_max_pause_ms",
    "mouse_path_straightness",

    # B. Click Features (11)
    "click_count",
    "click_rate",
    "mean_click_interval_ms",
    "std_click_interval_ms",
    "min_click_interval_ms",
    "max_click_interval_ms",
    "double_click_rate",
    "button_click_ratio",
    "link_click_ratio",
    "input_click_ratio",
    "other_click_ratio",

    # C. Keyboard Features (14)
    "key_event_count",
    "mean_dwell_ms",
    "std_dwell_ms",
    "min_dwell_ms",
    "max_dwell_ms",
    "mean_flight_ms",
    "std_flight_ms",
    "min_flight_ms",
    "max_flight_ms",
    "mean_inter_key_interval_ms",
    "std_inter_key_interval_ms",
    "typing_speed",
    "backspace_rate",
    "paste_rate",

    # D. Scroll Features (10)
    "scroll_event_count",
    "total_scroll_distance",
    "mean_scroll_velocity",
    "std_scroll_velocity",
    "max_scroll_velocity",
    "upward_scroll_ratio",
    "downward_scroll_ratio",
    "scroll_direction_change_count",
    "mean_scroll_interval_ms",
    "scroll_burst_count",

    # E. Navigation Features (9)
    "navigation_count",
    "unique_route_count",
    "mean_page_dwell_ms",
    "std_page_dwell_ms",
    "min_page_dwell_ms",
    "max_page_dwell_ms",
    "navigation_rate",
    "repeated_route_count",
    "route_repetition_ratio",

    # F. Visibility / Focus Features (8)
    "visibility_event_count",
    "hidden_event_count",
    "focus_event_count",
    "blur_event_count",
    "total_time_away_ms",
    "mean_time_away_ms",
    "max_time_away_ms",
    "time_away_ratio",

    # G. Cross-Behavior Session Features (8)
    "session_duration_ms",
    "total_behavior_event_count",
    "events_per_second",
    "active_behavior_duration_ms",
    "interaction_density",
    "mouse_to_click_ratio",
    "click_to_navigation_ratio",
    "navigation_to_session_ratio",
]


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely sanitize float values, eliminating NaN and Inf."""
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return round(f, 4)
    except (ValueError, TypeError):
        return default


def _calc_stats(arr: List[float]) -> Dict[str, float]:
    """Computes basic array summary statistics safely."""
    if not arr:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    clean_arr = [float(x) for x in arr if not (math.isnan(x) or math.isinf(x))]
    if not clean_arr:
        return {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
    
    mean = float(np.mean(clean_arr))
    std = float(np.std(clean_arr)) if len(clean_arr) > 1 else 0.0
    return {
        "mean": _safe_float(mean),
        "std": _safe_float(std),
        "min": _safe_float(min(clean_arr)),
        "max": _safe_float(max(clean_arr)),
    }


class BehavioralFeatureExtractor:
    """
    Transforms raw session event lists into 76 deterministic numerical features.
    Guarantees strict privacy: Operates solely on behavioral dynamics without touching sensitive contents.
    """

    @classmethod
    def extract_features(cls, events: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        Extracts all feature groups for a given session's events.
        """
        if not events:
            return cls._get_default_feature_vector()

        # Sort events chronologically
        valid_events = []
        for ev in events:
            if isinstance(ev, dict) and "event_type" in ev:
                valid_events.append(ev)
        
        valid_events.sort(key=lambda x: x.get("client_timestamp", 0))

        # Partition events by type
        mouse_moves: List[Dict[str, Any]] = []
        clicks: List[Dict[str, Any]] = []
        keys: List[Dict[str, Any]] = []
        scrolls: List[Dict[str, Any]] = []
        navs: List[Dict[str, Any]] = []
        visibilities: List[Dict[str, Any]] = []

        for ev in valid_events:
            t = ev.get("event_type")
            if t == "mouse_move":
                mouse_moves.append(ev)
            elif t == "mouse_click":
                clicks.append(ev)
            elif t == "key_meta":
                keys.append(ev)
            elif t == "scroll":
                scrolls.append(ev)
            elif t == "navigation":
                navs.append(ev)
            elif t == "visibility":
                visibilities.append(ev)

        # 1. Session Timing Foundations
        first_ts = valid_events[0].get("client_timestamp", 0)
        last_ts = valid_events[-1].get("client_timestamp", 0)
        session_duration_ms = max(0.0, float(last_ts - first_ts))
        session_duration_sec = session_duration_ms / 1000.0 if session_duration_ms > 0 else 0.001

        # 2. Extract Sub-groups
        features: Dict[str, float] = {}
        features.update(cls._extract_mouse_features(mouse_moves, session_duration_ms))
        features.update(cls._extract_click_features(clicks, session_duration_sec))
        features.update(cls._extract_keyboard_features(keys, session_duration_sec))
        features.update(cls._extract_scroll_features(scrolls))
        features.update(cls._extract_navigation_features(navs, session_duration_sec))
        features.update(cls._extract_visibility_features(visibilities, session_duration_ms))
        features.update(cls._extract_cross_session_features(valid_events, session_duration_ms, features))

        # 3. Final sanitization pass ensuring all 76 keys exist with finite float values
        final_vector: Dict[str, float] = {}
        for col in FEATURE_COLUMNS:
            val = features.get(col, 0.0)
            final_vector[col] = _safe_float(val, 0.0)

        return final_vector

    @classmethod
    def _extract_mouse_features(cls, events: List[Dict[str, Any]], session_duration_ms: float) -> Dict[str, float]:
        count = len(events)
        if count == 0:
            return {
                "mouse_event_count": 0.0,
                "mouse_session_duration_ms": 0.0,
                "mouse_total_distance_px": 0.0,
                "mouse_mean_velocity": 0.0,
                "mouse_std_velocity": 0.0,
                "mouse_max_velocity": 0.0,
                "mouse_mean_acceleration": 0.0,
                "mouse_std_acceleration": 0.0,
                "mouse_max_acceleration": 0.0,
                "mouse_direction_change_count": 0.0,
                "mouse_direction_change_rate": 0.0,
                "mouse_mean_direction_change": 0.0,
                "mouse_pause_count": 0.0,
                "mouse_mean_pause_ms": 0.0,
                "mouse_max_pause_ms": 0.0,
                "mouse_path_straightness": 0.0,
            }

        velocities = []
        accelerations = []
        direction_changes = []
        distances = []
        pauses = []
        total_dist = 0.0

        first_ts = events[0].get("client_timestamp", 0)
        last_ts = events[-1].get("client_timestamp", 0)
        mouse_duration_ms = max(0.0, float(last_ts - first_ts))

        first_data = events[0].get("event_data", {})
        last_data = events[-1].get("event_data", {})
        start_x, start_y = float(first_data.get("x", 0)), float(first_data.get("y", 0))
        end_x, end_y = float(last_data.get("x", 0)), float(last_data.get("y", 0))
        direct_distance = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)

        dir_change_count = 0
        for ev in events:
            data = ev.get("event_data", {})
            v = float(data.get("velocity_px_s", data.get("velocity", 0)))
            a = float(data.get("acceleration_px_s2", data.get("acceleration", 0)))
            d = float(data.get("distance_px", 0))
            dc = float(data.get("direction_change_deg", 0))
            dt = float(data.get("time_delta_ms", 0))

            velocities.append(v)
            accelerations.append(a)
            distances.append(d)
            total_dist += d

            if dc > 5.0:  # Meaningful angular deflection (> 5 degrees)
                dir_change_count += 1
                direction_changes.append(dc)

            if dt > 100.0:  # Pause threshold: >100ms between movement updates
                pauses.append(dt)

        v_stats = _calc_stats(velocities)
        a_stats = _calc_stats(accelerations)
        dc_stats = _calc_stats(direction_changes)
        p_stats = _calc_stats(pauses)

        mouse_dur_sec = mouse_duration_ms / 1000.0 if mouse_duration_ms > 0 else 1.0
        straightness = (direct_distance / total_dist) if total_dist > 0 else 1.0
        straightness = min(1.0, max(0.0, straightness))

        return {
            "mouse_event_count": float(count),
            "mouse_session_duration_ms": _safe_float(mouse_duration_ms),
            "mouse_total_distance_px": _safe_float(total_dist),
            "mouse_mean_velocity": v_stats["mean"],
            "mouse_std_velocity": v_stats["std"],
            "mouse_max_velocity": v_stats["max"],
            "mouse_mean_acceleration": a_stats["mean"],
            "mouse_std_acceleration": a_stats["std"],
            "mouse_max_acceleration": a_stats["max"],
            "mouse_direction_change_count": float(dir_change_count),
            "mouse_direction_change_rate": _safe_float(dir_change_count / mouse_dur_sec),
            "mouse_mean_direction_change": dc_stats["mean"],
            "mouse_pause_count": float(len(pauses)),
            "mouse_mean_pause_ms": p_stats["mean"],
            "mouse_max_pause_ms": p_stats["max"],
            "mouse_path_straightness": _safe_float(straightness),
        }

    @classmethod
    def _extract_click_features(cls, events: List[Dict[str, Any]], session_duration_sec: float) -> Dict[str, float]:
        count = len(events)
        if count == 0:
            return {
                "click_count": 0.0,
                "click_rate": 0.0,
                "mean_click_interval_ms": 0.0,
                "std_click_interval_ms": 0.0,
                "min_click_interval_ms": 0.0,
                "max_click_interval_ms": 0.0,
                "double_click_rate": 0.0,
                "button_click_ratio": 0.0,
                "link_click_ratio": 0.0,
                "input_click_ratio": 0.0,
                "other_click_ratio": 0.0,
            }

        intervals = []
        double_clicks = 0
        cat_counts = {"button": 0, "link": 0, "input": 0, "other": 0}

        for ev in events:
            data = ev.get("event_data", {})
            interval = float(data.get("time_since_last_click_ms", 0))
            if interval > 0:
                intervals.append(interval)

            if data.get("click_type") == "double":
                double_clicks += 1

            cat = str(data.get("target_category", "other")).lower()
            if cat in cat_counts:
                cat_counts[cat] += 1
            else:
                cat_counts["other"] += 1

        stats = _calc_stats(intervals)
        click_rate = count / session_duration_sec if session_duration_sec > 0 else 0.0

        return {
            "click_count": float(count),
            "click_rate": _safe_float(click_rate),
            "mean_click_interval_ms": stats["mean"],
            "std_click_interval_ms": stats["std"],
            "min_click_interval_ms": stats["min"],
            "max_click_interval_ms": stats["max"],
            "double_click_rate": _safe_float(double_clicks / count),
            "button_click_ratio": _safe_float(cat_counts["button"] / count),
            "link_click_ratio": _safe_float(cat_counts["link"] / count),
            "input_click_ratio": _safe_float(cat_counts["input"] / count),
            "other_click_ratio": _safe_float(cat_counts["other"] / count),
        }

    @classmethod
    def _extract_keyboard_features(cls, events: List[Dict[str, Any]], session_duration_sec: float) -> Dict[str, float]:
        count = len(events)
        if count == 0:
            return {
                "key_event_count": 0.0,
                "mean_dwell_ms": 0.0,
                "std_dwell_ms": 0.0,
                "min_dwell_ms": 0.0,
                "max_dwell_ms": 0.0,
                "mean_flight_ms": 0.0,
                "std_flight_ms": 0.0,
                "min_flight_ms": 0.0,
                "max_flight_ms": 0.0,
                "mean_inter_key_interval_ms": 0.0,
                "std_inter_key_interval_ms": 0.0,
                "typing_speed": 0.0,
                "backspace_rate": 0.0,
                "paste_rate": 0.0,
            }

        dwells = []
        flights = []
        inter_keys = []
        backspaces = 0
        pastes = 0

        for ev in events:
            data = ev.get("event_data", {})
            dwell = float(data.get("dwell_ms", data.get("hold_duration_ms", 0)))
            flight = float(data.get("flight_ms", data.get("flight_time_ms", 0)))
            inter = float(data.get("inter_key_interval_ms", 0))

            if dwell > 0:
                dwells.append(dwell)
            if flight > 0:
                flights.append(flight)
            if inter > 0:
                inter_keys.append(inter)

            if data.get("is_backspace") is True:
                backspaces += 1
            if data.get("is_paste") is True:
                pastes += 1

        d_stats = _calc_stats(dwells)
        f_stats = _calc_stats(flights)
        i_stats = _calc_stats(inter_keys)

        typing_speed = count / session_duration_sec if session_duration_sec > 0 else 0.0

        return {
            "key_event_count": float(count),
            "mean_dwell_ms": d_stats["mean"],
            "std_dwell_ms": d_stats["std"],
            "min_dwell_ms": d_stats["min"],
            "max_dwell_ms": d_stats["max"],
            "mean_flight_ms": f_stats["mean"],
            "std_flight_ms": f_stats["std"],
            "min_flight_ms": f_stats["min"],
            "max_flight_ms": f_stats["max"],
            "mean_inter_key_interval_ms": i_stats["mean"],
            "std_inter_key_interval_ms": i_stats["std"],
            "typing_speed": _safe_float(typing_speed),
            "backspace_rate": _safe_float(backspaces / count),
            "paste_rate": _safe_float(pastes / count),
        }

    @classmethod
    def _extract_scroll_features(cls, events: List[Dict[str, Any]]) -> Dict[str, float]:
        count = len(events)
        if count == 0:
            return {
                "scroll_event_count": 0.0,
                "total_scroll_distance": 0.0,
                "mean_scroll_velocity": 0.0,
                "std_scroll_velocity": 0.0,
                "max_scroll_velocity": 0.0,
                "upward_scroll_ratio": 0.0,
                "downward_scroll_ratio": 0.0,
                "scroll_direction_change_count": 0.0,
                "mean_scroll_interval_ms": 0.0,
                "scroll_burst_count": 0.0,
            }

        velocities = []
        intervals = []
        total_dist = 0.0
        up_count = 0
        down_count = 0
        dir_changes = 0
        burst_count = 0
        last_dir = None

        for ev in events:
            data = ev.get("event_data", {})
            v = float(data.get("velocity_px_s", data.get("velocity", 0)))
            dy = float(data.get("delta_y", 0))
            dx = float(data.get("delta_x", 0))
            dt = float(data.get("time_since_last_scroll_ms", 0))
            direction = str(data.get("direction", "none")).lower()

            velocities.append(abs(v))
            dist = math.sqrt(dx * dx + dy * dy)
            total_dist += dist

            if dt > 0:
                intervals.append(dt)
            if dt > 200.0 or last_dir is None:  # Burst boundary: >200ms pause
                burst_count += 1

            if direction == "up" or dy < 0:
                up_count += 1
            elif direction == "down" or dy > 0:
                down_count += 1

            if last_dir and direction in ["up", "down"] and last_dir in ["up", "down"] and direction != last_dir:
                dir_changes += 1

            if direction in ["up", "down"]:
                last_dir = direction

        v_stats = _calc_stats(velocities)
        i_stats = _calc_stats(intervals)

        return {
            "scroll_event_count": float(count),
            "total_scroll_distance": _safe_float(total_dist),
            "mean_scroll_velocity": v_stats["mean"],
            "std_scroll_velocity": v_stats["std"],
            "max_scroll_velocity": v_stats["max"],
            "upward_scroll_ratio": _safe_float(up_count / count),
            "downward_scroll_ratio": _safe_float(down_count / count),
            "scroll_direction_change_count": float(dir_changes),
            "mean_scroll_interval_ms": i_stats["mean"],
            "scroll_burst_count": float(max(1, burst_count)),
        }

    @classmethod
    def _extract_navigation_features(cls, events: List[Dict[str, Any]], session_duration_sec: float) -> Dict[str, float]:
        count = len(events)
        if count == 0:
            return {
                "navigation_count": 0.0,
                "unique_route_count": 0.0,
                "mean_page_dwell_ms": 0.0,
                "std_page_dwell_ms": 0.0,
                "min_page_dwell_ms": 0.0,
                "max_page_dwell_ms": 0.0,
                "navigation_rate": 0.0,
                "repeated_route_count": 0.0,
                "route_repetition_ratio": 0.0,
            }

        routes = []
        dwells = []
        seen_routes = set()
        repeated_routes = 0

        for ev in events:
            data = ev.get("event_data", {})
            path = str(data.get("path", "/")).strip()
            dwell = float(data.get("dwell_time_ms", 0))

            routes.append(path)
            if dwell > 0:
                dwells.append(dwell)

            if path in seen_routes:
                repeated_routes += 1
            else:
                seen_routes.add(path)

        d_stats = _calc_stats(dwells)
        nav_rate = count / session_duration_sec if session_duration_sec > 0 else 0.0

        return {
            "navigation_count": float(count),
            "unique_route_count": float(len(seen_routes)),
            "mean_page_dwell_ms": d_stats["mean"],
            "std_page_dwell_ms": d_stats["std"],
            "min_page_dwell_ms": d_stats["min"],
            "max_page_dwell_ms": d_stats["max"],
            "navigation_rate": _safe_float(nav_rate),
            "repeated_route_count": float(repeated_routes),
            "route_repetition_ratio": _safe_float(repeated_routes / count),
        }

    @classmethod
    def _extract_visibility_features(cls, events: List[Dict[str, Any]], session_duration_ms: float) -> Dict[str, float]:
        count = len(events)
        if count == 0:
            return {
                "visibility_event_count": 0.0,
                "hidden_event_count": 0.0,
                "focus_event_count": 0.0,
                "blur_event_count": 0.0,
                "total_time_away_ms": 0.0,
                "mean_time_away_ms": 0.0,
                "max_time_away_ms": 0.0,
                "time_away_ratio": 0.0,
            }

        hidden_count = 0
        focus_count = 0
        blur_count = 0
        times_away = []

        for ev in events:
            data = ev.get("event_data", {})
            state = str(data.get("state", "visible")).lower()
            away_ms = float(data.get("duration_away_ms", 0))

            if state == "hidden":
                hidden_count += 1
            elif state == "focus":
                focus_count += 1
            elif state == "blur":
                blur_count += 1

            if away_ms > 0:
                times_away.append(away_ms)

        t_stats = _calc_stats(times_away)
        total_away = sum(times_away)
        ratio = (total_away / session_duration_ms) if session_duration_ms > 0 else 0.0
        ratio = min(1.0, max(0.0, ratio))

        return {
            "visibility_event_count": float(count),
            "hidden_event_count": float(hidden_count),
            "focus_event_count": float(focus_count),
            "blur_event_count": float(blur_count),
            "total_time_away_ms": _safe_float(total_away),
            "mean_time_away_ms": t_stats["mean"],
            "max_time_away_ms": t_stats["max"],
            "time_away_ratio": _safe_float(ratio),
        }

    @classmethod
    def _extract_cross_session_features(
        cls,
        events: List[Dict[str, Any]],
        session_duration_ms: float,
        existing_features: Dict[str, float]
    ) -> Dict[str, float]:
        total_events = len(events)
        session_duration_sec = session_duration_ms / 1000.0 if session_duration_ms > 0 else 0.001
        events_per_sec = total_events / session_duration_sec

        mouse_count = existing_features.get("mouse_event_count", 0.0)
        click_count = existing_features.get("click_count", 0.0)
        nav_count = existing_features.get("navigation_count", 0.0)

        # Active interaction duration (time span covered by user physical movements)
        mouse_dur = existing_features.get("mouse_session_duration_ms", 0.0)
        active_duration = min(session_duration_ms, max(mouse_dur, total_events * 50.0))
        interaction_density = (total_events / (active_duration / 1000.0)) if active_duration > 0 else 0.0

        mouse_to_click = (mouse_count / click_count) if click_count > 0 else mouse_count
        click_to_nav = (click_count / nav_count) if nav_count > 0 else click_count
        nav_to_session = (nav_count / (session_duration_ms / 60000.0)) if session_duration_ms > 0 else 0.0

        return {
            "session_duration_ms": _safe_float(session_duration_ms),
            "total_behavior_event_count": float(total_events),
            "events_per_second": _safe_float(events_per_sec),
            "active_behavior_duration_ms": _safe_float(active_duration),
            "interaction_density": _safe_float(interaction_density),
            "mouse_to_click_ratio": _safe_float(mouse_to_click),
            "click_to_navigation_ratio": _safe_float(click_to_nav),
            "navigation_to_session_ratio": _safe_float(nav_to_session),
        }

    @classmethod
    def _get_default_feature_vector(cls) -> Dict[str, float]:
        return {col: 0.0 for col in FEATURE_COLUMNS}
