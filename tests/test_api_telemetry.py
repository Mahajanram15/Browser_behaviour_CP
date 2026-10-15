"""
Test Suite for API Telemetry Collection Pipeline (Experiment B Readiness).
Validates requirements A through M:
A. Valid API request is persisted.
B. API request receives a unique request ID.
C. Unknown session ID is rejected/discarded.
D. Sequence numbers are 1, 2, 3... monotonically increasing within a session.
E. Sequence numbers restart at 1 for a new session.
F. Query parameter VALUES are never persisted.
G. Query parameter NAMES are persisted.
H. JSON payload VALUES are never persisted.
I. JSON payload field NAMES are persisted.
J. client_timestamp is stored alongside server timestamp.
K. response_size_bytes is stored when available.
L. Existing API request contract is preserved.
M. Existing browser telemetry behavior is unaffected.
Additional:
- Concurrency safety: No duplicate sequence numbers under concurrent requests.
- Automated collector support: Can emit API telemetry when enabled, disabled by default.
"""

import os
import json
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.session_service import session_service
from ml.data_collection.automated_collector import AutomatedSessionGenerator, build_arg_parser


class TestApiTelemetryPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Save snapshot of active sessions cache to ensure test sessions do not alter research data
        cls.cache_path = session_service._get_cache_path()
        if os.path.exists(cls.cache_path):
            with open(cls.cache_path, "r", encoding="utf-8") as f:
                cls._cache_backup = f.read()
        else:
            cls._cache_backup = None
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        # Restore cache snapshot exactly
        if cls._cache_backup is not None:
            with open(cls.cache_path, "w", encoding="utf-8") as f:
                f.write(cls._cache_backup)
        session_service._load_cache()

    def setUp(self):
        self.created_sessions = []

    def tearDown(self):
        # Clean in-memory session service state created during individual tests
        for s_id in self.created_sessions:
            if s_id in session_service._sessions:
                del session_service._sessions[s_id]
            if s_id in session_service._events_count:
                del session_service._events_count[s_id]
            if s_id in session_service._events_by_session:
                del session_service._events_by_session[s_id]
            if s_id in session_service._api_requests:
                del session_service._api_requests[s_id]
            if s_id in session_service._api_requests_count:
                del session_service._api_requests_count[s_id]

    def _start_test_session(self, task_id="TASK_01", mode="AUTOMATED"):
        r = self.client.post("/api/session/start", json={
            "user_agent": "TestTelemetryAgent/1.0",
            "client_timestamp": 1690000000000,
            "task_id": task_id,
            "collection_mode": mode
        })
        self.assertEqual(r.status_code, 201)
        s_id = r.json()["session_id"]
        self.created_sessions.append(s_id)
        return s_id

    # --------------------------------------------------------------------------
    # Requirement A: Valid API request is persisted
    # --------------------------------------------------------------------------
    def test_a_valid_api_request_persisted(self):
        """Verify valid API telemetry requests are accepted and persisted in session registry."""
        session_id = self._start_test_session()

        payload = {
            "session_id": session_id,
            "endpoint": "/api/catalog/products",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 35.5,
            "request_size_bytes": 128,
            "response_size_bytes": 2048,
            "headers_fingerprint": "abc123hash",
            "client_timestamp": 1690000001000
        }
        res = self.client.post("/api/api-requests", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "RECORDED")
        self.assertEqual(data["session_id"], session_id)
        self.assertGreater(data["request_id"], 0)

        # Verify persisted record in session_service
        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 1)
        rec = stored[0]
        self.assertEqual(rec["endpoint"], "/api/catalog/products")
        self.assertEqual(rec["http_method"], "GET")
        self.assertEqual(rec["status_code"], 200)
        self.assertEqual(rec["response_time_ms"], 35.5)
        self.assertEqual(rec["request_size_bytes"], 128)
        self.assertEqual(rec["response_size_bytes"], 2048)

    # --------------------------------------------------------------------------
    # Requirement B: API request receives a unique request ID
    # --------------------------------------------------------------------------
    def test_b_unique_request_id(self):
        """Verify each persisted API telemetry request receives a unique global request ID."""
        session_id = self._start_test_session()

        r1 = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/endpoint_1",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 10.0
        })
        r2 = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/endpoint_2",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 12.0
        })

        id1 = r1.json()["request_id"]
        id2 = r2.json()["request_id"]
        self.assertGreater(id1, 0)
        self.assertGreater(id2, 0)
        self.assertNotEqual(id1, id2)
        self.assertGreater(id2, id1)

    # --------------------------------------------------------------------------
    # Requirement C: Unknown session ID is rejected/discarded
    # --------------------------------------------------------------------------
    def test_c_unknown_session_rejected_or_discarded(self):
        """Verify requests for nonexistent session IDs are safely discarded without orphan records."""
        unknown_id = "sess_nonexistent_xyz999"

        res = self.client.post("/api/api-requests", json={
            "session_id": unknown_id,
            "endpoint": "/api/orphan_test",
            "http_method": "POST",
            "status_code": 200,
            "response_time_ms": 15.0
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "DISCARDED_UNKNOWN_SESSION")
        self.assertEqual(data["request_id"], 0)
        self.assertEqual(data["sequence_number"], 0)

        # Verify zero records created in registry
        stored = session_service.get_session_api_requests(unknown_id)
        self.assertEqual(len(stored), 0)

    # --------------------------------------------------------------------------
    # Requirement D: Sequence numbers are 1, 2, 3... within a session
    # --------------------------------------------------------------------------
    def test_d_sequence_numbers_monotonic_within_session(self):
        """Verify sequence numbers increment strictly 1, 2, 3, 4, 5 for consecutive requests."""
        session_id = self._start_test_session()

        for expected_seq in range(1, 6):
            res = self.client.post("/api/api-requests", json={
                "session_id": session_id,
                "endpoint": f"/api/step_{expected_seq}",
                "http_method": "GET",
                "status_code": 200,
                "response_time_ms": 10.0 + expected_seq
            })
            self.assertEqual(res.status_code, 201)
            data = res.json()
            self.assertEqual(data["sequence_number"], expected_seq)

        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 5)
        for i, rec in enumerate(stored, start=1):
            self.assertEqual(rec["sequence_number"], i)

    # --------------------------------------------------------------------------
    # Requirement E: Sequence numbers restart at 1 for a new session
    # --------------------------------------------------------------------------
    def test_e_sequence_numbers_restart_for_new_session(self):
        """Verify sequence counter resets to 1 when a new session begins."""
        sess_1 = self._start_test_session(task_id="TASK_01")
        sess_2 = self._start_test_session(task_id="TASK_02")

        # Session 1: 3 requests
        for i in range(1, 4):
            r = self.client.post("/api/api-requests", json={
                "session_id": sess_1,
                "endpoint": f"/api/sess1/req_{i}",
                "http_method": "GET",
                "status_code": 200,
                "response_time_ms": 10.0
            })
            self.assertEqual(r.json()["sequence_number"], i)

        # Session 2: first request must restart at 1
        r_s2_1 = self.client.post("/api/api-requests", json={
            "session_id": sess_2,
            "endpoint": "/api/sess2/req_1",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 10.0
        })
        self.assertEqual(r_s2_1.json()["sequence_number"], 1)

        # Session 2: second request must be 2
        r_s2_2 = self.client.post("/api/api-requests", json={
            "session_id": sess_2,
            "endpoint": "/api/sess2/req_2",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 10.0
        })
        self.assertEqual(r_s2_2.json()["sequence_number"], 2)

        # Verify counts in session_service
        self.assertEqual(session_service.get_api_requests_count(sess_1), 3)
        self.assertEqual(session_service.get_api_requests_count(sess_2), 2)

    # --------------------------------------------------------------------------
    # Requirement F: Query parameter VALUES are never persisted
    # --------------------------------------------------------------------------
    def test_f_query_param_values_never_persisted(self):
        """Verify sensitive query parameter values are completely purged and never saved."""
        session_id = self._start_test_session()

        sensitive_query = "q=super_secret_password_987&apiKey=sk_live_token_secret_456"
        res = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": f"/api/search?{sensitive_query}",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 20.0,
            "query_params": {
                "user_ssn": "000-11-2222",
                "auth_bearer": "secret_jwt_token_here"
            }
        })
        self.assertEqual(res.status_code, 201)

        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 1)
        record_json_str = json.dumps(stored[0])

        # Assert no sensitive values leaked into stored record
        self.assertNotIn("super_secret_password_987", record_json_str)
        self.assertNotIn("sk_live_token_secret_456", record_json_str)
        self.assertNotIn("000-11-2222", record_json_str)
        self.assertNotIn("secret_jwt_token_here", record_json_str)

        # Assert endpoint URL was sanitized to path only
        self.assertEqual(stored[0]["endpoint"], "/api/search")

    # --------------------------------------------------------------------------
    # Requirement G: Query parameter NAMES are persisted
    # --------------------------------------------------------------------------
    def test_g_query_param_names_persisted(self):
        """Verify query parameter keys are retained in param_keys."""
        session_id = self._start_test_session()

        res = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/products?category=laptops&page=2&sort=price",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 18.0
        })
        self.assertEqual(res.status_code, 201)

        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 1)
        param_keys = stored[0]["param_keys"]
        self.assertIn("category", param_keys)
        self.assertIn("page", param_keys)
        self.assertIn("sort", param_keys)
        self.assertEqual(len(param_keys), 3)

    # --------------------------------------------------------------------------
    # Requirement H: JSON payload VALUES are never persisted
    # --------------------------------------------------------------------------
    def test_h_json_payload_values_never_persisted(self):
        """Verify body values, passwords, credit card info, and PII are never saved."""
        session_id = self._start_test_session()

        res = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/users/login",
            "http_method": "POST",
            "status_code": 200,
            "response_time_ms": 40.0,
            "raw_payload": {
                "username": "secret_user_john",
                "password": "unhashed_super_secret_pass!",
                "credit_card": "4111-2222-3333-4444"
            }
        })
        self.assertEqual(res.status_code, 201)

        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 1)
        record_json_str = json.dumps(stored[0])

        self.assertNotIn("secret_user_john", record_json_str)
        self.assertNotIn("unhashed_super_secret_pass!", record_json_str)
        self.assertNotIn("4111-2222-3333-4444", record_json_str)
        self.assertNotIn("raw_payload", stored[0])

    # --------------------------------------------------------------------------
    # Requirement I: JSON payload field NAMES are persisted
    # --------------------------------------------------------------------------
    def test_i_json_payload_field_names_persisted(self):
        """Verify field names in JSON body are captured in payload_keys alongside structural hash."""
        session_id = self._start_test_session()

        res = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/cart/checkout",
            "http_method": "POST",
            "status_code": 201,
            "response_time_ms": 60.0,
            "raw_payload": {
                "cart_id": "c987",
                "items": [{"sku": "SKU1", "qty": 2}],
                "promo_code": "DISCOUNT10"
            }
        })
        self.assertEqual(res.status_code, 201)

        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 1)
        rec = stored[0]
        self.assertIn("cart_id", rec["payload_keys"])
        self.assertIn("items", rec["payload_keys"])
        self.assertIn("promo_code", rec["payload_keys"])
        self.assertIsNotNone(rec["payload_structure_hash"])
        self.assertEqual(len(rec["payload_structure_hash"]), 16)

    # --------------------------------------------------------------------------
    # Requirement J: client_timestamp is stored
    # --------------------------------------------------------------------------
    def test_j_client_timestamp_stored(self):
        """Verify browser client_timestamp and server timestamp are both preserved."""
        session_id = self._start_test_session()

        client_ts = 1718000555123
        res = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/metrics",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 15.0,
            "client_timestamp": client_ts
        })
        self.assertEqual(res.status_code, 201)

        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 1)
        rec = stored[0]
        self.assertEqual(rec["client_timestamp"], client_ts)
        self.assertIn("timestamp", rec)
        self.assertIn("server_timestamp", rec)
        self.assertGreater(rec["server_timestamp"], 0)

    # --------------------------------------------------------------------------
    # Requirement K: response_size_bytes is stored when available
    # --------------------------------------------------------------------------
    def test_k_response_size_bytes_stored_when_available(self):
        """Verify response_size_bytes integer is recorded when supplied."""
        session_id = self._start_test_session()

        # Case 1: Size explicitly provided
        res1 = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/download",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 120.0,
            "response_size_bytes": 1048576
        })
        self.assertEqual(res1.status_code, 201)

        # Case 2: Size omitted (defaults safely to 0)
        res2 = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/ping",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 5.0
        })
        self.assertEqual(res2.status_code, 201)

        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 2)
        self.assertEqual(stored[0]["response_size_bytes"], 1048576)
        self.assertEqual(stored[1]["response_size_bytes"], 0)

    # --------------------------------------------------------------------------
    # Requirement L: Existing API request contract is preserved
    # --------------------------------------------------------------------------
    def test_l_existing_api_contract_preserved(self):
        """Verify backward compatibility of API contract for legacy callers omitting new fields."""
        session_id = self._start_test_session()

        legacy_payload = {
            "session_id": session_id,
            "endpoint": "/api/legacy-check",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 14.5
        }
        res = self.client.post("/api/api-requests", json=legacy_payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertIn("request_id", data)
        self.assertIn("session_id", data)
        self.assertIn("status", data)
        self.assertEqual(data["status"], "RECORDED")
        self.assertEqual(data["sequence_number"], 1)

    # --------------------------------------------------------------------------
    # Requirement M: Existing browser telemetry behavior is unaffected
    # --------------------------------------------------------------------------
    def test_m_existing_browser_telemetry_unaffected(self):
        """Verify browser behavioral event ingestion and session lifecycle continue operating normally."""
        session_id = self._start_test_session()

        # Ingest behavioral events
        event_batch = {
            "session_id": session_id,
            "events": [
                {
                    "event_type": "mouse_move",
                    "client_timestamp": 1690000001000,
                    "event_data": {"x": 100, "y": 200, "distance_px": 15, "velocity_px_s": 300}
                },
                {
                    "event_type": "mouse_click",
                    "client_timestamp": 1690000001400,
                    "event_data": {"x": 100, "y": 200, "button": 0}
                }
            ]
        }
        res_events = self.client.post("/api/behavior/events", json=event_batch)
        self.assertEqual(res_events.status_code, 202)
        self.assertEqual(res_events.json()["processed_events"], 2)
        self.assertEqual(res_events.json()["status"], "INGESTED")

        # Interleaved API request
        res_api = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/action",
            "http_method": "POST",
            "status_code": 200,
            "response_time_ms": 25.0
        })
        self.assertEqual(res_api.status_code, 201)

        # End session
        res_end = self.client.post("/api/session/end", json={
            "session_id": session_id,
            "end_reason": "TEST_COMPLETED"
        })
        self.assertEqual(res_end.status_code, 200)
        self.assertEqual(res_end.json()["status"], "COMPLETED")

        # Verify events and API requests are properly partitioned in session_service
        self.assertEqual(len(session_service.get_session_events(session_id)), 2)
        self.assertEqual(len(session_service.get_session_api_requests(session_id)), 1)

    # --------------------------------------------------------------------------
    # Concurrency Safety: Thread-safe monotonic sequence numbering
    # --------------------------------------------------------------------------
    def test_concurrent_requests_sequence_uniqueness(self):
        """Verify concurrent requests within the same session receive unique, consecutive sequence numbers."""
        session_id = self._start_test_session()
        num_requests = 20
        sequence_numbers = []
        lock = threading.Lock()

        def send_request(idx):
            res = self.client.post("/api/api-requests", json={
                "session_id": session_id,
                "endpoint": f"/api/concurrent_{idx}",
                "http_method": "GET",
                "status_code": 200,
                "response_time_ms": 10.0
            })
            seq = res.json()["sequence_number"]
            with lock:
                sequence_numbers.append(seq)

        with ThreadPoolExecutor(max_workers=5) as executor:
            list(executor.map(send_request, range(num_requests)))

        self.assertEqual(len(sequence_numbers), num_requests)
        self.assertEqual(len(set(sequence_numbers)), num_requests, "Duplicate sequence numbers detected!")
        self.assertEqual(sorted(sequence_numbers), list(range(1, num_requests + 1)))

    # --------------------------------------------------------------------------
    # Automated Collector Support & Telemetry Emission Flags
    # --------------------------------------------------------------------------
    def test_collector_api_telemetry_disabled_by_default(self):
        """Verify API telemetry emission is strictly disabled by default in CLI parser and run method."""
        # 1. Verify CLI argument parser defaults
        parser = build_arg_parser()
        args_empty = parser.parse_args([])
        self.assertFalse(args_empty.emit_api_telemetry)

        args_task = parser.parse_args(["--task", "TASK_02", "--condition", "AUTOMATED_VARIABLE"])
        self.assertFalse(args_task.emit_api_telemetry)

        # 2. Verify run_session_via_api without emit_api_telemetry (omitted/default) emits 0 API requests
        collector = AutomatedSessionGenerator()
        res = collector.run_session_via_api(
            task_id="TASK_01",
            condition="AUTOMATED_DETERMINISTIC",
            seed=42,
            client=self.client
        )
        self.created_sessions.append(res["session_id"])
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["api_requests_count"], 0)
        self.assertEqual(len(session_service.get_session_api_requests(res["session_id"])), 0)

    def test_collector_api_telemetry_enabled_with_flag(self):
        """Verify supplying --emit-api-telemetry enables telemetry in CLI and collector."""
        # 1. Verify CLI argument parser recognizes flag
        parser = build_arg_parser()
        args = parser.parse_args(["--emit-api-telemetry"])
        self.assertTrue(args.emit_api_telemetry)

        args_combined = parser.parse_args(["--task", "TASK_03", "--emit-api-telemetry", "--n-sessions", "2"])
        self.assertTrue(args_combined.emit_api_telemetry)

        # 2. Verify run_session_via_api with emit_api_telemetry=True generates and persists API requests
        collector = AutomatedSessionGenerator()
        res = collector.run_session_via_api(
            task_id="TASK_03",
            condition="AUTOMATED_DETERMINISTIC",
            seed=42,
            client=self.client,
            emit_api_telemetry=True
        )
        self.created_sessions.append(res["session_id"])
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["api_requests_count"], 3)  # TASK_03 generates 3 API requests

        stored = session_service.get_session_api_requests(res["session_id"])
        self.assertEqual(len(stored), 3)
        self.assertEqual([r["sequence_number"] for r in stored], [1, 2, 3])

    def test_existing_collector_commands_work_as_before(self):
        """Verify legacy CLI collector commands without the new flag function identically."""
        parser = build_arg_parser()
        legacy_args = parser.parse_args([
            "--task", "TASK_02",
            "--condition", "AUTOMATED_VARIABLE",
            "--seed", "123",
            "--participant-id", "bot_legacy_01",
            "--n-sessions", "1"
        ])
        self.assertEqual(legacy_args.task, "TASK_02")
        self.assertEqual(legacy_args.condition, "AUTOMATED_VARIABLE")
        self.assertEqual(legacy_args.seed, 123)
        self.assertEqual(legacy_args.participant_id, "bot_legacy_01")
        self.assertFalse(legacy_args.emit_api_telemetry)

        collector = AutomatedSessionGenerator()
        res = collector.run_session_via_api(
            task_id=legacy_args.task,
            condition=legacy_args.condition,
            seed=legacy_args.seed,
            participant_id=legacy_args.participant_id,
            client=self.client
        )
        self.created_sessions.append(res["session_id"])
        self.assertEqual(res["task_id"], "TASK_02")
        self.assertEqual(res["automation_condition"], "AUTOMATED_VARIABLE")
        self.assertEqual(res["participant_id"], "bot_legacy_01")
        self.assertEqual(res["label"], 1)
        self.assertGreater(res["events_count"], 0)
        self.assertEqual(res["api_requests_count"], 0)
        self.assertEqual(res["status"], "COMPLETED")

    def test_telemetry_not_emitted_for_invalid_or_uncreated_session(self):
        """Verify API telemetry is never emitted if session creation fails or returns invalid ID."""
        collector = AutomatedSessionGenerator()

        # Mock client where session start fails or returns empty session_id
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"session_id": ""}
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response
        mock_client.base_url = "http://testserver"

        with self.assertRaises(ValueError) as ctx:
            collector.run_session_via_api(
                task_id="TASK_01",
                client=mock_client,
                emit_api_telemetry=True
            )
        self.assertIn("invalid session_id", str(ctx.exception).lower())

        # Verify no calls were made to /api-requests
        for call_item in mock_client.post.call_args_list:
            endpoint_arg = call_item[0][0]
            self.assertNotIn("api-requests", endpoint_arg)

    def test_telemetry_failures_reported_clearly(self):
        """Verify API telemetry emission errors raise clear descriptive exceptions and never fail silently."""
        collector = AutomatedSessionGenerator()

        # Case A: Endpoint returns an HTTP failure on API request
        mock_client_http_err = MagicMock()
        mock_client_http_err.base_url = "http://testserver"

        def mock_post_side_effect(endpoint, **kwargs):
            resp = MagicMock()
            if "/session/start" in endpoint:
                resp.json.return_value = {"session_id": "sess_test_fail_01"}
                resp.raise_for_status.return_value = None
                return resp
            elif "/behavior/events" in endpoint:
                resp.json.return_value = {"status": "INGESTED"}
                resp.raise_for_status.return_value = None
                return resp
            elif "/api-requests" in endpoint:
                raise RuntimeError("Network timeout connecting to gateway")
            elif "/session/end" in endpoint:
                resp.json.return_value = {"status": "COMPLETED"}
                resp.raise_for_status.return_value = None
                return resp
            return resp

        mock_client_http_err.post.side_effect = mock_post_side_effect

        with self.assertRaises(RuntimeError) as ctx_a:
            collector.run_session_via_api(
                task_id="TASK_01",
                client=mock_client_http_err,
                emit_api_telemetry=True
            )
        self.assertIn("API telemetry emission failed", str(ctx_a.exception))
        self.assertIn("sess_test_fail_01", str(ctx_a.exception))

        # Case B: Endpoint returns rejected status (e.g. DISCARDED_UNKNOWN_SESSION)
        mock_client_reject = MagicMock()
        mock_client_reject.base_url = "http://testserver"

        def mock_reject_side_effect(endpoint, **kwargs):
            resp = MagicMock()
            if "/session/start" in endpoint:
                resp.json.return_value = {"session_id": "sess_test_fail_02"}
                resp.raise_for_status.return_value = None
                return resp
            elif "/behavior/events" in endpoint:
                resp.json.return_value = {"status": "INGESTED"}
                resp.raise_for_status.return_value = None
                return resp
            elif "/api-requests" in endpoint:
                resp.json.return_value = {"status": "DISCARDED_UNKNOWN_SESSION", "request_id": 0}
                resp.raise_for_status.return_value = None
                return resp
            elif "/session/end" in endpoint:
                resp.json.return_value = {"status": "COMPLETED"}
                resp.raise_for_status.return_value = None
                return resp
            return resp

        mock_client_reject.post.side_effect = mock_reject_side_effect

        with self.assertRaises(RuntimeError) as ctx_b:
            collector.run_session_via_api(
                task_id="TASK_01",
                client=mock_client_reject,
                emit_api_telemetry=True
            )
        self.assertIn("rejected with status: 'DISCARDED_UNKNOWN_SESSION'", str(ctx_b.exception))


if __name__ == "__main__":
    unittest.main()
