# Research Notes: Cross-Layer Behavioral Integrity Verification

## 1. Problem Formulation & Research Motivation

Contemporary web fraud detection operates primarily in isolated functional silos:
1. **Client-side telemetry** (e.g., CAPTCHAs, client JavaScript SDKs) evaluates mouse curves, browser canvas fingerprinting, or device characteristics. However, modern automated botnets (e.g., Puppeteer, Playwright with stealth plugins) can replay recorded human trajectories or generate Bézier curve movements.
2. **Backend API behavioral modeling** (e.g., WAFs, API gateways) evaluates request frequencies, IP reputation, and token lifecycles. However, distributed botnets using rotating residential proxies easily fly under rate-limiting thresholds.

### The Research Gap
Existing systems rarely evaluate the **temporal and causal coherence between client UI dynamics and backend API consumption**. A human user typing on a form and clicking a checkout button produces:
- A predictable interval between input completion and API dispatch.
- Natural variance in mouse deceleration prior to the click.
- Coherent API sequence transitions matching UI navigation states.

Conversely, adversarial attacks produce **Cross-Layer Discordance**:
- Case A: Programmatic API bursts originating from sessions where mouse movement is simulated or static.
- Case B: Human-like browser navigation coupled with out-of-order API parameter tampering.
- Case C: Replay attacks where mouse trajectories are identical across distinct sessions with mismatched API temporal footprints.

---

## 2. Threat Model

| Adversary Archetype | Browser Layer Characteristics | Backend API Layer Characteristics | System Detection Mechanism |
| :--- | :--- | :--- | :--- |
| **Direct API Script / Scraper** (cURL, Requests, Bot) | No browser telemetry (or static zero-entropy events) | High frequency, direct endpoint access without UI events | Rule `NO_BROWSER_TELEMETRY` + High Cross-Layer Discordance |
| **Stealth Headless Browser** (Puppeteer-Stealth, Selenium) | Bézier curve mouse paths, missing micro-jitters, constant velocity | Bursty API calls, zero human cognitive pauses | XGBoost feature anomalies (velocity std, direction changes) + Sequence Markov model |
| **Replay & Injection Attacks** | Cloned trajectory timestamps or repeated paths | Divergent API payload hashes and endpoint timings | Token binding mismatch + Path hash clustering |
| **Human Click-Farm / Fraud Ring** | Organic human motor dynamics | Scripted API sequences, parameter fuzzing, anomalous payloads | FastText + FAISS semantic distance + Agglomerative payload clustering |

---

## 3. Mathematical & Algorithmic Formulation

### 3.1. Browser Feature Engine
Let $M = \{(x_i, y_i, t_i)\}_{i=1}^N$ be the sequence of pointer events in time window $W$.
- Instantaneous velocity: $v_i = \frac{\sqrt{(x_i - x_{i-1})^2 + (y_i - y_{i-1})^2}}{t_i - t_{i-1}}$
- Angular direction changes: $\Delta \theta_i = \arccos\left(\frac{\vec{u}_i \cdot \vec{u}_{i-1}}{\|\vec{u}_i\| \|\vec{u}_{i-1}\|}\right)$
- Straightness index: $S = \frac{\sqrt{(x_N - x_1)^2 + (y_N - y_1)^2}}{\sum_{i=2}^N \sqrt{(x_i - x_{i-1})^2 + (y_i - y_{i-1})^2}}$

### 3.2. API Semantic & Structural Similarity
Let $E_k$ be the tokenized endpoint and schema structure of API call $k$.
- FastText subword representation $\mathbf{e}_k = \frac{1}{|E_k|} \sum_{w \in E_k} \mathbf{v}_w$
- Query against FAISS L2/Cosine index of baseline legitimate user request vectors $\mathcal{B}$:
  $$d_k = \min_{\mathbf{b} \in \mathcal{B}} \|\mathbf{e}_k - \mathbf{b}\|_2$$

### 3.3. Session Sequence Modeling (Markov Chain)
Let $\Sigma = \{s_{ui\_nav}, s_{ui\_click}, s_{api\_read}, s_{api\_write}, \dots\}$ be the joint state alphabet.
Given a transition matrix $P(s_t \mid s_{t-1})$ trained on legitimate session logs:
$$\text{Sequence Anomaly} = -\frac{1}{T} \sum_{t=2}^T \log P(s_t \mid s_{t-1})$$

### 3.4. Cross-Layer Discordance Metric
$$\Phi(S_{browser}, S_{api}) = \left| S_{browser} - S_{api} \right| \cdot \sigma(\kappa \cdot (S_{browser} + S_{api}))$$
where $\sigma(\cdot)$ is the logistic sigmoid and $\kappa$ is a scaling factor accentuating divergence when at least one layer indicates elevated anomaly.

---

## 4. Privacy & Regulatory Compliance (GDPR/CCPA)

1. **Zero Keylogger Guarantee**:
   The Browser SDK measures only inter-event deltas $\Delta t$ and key hold durations. Key identities (e.g. `'a'`, `'1'`, `'Enter'`) are stripped at the listener layer before any data leaves the client memory space.
2. **Form Value Isolation**:
   No DOM input values, textarea contents, or form payloads are ingested by the behavioral SDK.
3. **No PII Storage**:
   IP addresses are irreversibly hashed ($H(IP + \text{Salt})$), preventing direct user identification while allowing session correlation.
