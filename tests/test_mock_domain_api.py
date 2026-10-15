"""
Test Suite for Mock Application Domain Endpoints (Experiment B Preparation).
Validates:
1. Each endpoint returns expected status codes and response structures.
2. Identical requests produce deterministic responses.
3. Unknown product IDs return 404 Not Found.
4. Invalid pagination, limits, quantities, and missing fields return 422 Unprocessable Entity.
5. Existing telemetry and session endpoints continue to function without regression.
6. Mock domain endpoints do not mutate session state, active cache, or research datasets.
"""

import os
import json
import unittest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.session_service import session_service
from backend.app.schemas.mock_domain import MOCK_PRODUCTS


class TestMockDomainApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Save snapshot of cache to ensure complete isolation
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

    # --------------------------------------------------------------------------
    # 1. Success Status Codes and Response Structure
    # --------------------------------------------------------------------------
    def test_products_endpoint_structure_and_success(self):
        """Verify GET /api/products returns paginated product list with expected schema."""
        res = self.client.get("/api/products")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("products", data)
        self.assertIn("total", data)
        self.assertIn("page", data)
        self.assertIn("page_size", data)
        self.assertEqual(data["page"], 1)
        self.assertGreater(data["total"], 0)
        self.assertGreater(len(data["products"]), 0)

        first = data["products"][0]
        self.assertIn("id", first)
        self.assertIn("name", first)
        self.assertIn("category", first)
        self.assertIn("price", first)
        self.assertIn("in_stock", first)

    def test_products_category_filter(self):
        """Verify GET /api/products?category=laptops filters items by category."""
        res = self.client.get("/api/products?category=laptops")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["category"], "laptops")
        for prod in data["products"]:
            self.assertEqual(prod["category"], "laptops")

    def test_product_details_endpoint_structure_and_success(self):
        """Verify GET /api/products/details?id=prod_01 returns full product specification."""
        res = self.client.get("/api/products/details?id=prod_01")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], "prod_01")
        self.assertIn("name", data)
        self.assertIn("category", data)
        self.assertIn("price", data)
        self.assertIn("specifications", data)
        self.assertIsInstance(data["specifications"], dict)
        self.assertTrue(len(data["specifications"]) > 0)

    def test_search_endpoint_structure_and_success(self):
        """Verify GET /api/search?q=laptop returns matched search results."""
        res = self.client.get("/api/search?q=laptop&limit=5")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["query"], "laptop")
        self.assertIn("results", data)
        self.assertIn("total_results", data)
        self.assertIn("limit", data)
        self.assertEqual(data["limit"], 5)
        self.assertGreater(data["total_results"], 0)

    def test_search_filter_endpoint_structure_and_success(self):
        """Verify GET /api/search/filter returns filtered and sorted results."""
        res = self.client.get("/api/search/filter?filter=monitors&sort=price_asc")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["filter"], "monitors")
        self.assertEqual(data["sort"], "price_asc")
        self.assertIn("results", data)
        prices = [p["price"] for p in data["results"]]
        self.assertEqual(prices, sorted(prices))

    def test_catalog_endpoint_structure_and_success(self):
        """Verify GET /api/catalog returns categories overview and featured products."""
        res = self.client.get("/api/catalog")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("categories", data)
        self.assertIn("featured_products", data)
        self.assertIn("total_catalog_items", data)
        self.assertGreater(len(data["categories"]), 0)
        self.assertGreater(len(data["featured_products"]), 0)

    def test_cart_items_endpoint_structure_and_success(self):
        """Verify POST /api/cart/items returns 201 Created and expected mutation payload."""
        payload = {"item_id": "prod_01", "quantity": 2}
        res = self.client.post("/api/cart/items", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["status"], "ADDED")
        self.assertEqual(data["item_id"], "prod_01")
        self.assertEqual(data["quantity"], 2)
        self.assertIn("message", data)

    def test_checkout_verify_endpoint_structure_and_success(self):
        """Verify POST /api/checkout/verify returns 200 OK and verification payload."""
        payload = {"shipping_method": "express", "currency": "USD"}
        res = self.client.post("/api/checkout/verify", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "VERIFIED")
        self.assertEqual(data["shipping_method"], "express")
        self.assertEqual(data["currency"], "USD")
        self.assertTrue(data["is_valid"])

    # --------------------------------------------------------------------------
    # 2. Determinism of Identical Requests
    # --------------------------------------------------------------------------
    def test_identical_requests_return_deterministic_results(self):
        """Verify that identical valid requests produce identical deterministic payloads."""
        # Test Products
        r1 = self.client.get("/api/products?category=laptops&page=1&page_size=2")
        r2 = self.client.get("/api/products?category=laptops&page=1&page_size=2")
        self.assertEqual(r1.json(), r2.json())

        # Test Search
        s1 = self.client.get("/api/search?q=quantum&limit=3")
        s2 = self.client.get("/api/search?q=quantum&limit=3")
        self.assertEqual(s1.json(), s2.json())

        # Test Catalog
        c1 = self.client.get("/api/catalog")
        c2 = self.client.get("/api/catalog")
        self.assertEqual(c1.json(), c2.json())

        # Test Filter
        f1 = self.client.get("/api/search/filter?filter=peripherals&sort=rating")
        f2 = self.client.get("/api/search/filter?filter=peripherals&sort=rating")
        self.assertEqual(f1.json(), f2.json())

    # --------------------------------------------------------------------------
    # 3. Unknown Product IDs Return 404
    # --------------------------------------------------------------------------
    def test_unknown_product_id_returns_404(self):
        """Verify unknown product ID in details returns 404."""
        res = self.client.get("/api/products/details?id=prod_nonexistent_xyz999")
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    def test_unknown_cart_item_id_returns_404(self):
        """Verify unknown product ID in cart addition returns 404."""
        res = self.client.post("/api/cart/items", json={
            "item_id": "prod_unknown_888",
            "quantity": 1
        })
        self.assertEqual(res.status_code, 404)
        self.assertIn("not found", res.json()["detail"].lower())

    # --------------------------------------------------------------------------
    # 4. Input Validation and Rejection (422)
    # --------------------------------------------------------------------------
    def test_invalid_pagination_page_rejected(self):
        """Verify page < 1 is rejected with 422."""
        res = self.client.get("/api/products?page=0")
        self.assertEqual(res.status_code, 422)

    def test_invalid_pagination_page_size_rejected(self):
        """Verify page_size > 50 is rejected with 422."""
        res = self.client.get("/api/products?page_size=100")
        self.assertEqual(res.status_code, 422)

    def test_missing_product_details_id_rejected(self):
        """Verify GET /api/products/details without id returns 422."""
        res = self.client.get("/api/products/details")
        self.assertEqual(res.status_code, 422)

    def test_missing_search_query_rejected(self):
        """Verify GET /api/search without q returns 422."""
        res = self.client.get("/api/search")
        self.assertEqual(res.status_code, 422)

    def test_invalid_search_limit_rejected(self):
        """Verify search limit < 1 or > 50 is rejected with 422."""
        res_zero = self.client.get("/api/search?q=laptop&limit=0")
        self.assertEqual(res_zero.status_code, 422)

        res_too_large = self.client.get("/api/search?q=laptop&limit=100")
        self.assertEqual(res_too_large.status_code, 422)

    def test_invalid_filter_sort_rejected(self):
        """Verify invalid sort option returns 422."""
        res = self.client.get("/api/search/filter?filter=laptops&sort=unsupported_sort_order")
        self.assertEqual(res.status_code, 422)
        self.assertIn("invalid sort parameter", res.json()["detail"].lower())

    def test_invalid_cart_quantity_rejected(self):
        """Verify quantity <= 0 is rejected with 422."""
        res_zero = self.client.post("/api/cart/items", json={"item_id": "prod_01", "quantity": 0})
        self.assertEqual(res_zero.status_code, 422)

        res_neg = self.client.post("/api/cart/items", json={"item_id": "prod_01", "quantity": -3})
        self.assertEqual(res_neg.status_code, 422)

    def test_missing_cart_fields_rejected(self):
        """Verify missing cart request fields return 422."""
        res = self.client.post("/api/cart/items", json={})
        self.assertEqual(res.status_code, 422)

    def test_invalid_checkout_shipping_method_rejected(self):
        """Verify unsupported shipping method is rejected with 422."""
        res = self.client.post("/api/checkout/verify", json={
            "shipping_method": "teleportation_express",
            "currency": "USD"
        })
        self.assertEqual(res.status_code, 422)
        self.assertIn("invalid shipping_method", res.json()["detail"].lower())

    def test_invalid_checkout_currency_rejected(self):
        """Verify unsupported or non-3-letter currency code is rejected with 422."""
        res_invalid_code = self.client.post("/api/checkout/verify", json={
            "shipping_method": "standard",
            "currency": "US"
        })
        self.assertEqual(res_invalid_code.status_code, 422)

        res_unsupported = self.client.post("/api/checkout/verify", json={
            "shipping_method": "standard",
            "currency": "XYZ"
        })
        self.assertEqual(res_unsupported.status_code, 422)

    # --------------------------------------------------------------------------
    # 5. Existing Telemetry & Session Lifecycle Unaffected
    # --------------------------------------------------------------------------
    def test_existing_session_lifecycle_unaffected(self):
        """Verify core session lifecycle and telemetry pipelines function normally alongside mock domain routes."""
        # 1. Start Session
        r_start = self.client.post("/api/session/start", json={
            "user_agent": "RegressionVerificationAgent/1.0",
            "client_timestamp": 1690000000000,
            "task_id": "TASK_01",
            "collection_mode": "HUMAN"
        })
        self.assertEqual(r_start.status_code, 201)
        s_id = r_start.json()["session_id"]
        self.created_sessions.append(s_id)

        # 2. Ingest Behavioral Events
        r_events = self.client.post("/api/behavior/events", json={
            "session_id": s_id,
            "events": [
                {
                    "event_type": "mouse_click",
                    "client_timestamp": 1690000001000,
                    "event_data": {"x": 200, "y": 300, "button": 0, "target_category": "button"}
                }
            ]
        })
        self.assertEqual(r_events.status_code, 202)

        # 3. Ingest API Telemetry
        r_api = self.client.post("/api/api-requests", json={
            "session_id": s_id,
            "endpoint": "/api/products",
            "http_method": "GET",
            "status_code": 200,
            "response_time_ms": 25.0
        })
        self.assertEqual(r_api.status_code, 201)
        self.assertEqual(r_api.json()["status"], "RECORDED")

        # 4. End Session
        r_end = self.client.post("/api/session/end", json={
            "session_id": s_id,
            "end_reason": "TASK_COMPLETED",
            "collection_mode": "HUMAN",
            "task_id": "TASK_01",
            "label": 0
        })
        self.assertEqual(r_end.status_code, 200)
        self.assertEqual(r_end.json()["status"], "COMPLETED")

    # --------------------------------------------------------------------------
    # 6. Mock Endpoints Do Not Create Sessions or Modify Research Datasets
    # --------------------------------------------------------------------------
    def test_mock_endpoints_do_not_create_sessions_or_alter_cache(self):
        """Verify calling mock domain endpoints does not create session records or mutate active cache."""
        initial_sessions_count = len(session_service._sessions)
        initial_api_logs_count = sum(len(v) for v in session_service._api_requests.values())

        # Execute mock calls
        self.client.get("/api/products")
        self.client.get("/api/products/details?id=prod_01")
        self.client.get("/api/search?q=keyboard")
        self.client.get("/api/search/filter?filter=audio&sort=rating")
        self.client.get("/api/catalog")
        self.client.post("/api/cart/items", json={"item_id": "prod_02", "quantity": 1})
        self.client.post("/api/checkout/verify", json={"shipping_method": "standard", "currency": "USD"})

        # Assert no session or telemetry record was generated by calling mock endpoints
        final_sessions_count = len(session_service._sessions)
        final_api_logs_count = sum(len(v) for v in session_service._api_requests.values())

        self.assertEqual(final_sessions_count, initial_sessions_count)
        self.assertEqual(final_api_logs_count, initial_api_logs_count)


if __name__ == "__main__":
    unittest.main()
