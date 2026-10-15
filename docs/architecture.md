# System Architecture: Browser-to-Backend Behavioral Integrity Verification System

## 1. Executive Summary & Core Principle

Modern automated threat actors and sophisticated fraud vectors bypass conventional perimeter defenses (such as static bot challenges, CAPTCHAs, or standalone IP/WAF rate limits) by decoupling or mimicking single layers. For example:
- **Headless automation with synthetic mouse movements** can mimic human micro-trajectories while executing automated, high-frequency backend API scraping.
- **Human-assisted fraud / click-farming** produces legitimate human motor interactions on the browser UI, but exhibits anomalous, out-of-order, or scripted API request graphs.

The **Browser-to-Backend Behavioral Integrity Verification System** solves this by establishing a **Cross-Layer Behavioral Correlation Architecture**. The core principle is that genuine user sessions exhibit natural, correlated entropy between physical user-interface dynamics (mouse, keyboard cadence, scrolling, navigation) and backend resource requests (endpoint traversal order, invocation intervals, semantic intent).

The system outputs a continuous **Behavioral Integrity / Risk Score** $[0.0, 1.0]$, supported by explainable attribution (SHAP values & deterministic rule triggers), categorizing sessions into `ALLOW`, `CHALLENGE`, or `RATE_LIMIT` / `BLOCK`.

---

## 2. High-Level Target Architecture Diagram

```
Browser Client / Web Application
           │
           ▼
  [ TypeScript Browser SDK ]
  ├─ Raw Telemetry Capture (Mouse, Keystroke Dynamics, Scroll, Timing)
  ├─ Privacy Filter (Zero Key Characters / Zero Form PII)
  └─ Micro-Batching & Async Transport
           │
           ▼ (HTTPS / JSON)
  [ FastAPI Backend Gateway ]
  ├─ Session Management & Token Binding
  ├─ Async Ingestion Pipeline (PostgreSQL)
  │
  ├───► [ 1. Behavior Feature Engine ]
  │           │
  │           ▼ (Sliding Window Statistics)
  │     [ XGBoost Model ] ──► Browser Anomaly Score (S_browser)
  │           │
  │           ▼
  │     [ SHAP Explainer ] ──► Feature Attribution
  │
  ├───► [ 2. API Behavior Engine ]
  │           │
  │           ├─► [ Structure Analysis ] (CountVectorizer + Clustering) ──► S_api_struct
  │           └─► [ FastText + FAISS Index ] (Semantic Vector Distance) ──► S_api_semantic
  │
  └───► [ 3. Sequence Engine ]
              │
              ▼
        [ Markov Chain Model ] ──► Sequence Transition Anomaly (S_sequence)
              │
              ▼
    ========================================================
    [ 4. Cross-Layer Risk Fusion Engine ]
    - Evaluates Discordance: D = |S_browser - S_api|
    - Weighted Fusion: R = w1*S_browser + w2*S_api + w3*S_seq + w4*D
    ========================================================
              │
              ▼
    [ 5. Security Decision Engine ]
    ├─ R < 0.35  ──► ALLOW
    ├─ 0.35 <= R < 0.70 ──► CHALLENGE (Step-Up Verification)
    └─ R >= 0.70 ──► RATE_LIMIT / BLOCK
              │
              ▼
    [ 6. SOC / Analyst React Dashboard ]
    - Live Risk Timeline & Session Topology
    - Radar Charts of Behavioral Signals
    - Cross-Layer Anomaly Visualizations & SHAP Explanations
```

---

## 3. Component Breakdown & Responsibilities

### 3.1. Browser Behavior SDK (`browser-sdk/`)
- **Technology**: TypeScript (zero heavy external runtime dependencies).
- **Core Functionality**:
  - Intercepts pointer events (`mousemove`, `mousedown`, `mouseup`, `click`, `dblclick`).
  - Measures trajectory curvature, instantaneous velocity, angular variance, and deceleration.
  - Monitors keyboard timing (`keydown`, `keyup` deltas) **without ever reading `event.key`, `event.code`, or input field values**.
  - Tracks scroll acceleration and reversal patterns.
  - Buffers events client-side and transmits in lightweight batches to prevent UI thread starvation.

### 3.2. FastAPI Backend Core (`backend/app/`)
- **Technology**: Python 3, FastAPI, Pydantic v2, SQLAlchemy / asyncpg.
- **Core Functionality**:
  - Serves lightweight asynchronous REST endpoints for session lifecycle, event ingestion, and dashboard data.
  - Generates cryptographically secure session identifiers tied to client fingerprints.
  - Dispatches background workers for sliding-window feature aggregation and risk recalculation.
  - Implements API middleware to automatically intercept and log backend route calls for the API behavior engine.

### 3.3. Behavior Feature Engine (`ml/features/`)
- Extracts time-series and distributional features over $T$-second sliding windows (e.g., $T = 5s, 15s, 60s$):
  - **Mouse**: Mean velocity, velocity variance, path straightness ratio, direction change frequency.
  - **Clicks**: Inter-click interval mean/std, double-click cadence.
  - **Keystrokes**: Inter-key interval (flight time), key hold duration (dwell time), typing speed (characters/sec), backspace frequency, paste events.
  - **Scroll**: Scroll burst count, mean velocity, scroll direction inversion rate.

### 3.4. Machine Learning & Behavioral Inference
- **Browser Behavior Model**: **XGBoost Classifier** trained on high-entropy human vs. synthetic bot trajectories.
- **API Structure Analyzer**: **Scikit-learn CountVectorizer** + **Agglomerative Clustering** analyzing structural syntax of query parameters, payload keys, and endpoint paths.
- **API Semantic Similarity Engine**: **FastText** embeddings mapped into a **FAISS** vector index to compute cosine distances from normal baseline API navigation flows.
- **Sequence Engine**: First-order and second-order **Markov Chain transition probability matrices** modeling valid transitions between UI actions and API endpoints.

### 3.5. Cross-Layer Risk Fusion Engine
Combines normalized signal outputs ($[0.0, 1.0]$) into a consolidated **Behavioral Integrity Score**:

$$R_{final} = w_b \cdot S_{browser} + w_{api} \cdot S_{api} + w_{seq} \cdot S_{sequence} + w_{disc} \cdot \Phi(S_{browser}, S_{api}) + w_{freq} \cdot S_{frequency}$$

Where $\Phi(S_{browser}, S_{api})$ is the **Cross-Layer Discordance Penalty** that spikes when one layer exhibits human-like metrics while the correlated layer exhibits extreme machine-like metrics.

### 3.6. Explainability Engine
- Generates localized **SHAP (SHapley Additive exPlanations)** values from the XGBoost model to show which physical dynamics contributed most to the risk elevation.
- Synthesizes structured, human-readable audit reasons (e.g., *"Excessive linear mouse trajectory"*, *"API call executed without preceding browser DOM interaction"*).

### 3.7. Security Decision Engine
- Evaluates risk thresholds to issue real-time policy enforcements:
  - **`ALLOW`**: $R < 0.35$ — Unrestricted access.
  - **`CHALLENGE`**: $0.35 \le R < 0.70$ — Trigger step-up verification / challenge.
  - **`RATE_LIMIT` / `BLOCK`**: $R \ge 0.70$ — Enforce rate limiting or block requests.

### 3.8. React Security Operations Dashboard (`frontend/`)
- **Technology**: React 18, TypeScript, Tailwind CSS, Recharts.
- Provides cybersecurity analysts and engineers with:
  - Real-time session monitoring table with status badges and risk scores.
  - Signal decomposition radar charts and risk timelines over session duration.
  - Cross-layer anomaly event logs with SHAP feature contribution waterfalls.

---

## 4. Privacy & Ethical Guardrails

1. **Zero Keystroke Content Capture**: The system strictly records timestamp deltas ($\Delta t = t_{keyup} - t_{keydown}$) and inter-key gaps. The actual characters pressed are deliberately dropped at the browser SDK level.
2. **Zero Form Data Ingestion**: Form field contents, values, search queries, and credentials are never captured or forwarded.
3. **Anonymized Client Identification**: Client IP addresses are stored only as SHA-256 salted hashes.
4. **Transparent Risk Scoring**: No black-box automated blocks without explainability logs; all elevated actions preserve SHAP feature rankings and rule traces for auditing.
