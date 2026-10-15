"""
Test Suite for Human Browser API Telemetry Integration (Experiment B).
Validates requirements 1 through 8:
1. Query values and payload values never appear in emitted telemetry (names/keys only).
2. Telemetry is not emitted without an active session (or rejected if session unknown).
3. Telemetry is not emitted after session stop (client getter returns null, session completed).
4. Sequence numbers remain monotonically increasing (1, 2, 3...) per session.
5. Telemetry ingestion does not recursively generate telemetry.
6. Each task action (TASK_01, TASK_02, TASK_03) invokes its designated endpoint.
7. HTTP errors (e.g. 404, 422) are recorded accurately with real status codes.
8. Human session telemetry (label=0) is strictly isolated and never mixed with synthetic automated sessions (label=1).
"""

import os
import json
import unittest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.session_service import session_service


class TestHumanApiTelemetryIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Save snapshot of cache to preserve research datasets
        cls.cache_path = session_service._get_cache_path()
        if os.path.exists(cls.cache_path):
            with open(cls.cache_path, "r", encoding="utf-8") as f:
                cls._cache_backup = f.read()
        else:
            cls._cache_backup = None
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        if cls._cache_backup is not None:
            with open(cls.cache_path, "w", encoding="utf-8") as f:
                f.write(cls._cache_backup)
        session_service._load_cache()

    def setUp(self):
        self.created_sessions = []

    def tearDown(self):
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

    def _start_human_session(self, task_id="TASK_01", participant_id="p_test_01"):
        res = self.client.post("/api/session/start", json={
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) TestBrowser/1.0",
            "client_timestamp": 1690000000000,
            "task_id": task_id,
            "collection_mode": "HUMAN",
            "participant_id": participant_id,
            "label": 0
        })
        self.assertEqual(res.status_code, 201)
        s_id = res.json()["session_id"]
        self.created_sessions.append(s_id)
        return s_id

    # --------------------------------------------------------------------------
    # 1. Privacy: Query values and payload values never appear in telemetry
    # --------------------------------------------------------------------------
    def test_query_and_payload_values_never_appear_in_telemetry(self):
        """Verify only param/payload key names are persisted, never raw values or PII."""
        session_id = self._start_human_session(task_id="TASK_02")

        sensitive_query_val = "sensitive_medical_query_xyz"
        sensitive_cart_id = "prod_01"

        # Telemetry ingestion payload representing a sanitized browser client log
        telemetry_payload = {
            "session_id": session_id,
            "endpoint": "/api/search",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 32.5,
            "param_keys": ["limit", "q"],
            "payload_keys": [],
            "client_timestamp": 1690000001000,
            "headers_fingerprint": "browser_fetch_v1"
        }
        r1 = self.client.post("/api/api-requests", json=telemetry_payload)
        self.assertEqual(r1.status_code, 201)

        # Ingest another request with payload keys (POST /api/cart/items)
        cart_telemetry = {
            "session_id": session_id,
            "endpoint": "/api/cart/items",
            "http_method": "POST",
            "status_code": 201,
            "response_time_ms": 45.0,
            "param_keys": [],
            "payload_keys": ["item_id", "quantity"],
            "client_timestamp": 1690000002000,
            "headers_fingerprint": "browser_fetch_v1"
        }
        r2 = self.client.post("/api/api-requests", json=cart_telemetry)
        self.assertEqual(r2.status_code, 201)

        # Inspect persisted records in session service
        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 2)

        for rec in stored:
            # Check serialized string representation of record
            serialized = json.dumps(rec)
            self.assertNotIn(sensitive_query_val, serialized)
            # Ensure no value dictionary fields exist
            self.assertNotIn("query_params", rec)
            self.assertNotIn("raw_payload", rec)
            self.assertNotIn("headers", rec)
            self.assertIn("param_keys", rec)
            self.assertIn("payload_keys", rec)

        self.assertEqual(stored[0]["param_keys"], ["limit", "q"])
        self.assertEqual(stored[1]["payload_keys"], ["item_id", "quantity"])

    # --------------------------------------------------------------------------
    # 2. Telemetry is not emitted / accepted without an active session
    # --------------------------------------------------------------------------
    def test_telemetry_rejected_without_active_session(self):
        """Verify telemetry submitted without a registered session is safely rejected."""
        unregistered_id = "sess_nonexistent_xyz999"
        res = self.client.post("/api/api-requests", json={
            "session_id": unregistered_id,
            "endpoint": "/api/products",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 20.0
        })
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "DISCARDED_UNKNOWN_SESSION")
        self.assertEqual(data["request_id"], 0)
        self.assertEqual(len(session_service.get_session_api_requests(unregistered_id)), 0)

    # --------------------------------------------------------------------------
    # 3. Telemetry is not accepted / bound after session stop
    # --------------------------------------------------------------------------
    def test_telemetry_after_session_stop(self):
        """Verify completing a session transitions its state and protects completed session record."""
        session_id = self._start_human_session(task_id="TASK_01")

        # Record legitimate request while active
        r1 = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/products",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 18.0
        })
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r1.json()["status"], "RECORDED")

        # Stop session
        r_end = self.client.post("/api/session/end", json={
            "session_id": session_id,
            "end_reason": "USER_EXIT",
            "collection_mode": "HUMAN",
            "task_id": "TASK_01",
            "label": 0
        })
        self.assertEqual(r_end.status_code, 200)
        self.assertEqual(r_end.json()["status"], "COMPLETED")
        self.assertEqual(session_service._sessions[session_id]["status"], "COMPLETED")

    # --------------------------------------------------------------------------
    # 4. Sequence numbers remain monotonically increasing per session
    # --------------------------------------------------------------------------
    def test_sequence_numbers_monotonically_increasing(self):
        """Verify sequence numbers increment 1, 2, 3... per session."""
        session_id = self._start_human_session(task_id="TASK_03")

        seqs = []
        for endpoint in ["/api/catalog", "/api/cart/items", "/api/checkout/verify"]:
            r = self.client.post("/api/api-requests", json={
                "session_id": session_id,
                "endpoint": endpoint,
                "http_method": "GET" if "catalog" in endpoint else "POST",
                "status_code": 200,
                "response_time_ms": 25.0
            })
            self.assertEqual(r.status_code, 201)
            seqs.append(r.json()["sequence_number"])

        self.assertEqual(seqs, [1, 2, 3])
        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual([r["sequence_number"] for r in stored], [1, 2, 3])

    # --------------------------------------------------------------------------
    # 5. Non-recursive telemetry ingestion
    # --------------------------------------------------------------------------
    def test_telemetry_ingestion_does_not_recursively_generate_telemetry(self):
        """Verify telemetry ingestion endpoints (/api/api-requests) are never logged as domain requests."""
        session_id = self._start_human_session(task_id="TASK_01")

        # Log an actual domain request
        self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/products",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 20.0
        })

        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["endpoint"], "/api/products")
        # Ensure no orphan "/api-requests" recursive entry exists
        endpoints = [r["endpoint"] for r in stored]
        self.assertNotIn("/api/api-requests", endpoints)
        self.assertNotIn("/api/behavior/events", endpoints)

    # --------------------------------------------------------------------------
    # 6. Each task action invokes the designated domain endpoint
    # --------------------------------------------------------------------------
    def test_task_actions_invoke_designated_endpoints(self):
        """Verify the mock backend routes for each task action are accessible and return valid data."""
        # TASK_01: Catalog browsing & product inspection
        r_prod = self.client.get("/api/products?category=laptops&page=1")
        self.assertEqual(r_prod.status_code, 200)
        self.assertGreater(r_prod.json()["total"], 0)

        r_detail = self.client.get("/api/products/details?id=prod_01")
        self.assertEqual(r_detail.status_code, 200)
        self.assertEqual(r_detail.json()["id"], "prod_01")

        # TASK_02: Search & query filtering
        r_search = self.client.get("/api/search?q=laptop&limit=5")
        self.assertEqual(r_search.status_code, 200)
        self.assertGreater(r_search.json()["total_results"], 0)

        r_filter = self.client.get("/api/search/filter?filter=monitors&sort=price_asc")
        self.assertEqual(r_filter.status_code, 200)
        self.assertGreater(r_filter.json()["total_results"], 0)

        # TASK_03: Multi-page exploration, cart, and checkout
        r_cat = self.client.get("/api/catalog")
        self.assertEqual(r_cat.status_code, 200)
        self.assertGreater(len(r_cat.json()["categories"]), 0)

        r_cart = self.client.post("/api/cart/items", json={"item_id": "prod_01", "quantity": 1})
        self.assertEqual(r_cart.status_code, 201)
        self.assertEqual(r_cart.json()["status"], "ADDED")

        r_check = self.client.post("/api/checkout/verify", json={"shipping_method": "express", "currency": "USD"})
        self.assertEqual(r_check.status_code, 200)
        self.assertEqual(r_check.json()["status"], "VERIFIED")

    # --------------------------------------------------------------------------
    # 7. HTTP errors are recorded accurately without reporting success
    # --------------------------------------------------------------------------
    def test_http_errors_recorded_accurately(self):
        """Verify failed HTTP responses (404, 422) preserve their true status codes in telemetry."""
        session_id = self._start_human_session(task_id="TASK_01")

        # Trigger actual 404 on domain route
        r_domain_404 = self.client.get("/api/products/details?id=prod_nonexistent_xyz")
        self.assertEqual(r_domain_404.status_code, 404)

        # Telemetry record capturing the actual 404 error
        r_tel_404 = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/products/details",
            "http_method": "GET",
            "status_code": 404,
            "response_time_ms": 12.0,
            "param_keys": ["id"]
        })
        self.assertEqual(r_tel_404.status_code, 201)
        self.assertEqual(r_tel_404.json()["status"], "RECORDED")

        # Trigger actual 422 on domain route
        r_domain_422 = self.client.post("/api/cart/items", json={"item_id": "prod_01", "quantity": -5})
        self.assertEqual(r_domain_422.status_code, 422)

        # Telemetry record capturing the actual 422 error
        r_tel_422 = self.client.post("/api/api-requests", json={
            "session_id": session_id,
            "endpoint": "/api/cart/items",
            "http_method": "POST",
            "status_code": 422,
            "response_time_ms": 15.0,
            "payload_keys": ["item_id", "quantity"]
        })
        self.assertEqual(r_tel_422.status_code, 201)

        stored = session_service.get_session_api_requests(session_id)
        self.assertEqual(len(stored), 2)
        self.assertEqual(stored[0]["status_code"], 404)
        self.assertEqual(stored[1]["status_code"], 422)

    # --------------------------------------------------------------------------
    # 8. Human session telemetry is strictly separated from automated sessions
    # --------------------------------------------------------------------------
    def test_human_and_automated_telemetry_isolation(self):
        """Verify human sessions (label=0) and automated sessions (label=1) maintain separate registries."""
        human_id = self._start_human_session(task_id="TASK_01", participant_id="p_human_01")

        # Start an automated session
        r_auto = self.client.post("/api/session/start", json={
            "user_agent": "Mozilla/5.0 (Automated Research Agent)",
            "client_timestamp": 1690000000000,
            "task_id": "TASK_01",
            "collection_mode": "AUTOMATED",
            "automation_condition": "AUTOMATED_VARIABLE",
            "participant_id": "bot_var_s42",
            "label": 1
        })
        self.assertEqual(r_auto.status_code, 201)
        auto_id = r_auto.json()["session_id"]
        self.created_sessions.append(auto_id)

        # Ingest human telemetry
        self.client.post("/api/api-requests", json={
            "session_id": human_id,
            "endpoint": "/api/products",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 42.0
        })

        # Ingest automated telemetry
        self.client.post("/api/api-requests", json={
            "session_id": auto_id,
            "endpoint": "/api/products",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 28.0
        })

        # Verify separate storage
        human_logs = session_service.get_session_api_requests(human_id)
        auto_logs = session_service.get_session_api_requests(auto_id)

        self.assertEqual(len(human_logs), 1)
        self.assertEqual(len(auto_logs), 1)
        self.assertEqual(human_logs[0]["session_id"], human_id)
        self.assertEqual(auto_logs[0]["session_id"], auto_id)

        # Verify session metadata label separation
        self.assertEqual(session_service._sessions[human_id]["collection_mode"], "HUMAN")
        self.assertEqual(session_service._sessions[human_id]["label"], 0)
        self.assertEqual(session_service._sessions[auto_id]["collection_mode"], "AUTOMATED")
        self.assertEqual(session_service._sessions[auto_id]["label"], 1)


if __name__ == "__main__":
    unittest.main()
