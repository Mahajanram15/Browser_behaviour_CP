"""
Automated Telemetry Collection Harness.
Generates controlled, deterministic automated behavioral sessions matching predefined research tasks.
Outputs: collection_mode = 'AUTOMATED', label = 1.
"""

import math
import random
import time
import argparse
from typing import List, Dict, Any, Optional
import httpx

from ml.data_collection.tasks import get_task, get_all_task_ids


class AutomatedSessionGenerator:
    """
    Simulates programmatic automation across defined research tasks.
    Supports two controlled conditions:
    1. AUTOMATED_DETERMINISTIC: Baseline rigid automation (constant velocity, straight line, fixed keystroke/scroll timing).
    2. AUTOMATED_VARIABLE: Intermediate challenge automation with bounded, reproducible kinematic variations.
    """

    def __init__(self, api_base_url: str = "http://localhost:8000/api"):
        self.api_base_url = api_base_url.rstrip("/")

    def generate_task_events(
        self,
        task_id: str,
        base_time_ms: Optional[int] = None,
        condition: str = "AUTOMATED_DETERMINISTIC",
        seed: int = 42
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes behavioral telemetry for a specified task under the requested automation condition.
        """
        norm_cond = condition.upper()
        if norm_cond in ("AUTOMATED_VARIABLE", "VARIABLE"):
            return self._generate_variable_task_events(task_id, base_time_ms=base_time_ms, seed=seed)
        return self._generate_deterministic_task_events(task_id, base_time_ms=base_time_ms)

    def _generate_deterministic_task_events(
        self,
        task_id: str,
        base_time_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Original deterministic automation baseline: perfectly uniform velocities, straight line, fixed timings.
        """
        task = get_task(task_id)
        t = base_time_ms if base_time_ms is not None else int(time.time() * 1000)
        events: List[Dict[str, Any]] = []

        # 1. Initial Landing Navigation
        events.append({
            "event_type": "navigation",
            "client_timestamp": t,
            "event_data": {
                "path": task.target_routes[0] if task.target_routes else "/demo/landing",
                "referrer": "/",
                "dwell_time_ms": 0,
                "sequence_number": 1
            }
        })
        t += 350

        # 2. Linear Programmatic Mouse Movement (Constant velocity, 0 jitter, straight line)
        start_x, start_y = 120, 150
        target_x, target_y = 480, 520
        steps = 15
        dx = (target_x - start_x) / steps
        dy = (target_y - start_y) / steps

        curr_x, curr_y = start_x, start_y
        for i in range(steps):
            curr_x += dx
            curr_y += dy
            t += 33  # Strict 30Hz timing
            events.append({
                "event_type": "mouse_move",
                "client_timestamp": t,
                "event_data": {
                    "x": round(curr_x),
                    "y": round(curr_y),
                    "distance_px": round((dx**2 + dy**2)**0.5, 2),
                    "time_delta_ms": 33,
                    "velocity_px_s": 500.0,
                    "acceleration_px_s2": 0.0,
                    "angle_degrees": 45.0,
                    "direction_change_deg": 0.0
                }
            })

        t += 50

        # 3. Automated Click Event
        events.append({
            "event_type": "mouse_click",
            "client_timestamp": t,
            "event_data": {
                "x": round(curr_x),
                "y": round(curr_y),
                "button": 0,
                "click_type": "single",
                "time_since_last_click_ms": 500,
                "target_category": "button" if "01" in task_id else "input"
            }
        })

        t += 150

        # 4. Task-Specific Actions
        if task_id == "TASK_02" or task_id == "TASK_03":
            # Automated Typing: Uniform 50ms hold, 70ms flight (robotic cadence)
            num_keys = 8
            for k in range(num_keys):
                t += 70  # Fixed flight time
                events.append({
                    "event_type": "key_meta",
                    "client_timestamp": t,
                    "event_data": {
                        "dwell_ms": 50,  # Fixed dwell duration
                        "flight_ms": 70,
                        "inter_key_interval_ms": 120,
                        "is_backspace": False,
                        "is_paste": False
                    }
                })

        # 5. Programmatic Scrolling (Uniform chunks, fixed 100ms intervals)
        scroll_steps = 4
        for s in range(scroll_steps):
            t += 100
            events.append({
                "event_type": "scroll",
                "client_timestamp": t,
                "event_data": {
                    "scroll_x": 0,
                    "scroll_y": (s + 1) * 120,
                    "delta_x": 0,
                    "delta_y": 120,
                    "velocity_px_s": 1200.0,
                    "direction": "down",
                    "time_since_last_scroll_ms": 100
                }
            })

        t += 200

        # 6. Secondary Route Navigation
        if len(task.target_routes) > 1:
            events.append({
                "event_type": "navigation",
                "client_timestamp": t,
                "event_data": {
                    "path": task.target_routes[1],
                    "referrer": task.target_routes[0],
                    "dwell_time_ms": 1200,
                    "sequence_number": 2
                }
            })

        t += 100

        # 7. Visibility Confirmation
        events.append({
            "event_type": "visibility",
            "client_timestamp": t,
            "event_data": {
                "state": "visible",
                "duration_away_ms": 0
            }
        })

        return events

    def _generate_variable_task_events(
        self,
        task_id: str,
        base_time_ms: Optional[int] = None,
        seed: int = 42
    ) -> List[Dict[str, Any]]:
        """
        Intermediate challenge automation condition: bounded, reproducible variation in
        velocity, acceleration, trajectory curvature, inter-key timing, and scroll dynamics.
        Deterministic given the specified seed.
        """
        rng = random.Random(seed)
        task = get_task(task_id)
        t = base_time_ms if base_time_ms is not None else int(time.time() * 1000)
        events: List[Dict[str, Any]] = []

        # 1. Initial Landing Navigation (small dwell variation)
        nav_dwell = rng.randint(280, 420)
        events.append({
            "event_type": "navigation",
            "client_timestamp": t,
            "event_data": {
                "path": task.target_routes[0] if task.target_routes else "/demo/landing",
                "referrer": "/",
                "dwell_time_ms": 0,
                "sequence_number": 1
            }
        })
        t += nav_dwell

        # 2. Curved Trajectory Mouse Movement with Bounded Kinematic Variation
        # Uses a parametric quadratic Bézier curve to introduce controlled trajectory curvature
        start_x, start_y = 120.0, 150.0
        target_x, target_y = 480.0, 520.0

        # Midpoint with perpendicular offset for controlled curvature
        mid_x = (start_x + target_x) / 2.0
        mid_y = (start_y + target_y) / 2.0
        dist_total = math.hypot(target_x - start_x, target_y - start_y)
        # Normal vector perpendicular to trajectory
        norm_x = -(target_y - start_y) / dist_total
        norm_y = (target_x - start_x) / dist_total
        curve_offset = rng.uniform(25.0, 45.0) * (1 if rng.random() > 0.5 else -1)
        ctrl_x = mid_x + norm_x * curve_offset
        ctrl_y = mid_y + norm_y * curve_offset

        steps = rng.randint(16, 20)
        prev_x, prev_y = start_x, start_y
        prev_velocity = 200.0
        prev_angle = math.degrees(math.atan2(target_y - start_y, target_x - start_x))

        for step in range(1, steps + 1):
            u = step / float(steps)
            # Quadratic Bézier: B(u) = (1-u)^2 * P0 + 2(1-u)u * P1 + u^2 * P2
            curr_x = (1 - u)**2 * start_x + 2 * (1 - u) * u * ctrl_x + u**2 * target_x
            curr_y = (1 - u)**2 * start_y + 2 * (1 - u) * u * ctrl_y + u**2 * target_y

            # Step distance and timing
            step_dist = math.hypot(curr_x - prev_x, curr_y - prev_y)
            step_dt = rng.randint(28, 42)  # Bounded sampling jitter around ~33ms (24-35Hz)

            # Velocity follows bell-like profile with bounded perturbations
            # Peak speed in middle of movement, deceleration near target
            profile_mult = math.sin(u * math.pi) * 1.3 + 0.5  # Range ~0.5 to ~1.8
            curr_velocity = max(120.0, min(850.0, (step_dist / (step_dt / 1000.0)) * profile_mult))

            # Acceleration/deceleration
            accel = (curr_velocity - prev_velocity) / (step_dt / 1000.0)

            # Direction and curvature
            curr_angle = math.degrees(math.atan2(curr_y - prev_y, curr_x - prev_x)) if step_dist > 0.001 else prev_angle
            angle_diff = abs(curr_angle - prev_angle)
            if angle_diff > 180.0:
                angle_diff = 360.0 - angle_diff
            direction_change_deg = round(angle_diff, 2)

            t += step_dt
            events.append({
                "event_type": "mouse_move",
                "client_timestamp": t,
                "event_data": {
                    "x": round(curr_x),
                    "y": round(curr_y),
                    "distance_px": round(step_dist, 2),
                    "time_delta_ms": step_dt,
                    "velocity_px_s": round(curr_velocity, 2),
                    "acceleration_px_s2": round(accel, 2),
                    "angle_degrees": round(curr_angle, 2),
                    "direction_change_deg": direction_change_deg
                }
            })

            # Controlled micro-pause at mid-point
            if step == steps // 2:
                micro_pause = rng.randint(40, 75)
                t += micro_pause

            prev_x, prev_y = curr_x, curr_y
            prev_velocity = curr_velocity
            prev_angle = curr_angle

        # 3. Automated Click Event with Bounded Pre-Click Delay
        pre_click_delay = rng.randint(80, 160)
        t += pre_click_delay
        events.append({
            "event_type": "mouse_click",
            "client_timestamp": t,
            "event_data": {
                "x": round(prev_x),
                "y": round(prev_y),
                "button": 0,
                "click_type": "single",
                "time_since_last_click_ms": rng.randint(400, 650),
                "target_category": "button" if "01" in task_id else "input"
            }
        })

        t += rng.randint(120, 220)

        # 4. Task-Specific Actions with Bounded Typing Cadence
        if task_id in ("TASK_02", "TASK_03"):
            # Bounded keystroke variation around baseline (dwell ~42-68ms, flight ~55-95ms)
            # NEVER stores characters, keys, or passwords.
            num_keys = rng.randint(7, 10)
            for _ in range(num_keys):
                dwell = rng.randint(42, 68)
                flight = rng.randint(55, 95)
                inter_key = dwell + flight
                t += flight
                events.append({
                    "event_type": "key_meta",
                    "client_timestamp": t,
                    "event_data": {
                        "dwell_ms": dwell,
                        "flight_ms": flight,
                        "inter_key_interval_ms": inter_key,
                        "is_backspace": False,
                        "is_paste": False
                    }
                })

        # 5. Programmatic Scrolling with Bounded Distance & Interval Variation
        scroll_steps = rng.randint(3, 5)
        accum_y = 0
        for _ in range(scroll_steps):
            s_dt = rng.randint(80, 140)
            s_dist = rng.randint(90, 160)
            accum_y += s_dist
            s_vel = round(s_dist / (s_dt / 1000.0), 1)
            t += s_dt
            events.append({
                "event_type": "scroll",
                "client_timestamp": t,
                "event_data": {
                    "scroll_x": 0,
                    "scroll_y": accum_y,
                    "delta_x": 0,
                    "delta_y": s_dist,
                    "velocity_px_s": s_vel,
                    "direction": "down",
                    "time_since_last_scroll_ms": s_dt
                }
            })

        t += rng.randint(180, 280)

        # 6. Secondary Route Navigation
        if len(task.target_routes) > 1:
            route_dwell = rng.randint(1000, 1400)
            events.append({
                "event_type": "navigation",
                "client_timestamp": t,
                "event_data": {
                    "path": task.target_routes[1],
                    "referrer": task.target_routes[0],
                    "dwell_time_ms": route_dwell,
                    "sequence_number": 2
                }
            })

        t += rng.randint(80, 140)

        # 7. Visibility Confirmation
        events.append({
            "event_type": "visibility",
            "client_timestamp": t,
            "event_data": {
                "state": "visible",
                "duration_away_ms": 0
            }
        })

        return events

    def generate_task_api_requests(
        self,
        task_id: str,
        base_time_ms: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Synthesizes task-appropriate client API telemetry requests matching the browser workflow.
        PRIVACY: Never includes parameter values or raw payload bodies.
        """
        t = base_time_ms if base_time_ms is not None else int(time.time() * 1000)
        requests: List[Dict[str, Any]] = []

        if task_id == "TASK_01":
            # Catalog inspection API workflow
            requests.append({
                "endpoint": "/api/products",
                "http_method": "GET",
                "status_code": 200,
                "response_time_ms": 42.5,
                "request_size_bytes": 0,
                "response_size_bytes": 4120,
                "headers_fingerprint": "a1b2c3d4e5f60101",
                "client_timestamp": t + 350,
                "param_keys": ["category", "page"],
                "payload_keys": [],
            })
            requests.append({
                "endpoint": "/api/products/details",
                "http_method": "GET",
                "status_code": 200,
                "response_time_ms": 28.0,
                "request_size_bytes": 0,
                "response_size_bytes": 1850,
                "headers_fingerprint": "a1b2c3d4e5f60101",
                "client_timestamp": t + 1200,
                "param_keys": ["id"],
                "payload_keys": [],
            })
        elif task_id == "TASK_02":
            # Search & query filtering workflow
            requests.append({
                "endpoint": "/api/search",
                "http_method": "GET",
                "status_code": 200,
                "response_time_ms": 65.2,
                "request_size_bytes": 0,
                "response_size_bytes": 3150,
                "headers_fingerprint": "b2c3d4e5f6010202",
                "client_timestamp": t + 450,
                "param_keys": ["q", "limit"],
                "payload_keys": [],
            })
            requests.append({
                "endpoint": "/api/search/filter",
                "http_method": "GET",
                "status_code": 200,
                "response_time_ms": 31.4,
                "request_size_bytes": 0,
                "response_size_bytes": 1280,
                "headers_fingerprint": "b2c3d4e5f6010202",
                "client_timestamp": t + 1150,
                "param_keys": ["filter", "sort"],
                "payload_keys": [],
            })
        elif task_id == "TASK_03":
            # Multi-page exploration & checkout workflow
            requests.append({
                "endpoint": "/api/catalog",
                "http_method": "GET",
                "status_code": 200,
                "response_time_ms": 51.0,
                "request_size_bytes": 0,
                "response_size_bytes": 3950,
                "headers_fingerprint": "c3d4e5f601030303",
                "client_timestamp": t + 400,
                "param_keys": ["category"],
                "payload_keys": [],
            })
            requests.append({
                "endpoint": "/api/cart/items",
                "http_method": "POST",
                "status_code": 201,
                "response_time_ms": 78.5,
                "request_size_bytes": 84,
                "response_size_bytes": 512,
                "headers_fingerprint": "c3d4e5f601030303",
                "client_timestamp": t + 1300,
                "param_keys": [],
                "payload_keys": ["item_id", "quantity"],
            })
            requests.append({
                "endpoint": "/api/checkout/verify",
                "http_method": "POST",
                "status_code": 200,
                "response_time_ms": 105.8,
                "request_size_bytes": 120,
                "response_size_bytes": 860,
                "headers_fingerprint": "c3d4e5f601030303",
                "client_timestamp": t + 2200,
                "param_keys": [],
                "payload_keys": ["shipping_method", "currency"],
            })
        else:
            requests.append({
                "endpoint": "/api/general",
                "http_method": "GET",
                "status_code": 200,
                "response_time_ms": 25.0,
                "request_size_bytes": 0,
                "response_size_bytes": 500,
                "headers_fingerprint": "d4e5f60104040404",
                "client_timestamp": t + 300,
                "param_keys": [],
                "payload_keys": [],
            })

        return requests

    def run_session_via_api(
        self,
        task_id: str,
        condition: str = "AUTOMATED_DETERMINISTIC",
        seed: int = 42,
        participant_id: Optional[str] = None,
        client: Optional[httpx.Client] = None,
        emit_api_telemetry: bool = False
    ) -> Dict[str, Any]:
        """
        Executes an automated session against the FastAPI backend, binding:
        - collection_mode = 'AUTOMATED'
        - automation_condition = condition ('AUTOMATED_DETERMINISTIC' or 'AUTOMATED_VARIABLE')
        - participant_id = provenance identifier
        - label = 1
        - emit_api_telemetry = optional boolean to emit API request logs during session execution
        """
        should_close = False
        if client is None:
            client = httpx.Client(base_url=self.api_base_url, timeout=10.0)
            should_close = True

        norm_condition = "AUTOMATED_VARIABLE" if condition.upper() in ("AUTOMATED_VARIABLE", "VARIABLE") else "AUTOMATED_DETERMINISTIC"
        resolved_participant_id = participant_id or (f"bot_det" if norm_condition == "AUTOMATED_DETERMINISTIC" else f"bot_var_s{seed}")

        # Determine endpoint path prefix dynamically based on client base_url
        client_base = str(getattr(client, "base_url", "")).rstrip("/")
        prefix = "" if client_base.endswith("/api") else "/api"

        try:
            start_payload = {
                "user_agent": "Mozilla/5.0 (Automated Research Agent)",
                "screen_resolution": "1920x1080",
                "client_timezone": "UTC",
                "client_timestamp": int(time.time() * 1000),
                "collection_mode": "AUTOMATED",
                "automation_condition": norm_condition,
                "participant_id": resolved_participant_id,
                "task_id": task_id,
                "label": 1
            }

            # 1. Start Session
            r_start = client.post(f"{prefix}/session/start", json=start_payload)
            r_start.raise_for_status()
            session_data = r_start.json()
            session_id = session_data.get("session_id")
            if not session_id or not isinstance(session_id, str) or not session_id.startswith("sess_"):
                raise ValueError(f"Session initiation failed or returned invalid session_id: '{session_id}'")

            # 2. Ingest Events
            events = self.generate_task_events(task_id, condition=norm_condition, seed=seed)
            r_events = client.post(f"{prefix}/behavior/events", json={
                "session_id": session_id,
                "events": events
            })
            r_events.raise_for_status()

            # 2b. Optionally Ingest API Telemetry (Disabled by default until research collection)
            emitted_api_count = 0
            if emit_api_telemetry:
                api_requests = self.generate_task_api_requests(task_id, base_time_ms=start_payload["client_timestamp"])
                for idx, api_req in enumerate(api_requests, start=1):
                    req_payload = dict(api_req)
                    req_payload["session_id"] = session_id
                    try:
                        r_api = client.post(f"{prefix}/api-requests", json=req_payload)
                        r_api.raise_for_status()
                        api_res = r_api.json()
                        if api_res.get("status") != "RECORDED":
                            raise RuntimeError(
                                f"API request {idx}/{len(api_requests)} for session {session_id} rejected with status: '{api_res.get('status')}'"
                            )
                        emitted_api_count += 1
                    except Exception as e:
                        raise RuntimeError(
                            f"API telemetry emission failed on request {idx}/{len(api_requests)} ({api_req.get('endpoint')}) for session {session_id}: {e}"
                        ) from e

            # 3. End Session
            r_end = client.post(f"{prefix}/session/end", json={
                "session_id": session_id,
                "end_reason": f"{norm_condition}_TASK_COMPLETED",
                "collection_mode": "AUTOMATED",
                "automation_condition": norm_condition,
                "participant_id": resolved_participant_id,
                "task_id": task_id,
                "label": 1
            })
            r_end.raise_for_status()

            return {
                "session_id": session_id,
                "collection_mode": "AUTOMATED",
                "automation_condition": norm_condition,
                "participant_id": resolved_participant_id,
                "task_id": task_id,
                "label": 1,
                "events_count": len(events),
                "api_requests_count": emitted_api_count,
                "status": "COMPLETED"
            }
        finally:
            if should_close:
                client.close()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automated Telemetry Collection Harness")
    parser.add_argument("--task", default="TASK_01", choices=get_all_task_ids(), help="Task ID to execute")
    parser.add_argument("--condition", default="AUTOMATED_DETERMINISTIC",
                        choices=["AUTOMATED_DETERMINISTIC", "AUTOMATED_VARIABLE", "DETERMINISTIC", "VARIABLE"],
                        help="Automation condition: DETERMINISTIC baseline or VARIABLE challenge")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducible variable automation")
    parser.add_argument("--participant-id", default=None, help="Optional bot entity identifier for grouped evaluation")
    parser.add_argument("--n-sessions", type=int, default=1, help="Number of automated sessions to generate")
    parser.add_argument("--api-url", default="http://localhost:8000/api", help="FastAPI API base URL")
    parser.add_argument("--emit-api-telemetry", action="store_true", default=False,
                        help="Emit synthetic API request telemetry during session execution (default: False)")
    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()
    collector = AutomatedSessionGenerator(api_base_url=args.api_url)

    norm_cond = "AUTOMATED_VARIABLE" if args.condition.upper() in ("AUTOMATED_VARIABLE", "VARIABLE") else "AUTOMATED_DETERMINISTIC"
    telemetry_status = "ENABLED" if args.emit_api_telemetry else "DISABLED"
    print(f"Executing {args.n_sessions} {norm_cond} session(s) for {args.task} (seed={args.seed}, api_telemetry={telemetry_status})...")

    with httpx.Client(base_url=args.api_url, timeout=10.0) as client:
        for i in range(args.n_sessions):
            session_seed = args.seed + i
            res = collector.run_session_via_api(
                task_id=args.task,
                condition=norm_cond,
                seed=session_seed,
                participant_id=args.participant_id,
                client=client,
                emit_api_telemetry=args.emit_api_telemetry
            )
            api_info = f" | API Requests: {res['api_requests_count']}" if args.emit_api_telemetry else ""
            print(f"[{i+1}/{args.n_sessions}] Session {res['session_id']} | Task: {res['task_id']} | Condition: {res['automation_condition']} | Entity: {res['participant_id']} | Label: {res['label']} | Events: {res['events_count']}{api_info}")


if __name__ == "__main__":
    main()


