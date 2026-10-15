/**
 * Type Definitions for Browser Behavior SDK
 *
 * STRICT PRIVACY DIRECTIVE:
 * Under no circumstances does this SDK capture, store, or transmit:
 * - Keystroke characters or typed textual contents
 * - Input field values, passwords, or form payloads
 * - Clipboard data or personal identifiable info
 */

export type EventType =
  | 'mouse_move'
  | 'mouse_click'
  | 'key_meta'
  | 'scroll'
  | 'navigation'
  | 'visibility';

export type TargetCategory = 'button' | 'link' | 'input' | 'select' | 'canvas' | 'other';

export interface MouseMovePayload {
  x: number;
  y: number;
  distance_px: number;
  time_delta_ms: number;
  velocity_px_s: number;
  acceleration_px_s2: number;
  angle_degrees: number;
  direction_change_deg: number;
}

export interface MouseClickPayload {
  x: number;
  y: number;
  button: number; // 0: left, 1: middle, 2: right
  click_type: 'single' | 'double';
  time_since_last_click_ms: number;
  target_category: TargetCategory;
}

export interface KeyMetaPayload {
  /** Hold duration in milliseconds (keyup - keydown) */
  dwell_ms: number;
  /** Flight time in milliseconds (keydown_curr - keyup_prev) */
  flight_ms: number;
  /** Inter-key interval (keydown_curr - keydown_prev) */
  inter_key_interval_ms: number;
  is_backspace: boolean;
  is_paste: boolean;
  // NOTE: Key characters, key codes, and input values are strictly omitted.
}

export interface ScrollPayload {
  scroll_x: number;
  scroll_y: number;
  delta_x: number;
  delta_y: number;
  velocity_px_s: number;
  direction: 'up' | 'down' | 'left' | 'right' | 'none';
  time_since_last_scroll_ms: number;
}

export interface NavigationPayload {
  path: string; // Sanitized pathname (no query params, no hash secrets)
  referrer: string; // Sanitized referrer pathname
  dwell_time_ms: number;
  sequence_number: number;
}

export interface VisibilityPayload {
  state: 'visible' | 'hidden' | 'focus' | 'blur';
  duration_away_ms: number;
}

export type EventDataPayload =
  | MouseMovePayload
  | MouseClickPayload
  | KeyMetaPayload
  | ScrollPayload
  | NavigationPayload
  | VisibilityPayload
  | Record<string, unknown>;

export interface BehaviorEvent {
  event_type: EventType;
  client_timestamp: number;
  event_data: EventDataPayload;
}

export interface SDKConfig {
  apiBaseUrl: string;
  sessionId?: string;
  batchIntervalMs?: number;
  maxBatchSize?: number;
  sampleRateMouseHz?: number; // Target mouse sampling rate (default ~25-30Hz)
  scrollSampleIntervalMs?: number; // Target scroll debounce interval (default ~100ms)
  maxRetryBufferSize?: number; // Max events to retain on network drops (default 150)
  collectionMode?: 'HUMAN' | 'AUTOMATED' | 'UNSPECIFIED';
  automationCondition?: 'AUTOMATED_DETERMINISTIC' | 'AUTOMATED_VARIABLE' | 'NONE' | string;
  participantId?: string;
  taskId?: string;
  label?: number;
  debug?: boolean;
}

export interface SessionStartOptions {
  collectionMode?: 'HUMAN' | 'AUTOMATED' | 'UNSPECIFIED';
  automationCondition?: 'AUTOMATED_DETERMINISTIC' | 'AUTOMATED_VARIABLE' | 'NONE' | string;
  participantId?: string;
  taskId?: string;
  label?: number;
}

export interface SessionStartResponse {
  session_id: string;
  status: string;
  start_time: string;
  config: {
    batch_interval_ms: number;
    sampling_rate_mouse_hz: number;
  };
}

export interface SessionEndResponse {
  session_id: string;
  status: string;
  duration_seconds: number;
  total_events_captured: number;
  final_integrity_score?: number;
}

export interface TelemetryStats {
  sessionId: string | null;
  isRunning: boolean;
  eventsCollected: number;
  eventsSent: number;
  eventsBuffered: number;
  lastFlushTime: number | null;
  lastError: string | null;
}
