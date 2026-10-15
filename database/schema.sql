-- ==============================================================================
-- BROWSER-TO-BACKEND BEHAVIORAL INTEGRITY VERIFICATION SYSTEM
-- PostgreSQL Database Schema Definition
-- ==============================================================================

-- Enable UUID extension if available
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------------------------
-- 1. SESSIONS TABLE
-- Tracks active and completed browser-to-backend user interaction sessions.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(64) PRIMARY KEY,
    user_agent TEXT NOT NULL,
    ip_hash VARCHAR(64) NOT NULL, -- SHA-256 hashed IP for client privacy
    start_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- 'ACTIVE', 'COMPLETED', 'TERMINATED'
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_session_status CHECK (status IN ('ACTIVE', 'COMPLETED', 'TERMINATED'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);

-- ------------------------------------------------------------------------------
-- 2. BEHAVIOR_EVENTS TABLE
-- Raw fine-grained telemetry emitted by the Browser Behavior SDK.
-- PRIVACY COMPLIANCE: NEVER stores raw keystroke characters, typed text, or form inputs.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS behavior_events (
    event_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    event_type VARCHAR(32) NOT NULL, -- 'mouse_move', 'mouse_click', 'scroll', 'key_meta', 'navigation'
    client_timestamp BIGINT NOT NULL, -- Epoch ms from browser clock
    server_timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    event_data JSONB NOT NULL, -- Derived metadata (e.g., velocity, angle, key_hold_ms, scroll_delta)
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_behavior_events_session_id ON behavior_events(session_id);
CREATE INDEX IF NOT EXISTS idx_behavior_events_event_type ON behavior_events(event_type);
CREATE INDEX IF NOT EXISTS idx_behavior_events_client_timestamp ON behavior_events(client_timestamp);
CREATE INDEX IF NOT EXISTS idx_behavior_events_server_timestamp ON behavior_events(server_timestamp);

-- ------------------------------------------------------------------------------
-- 3. API_REQUESTS TABLE
-- Backend/API access logs correlated with active client sessions.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS api_requests (
    request_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    sequence_number INTEGER NOT NULL DEFAULT 1, -- Monotonically increasing sequence within session
    endpoint VARCHAR(255) NOT NULL,
    http_method VARCHAR(10) NOT NULL,
    status_code SMALLINT NOT NULL,
    response_time_ms DOUBLE PRECISION NOT NULL,
    request_size_bytes INTEGER DEFAULT 0,
    response_size_bytes INTEGER DEFAULT 0,
    headers_fingerprint VARCHAR(64),
    payload_structure_hash VARCHAR(64), -- Structural hash of schema, zero PII
    param_keys JSONB DEFAULT '[]'::jsonb, -- Query parameter names only, zero parameter values
    payload_keys JSONB DEFAULT '[]'::jsonb, -- JSON payload field names only, zero payload values
    client_timestamp BIGINT, -- Browser-side timestamp when API request was initiated
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

/

-- ------------------------------------------------------------------------------
-- 4. BEHAVIOR_FEATURES TABLE
-- Aggregated statistical features computed over sliding windows for ML inference.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS behavior_features (
    feature_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    -- Mouse movement dynamics
    mouse_velocity_mean DOUBLE PRECISION DEFAULT 0.0,
    mouse_velocity_std DOUBLE PRECISION DEFAULT 0.0,
    mouse_acceleration_mean DOUBLE PRECISION DEFAULT 0.0,
    mouse_direction_changes INTEGER DEFAULT 0,
    mouse_path_straightness DOUBLE PRECISION DEFAULT 0.0,
    -- Click dynamics
    click_count INTEGER DEFAULT 0,
    click_interval_mean DOUBLE PRECISION DEFAULT 0.0,
    click_interval_std DOUBLE PRECISION DEFAULT 0.0,
    double_click_count INTEGER DEFAULT 0,
    -- Keystroke dynamics (Derived statistics only)
    typing_speed_cps DOUBLE PRECISION DEFAULT 0.0, -- characters per second
    key_hold_mean_ms DOUBLE PRECISION DEFAULT 0.0,
    key_hold_std_ms DOUBLE PRECISION DEFAULT 0.0,
    inter_key_interval_mean_ms DOUBLE PRECISION DEFAULT 0.0,
    backspace_rate DOUBLE PRECISION DEFAULT 0.0,
    paste_count INTEGER DEFAULT 0,
    -- Scroll dynamics
    scroll_count INTEGER DEFAULT 0,
    scroll_velocity_mean DOUBLE PRECISION DEFAULT 0.0,
    scroll_direction_reversals INTEGER DEFAULT 0,
    -- Sequence dynamics
    time_between_actions_mean_ms DOUBLE PRECISION DEFAULT 0.0,
    repeated_pattern_ratio DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_behavior_features_session_id ON behavior_features(session_id);
CREATE INDEX IF NOT EXISTS idx_behavior_features_window ON behavior_features(window_start, window_end);

-- ------------------------------------------------------------------------------
-- 5. RISK_SCORES TABLE
-- Multi-signal behavioral integrity risk calculations.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_scores (
    score_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    browser_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,       -- [0.0 - 1.0] from XGBoost browser model
    api_anomaly_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,   -- [0.0 - 1.0] from FastText + FAISS semantic distance
    api_structure_score DOUBLE PRECISION NOT NULL DEFAULT 0.0, -- [0.0 - 1.0] from Agglomerative Clustering
    sequence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,      -- [0.0 - 1.0] from Markov Chain sequence engine
    frequency_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,     -- [0.0 - 1.0] from rate & frequency heuristics
    cross_layer_inconsistency_score DOUBLE PRECISION NOT NULL DEFAULT 0.0, -- Discordance metric
    behavioral_integrity_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,      -- Fused risk score [0.0 - 1.0]
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_risk_scores_session_id ON risk_scores(session_id);
CREATE INDEX IF NOT EXISTS idx_risk_scores_evaluated_at ON risk_scores(evaluated_at);
CREATE INDEX IF NOT EXISTS idx_risk_scores_integrity ON risk_scores(behavioral_integrity_score);

-- ------------------------------------------------------------------------------
-- 6. SECURITY_ACTIONS TABLE
-- Security policy decisions made based on behavioral integrity risk scores.
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS security_actions (
    action_id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(64) NOT NULL,
    score_id BIGINT,
    decision VARCHAR(20) NOT NULL, -- 'ALLOW', 'CHALLENGE', 'RATE_LIMIT', 'BLOCK'
    reason TEXT NOT NULL,
    shap_contributions JSONB DEFAULT '{}'::jsonb, -- Top contributing risk factors
    rule_triggers JSONB DEFAULT '[]'::jsonb,      -- List of rule codes triggered
    enacted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_security_decision CHECK (decision IN ('ALLOW', 'CHALLENGE', 'RATE_LIMIT', 'BLOCK')),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (score_id) REFERENCES risk_scores(score_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_security_actions_session_id ON security_actions(session_id);
CREATE INDEX IF NOT EXISTS idx_security_actions_decision ON security_actions(decision);
CREATE INDEX IF NOT EXISTS idx_security_actions_enacted_at ON security_actions(enacted_at);
