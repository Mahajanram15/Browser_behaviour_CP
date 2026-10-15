# API Contract Specification

This document details the REST API contract for the **Browser-to-Backend Behavioral Integrity Verification System**.

Base URL: `/api` (or `/` for top-level health)

---

## Summary of Endpoints

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/health` | System health and component status check |
| `POST` | `/api/session/start` | Initialize a new tracking session |
| `POST` | `/api/behavior/events` | Ingest batch of browser behavioral telemetry |
| `POST` | `/api/api-requests` | Ingest API request logs for cross-layer correlation |
| `POST` | `/api/session/end` | Terminate and finalize an active session |
| `GET` | `/api/risk/{session_id}` | Retrieve real-time behavioral risk scores for a session |
| `GET` | `/api/explanation/{session_id}` | Retrieve SHAP and rule-based explainability details |
| `GET` | `/api/dashboard/stats` | Aggregated statistical metrics for the analyst dashboard |

---

## 1. System Health Check

### `GET /health`
- **Purpose**: Verifies that the FastAPI backend, database connection, and ML inference runtimes are operational.
- **Headers**: None required.
- **Request Body**: None.
- **Response `200 OK`**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2026-09-30T07:45:00.000Z",
  "components": {
    "database": "connected",
    "feature_engine": "ready",
    "ml_models": "initialized"
  }
}
```
- **Error Response `503 Service Unavailable`**:
```json
{
  "status": "degraded",
  "detail": "Database connection unreachable"
}
```

---

## 2. Session Initialization

### `POST /api/session/start`
- **Purpose**: Creates an active behavioral session and returns a bound `session_id`.
- **Request Body**:
```json
{
  "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...",
  "screen_resolution": "1920x1080",
  "client_timezone": "UTC+05:30",
  "client_timestamp": 1790754300000
}
```
- **Validation**:
  - `user_agent`: Non-empty string (max 512 chars).
  - `client_timestamp`: Positive 64-bit integer timestamp (ms).
- **Response `201 Created`**:
```json
{
  "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
  "status": "ACTIVE",
  "start_time": "2026-09-30T07:45:00.120Z",
  "config": {
    "batch_interval_ms": 2000,
    "sampling_rate_mouse_hz": 60
  }
}
```
- **Error Response `400 Bad Request`**:
```json
{
  "error": "INVALID_REQUEST_PAYLOAD",
  "message": "Field 'user_agent' cannot be empty"
}
```

---

## 3. Behavior Telemetry Ingestion

### `POST /api/behavior/events`
- **Purpose**: Ingests batched telemetry events captured by the Browser Behavior SDK.
- **Privacy Rule**: Event payloads must NEVER include keystroke characters, typed string values, or sensitive input contents.
- **Request Body**:
```json
{
  "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
  "events": [
    {
      "event_type": "mouse_move",
      "client_timestamp": 1790754301100,
      "event_data": {
        "x": 420.5,
        "y": 680.2,
        "velocity": 142.3,
        "acceleration": 18.2,
        "angle_degrees": 42.1
      }
    },
    {
      "event_type": "key_meta",
      "client_timestamp": 1790754301450,
      "event_data": {
        "hold_duration_ms": 78,
        "flight_time_ms": 112,
        "is_backspace": false,
        "is_paste": false
      }
    }
  ]
}
```
- **Validation**:
  - `session_id`: Must exist and have status `'ACTIVE'`.
  - `events`: Array of 1 to 500 events per batch.
  - `event_type`: Allowed values: `['mouse_move', 'mouse_click', 'scroll', 'key_meta', 'navigation']`.
- **Response `202 Accepted`**:
```json
{
  "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
  "processed_events": 2,
  "status": "INGESTED"
}
```
- **Error Response `404 Not Found`**:
```json
{
  "error": "SESSION_NOT_FOUND",
  "message": "Session 'sess_invalid' does not exist or has already ended"
}
```

---

## 4. API Request Telemetry Ingestion

### `POST /api/api-requests`
- **Purpose**: Ingests backend/API access logs associated with a session to correlate API behavior with browser dynamics.
- **Request Body**:
```json
{
  "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
  "endpoint": "/api/v1/orders/submit",
  "http_method": "POST",
  "status_code": 200,
  "response_time_ms": 42.5,
  "request_size_bytes": 1024,
  "headers_fingerprint": "a3f8c7b41e92d805",
  "payload_structure_hash": "e6a7102bc45019a8",
  "timestamp": 1790754302000
}
```
- **Response `201 Created`**:
```json
{
  "request_id": 1042,
  "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
  "status": "RECORDED"
}
```

---

## 5. Session Termination

### `POST /api/session/end`
- **Purpose**: Marks a session as `COMPLETED`, finalizes sliding window feature aggregation, and computes the terminal behavioral score.
- **Request Body**:
```json
{
  "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
  "end_reason": "USER_LOGOUT"
}
```
- **Response `200 OK`**:
```json
{
  "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
  "status": "COMPLETED",
  "duration_seconds": 142.5,
  "total_events_captured": 482,
  "final_integrity_score": 0.14
}
```

---

## 6. Risk Score Retrieval

### `GET /api/risk/{session_id}`
- **Purpose**: Fetches the multi-signal behavioral risk score breakdown and security decision for an active or completed session.
- **Parameters**: `session_id` (Path parameter, string).
- **Response `200 OK`**:
```json
{
  "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
  "behavioral_integrity_score": 0.18,
  "signals": {
    "browser_score": 0.15,
    "api_anomaly_score": 0.22,
    "api_structure_score": 0.10,
    "sequence_score": 0.12,
    "frequency_score": 0.05,
    "cross_layer_discordance": 0.07
  },
  "decision": {
    "action": "ALLOW",
    "reason": "Normal human behavioral dynamics observed across browser and backend layers.",
    "enacted_at": "2026-09-30T07:46:10.000Z"
  },
  "last_evaluated_at": "2026-09-30T07:46:10.000Z"
}
```

---

## 7. Explainability & Attribution

### `GET /api/explanation/{session_id}`
- **Purpose**: Retrieves SHAP feature contributions and triggered security rules explaining the risk score.
- **Parameters**: `session_id` (Path parameter, string).
- **Response `200 OK`**:
```json
{
  "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
  "behavioral_integrity_score": 0.82,
  "decision": "BLOCK",
  "shap_contributions": [
    {
      "feature_name": "mouse_direction_changes",
      "feature_value": 0.0,
      "shap_value": 0.42,
      "description": "Zero direction changes indicating purely linear programmatic mouse trajectory."
    },
    {
      "feature_name": "cross_layer_discordance",
      "feature_value": 0.78,
      "shap_value": 0.31,
      "description": "High API call volume without preceding user interface interaction."
    }
  ],
  "rule_triggers": [
    {
      "rule_id": "RULE_CROSS_LAYER_UNLINKED_POST",
      "severity": "HIGH",
      "message": "API write operation invoked without any recent mouse click or keypress event in browser session."
    }
  ]
}
```

---

## 8. Dashboard Aggregate Statistics

### `GET /api/dashboard/stats`
- **Purpose**: Aggregates fleet-wide metrics for the cybersecurity analyst dashboard.
- **Query Parameters**:
  - `time_range`: Optional (`1h`, `24h`, `7d`, default `24h`).
- **Response `200 OK`**:
```json
{
  "total_sessions": 1420,
  "active_sessions": 38,
  "average_risk_score": 0.24,
  "decision_distribution": {
    "ALLOW": 1280,
    "CHALLENGE": 98,
    "RATE_LIMIT": 32,
    "BLOCK": 10
  },
  "recent_flagged_sessions": [
    {
      "session_id": "sess_01HZY9B5A8M3V1C7X2E4F6G8K0",
      "risk_score": 0.82,
      "decision": "BLOCK",
      "primary_reason": "Programmatic trajectory & API frequency burst",
      "timestamp": "2026-09-30T07:44:12.000Z"
    }
  ]
}
```
