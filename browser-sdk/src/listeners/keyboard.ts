import { BehaviorEvent, KeyMetaPayload } from '../types.js';

export interface KeyboardListenerOptions {
  onEvent: (event: BehaviorEvent) => void;
}

export class KeyboardListener {
  private onEvent: (event: BehaviorEvent) => void;
  private isListening = false;

  // Transient in-memory timing structures (never emitted externally)
  private activeKeydownTimestamps: Map<string, number> = new Map();
  private lastKeydownTime = 0;
  private lastKeyupTime = 0;

  // Bound handlers
  private handleKeyDownBound = this.handleKeyDown.bind(this);
  private handleKeyUpBound = this.handleKeyUp.bind(this);
  private handlePasteBound = this.handlePaste.bind(this);

  constructor(options: KeyboardListenerOptions) {
    this.onEvent = options.onEvent;
  }

  public attach(): void {
    if (this.isListening || typeof window === 'undefined') return;

    window.addEventListener('keydown', this.handleKeyDownBound, { passive: true, capture: true });
    window.addEventListener('keyup', this.handleKeyUpBound, { passive: true, capture: true });
    window.addEventListener('paste', this.handlePasteBound, { passive: true, capture: true });
    this.isListening = true;
  }

  public detach(): void {
    if (!this.isListening || typeof window === 'undefined') return;

    window.removeEventListener('keydown', this.handleKeyDownBound, { capture: true });
    window.removeEventListener('keyup', this.handleKeyUpBound, { capture: true });
    window.removeEventListener('paste', this.handlePasteBound, { capture: true });

    this.activeKeydownTimestamps.clear();
    this.isListening = false;
  }

  private handleKeyDown(e: KeyboardEvent): void {
    const now = Date.now();

    const transientSlot = e.code || 'slot_default';
    if (!this.activeKeydownTimestamps.has(transientSlot)) {
      this.activeKeydownTimestamps.set(transientSlot, now);
    }

    const isPasteCombo = (e.ctrlKey || e.metaKey) && (e.key === 'v' || e.code === 'KeyV' || e.keyCode === 86);

    const flightTimeMs = this.lastKeyupTime > 0 ? Math.max(0, now - this.lastKeyupTime) : 0;
    const interKeyIntervalMs = this.lastKeydownTime > 0 ? Math.max(0, now - this.lastKeydownTime) : 0;

    this.lastKeydownTime = now;

    if (isPasteCombo) {
      this.emitKeyboardEvent({
        dwell_ms: 0,
        flight_ms: flightTimeMs,
        inter_key_interval_ms: interKeyIntervalMs,
        is_backspace: false,
        is_paste: true,
      }, now);
    }
  }

  private handleKeyUp(e: KeyboardEvent): void {
    const now = Date.now();
    const transientSlot = e.code || 'slot_default';

    const downTime = this.activeKeydownTimestamps.get(transientSlot) ?? this.lastKeydownTime ?? now;
    this.activeKeydownTimestamps.delete(transientSlot);

    const dwellMs = Math.max(0, now - downTime);
    const flightTimeMs = this.lastKeyupTime > 0 ? Math.max(0, downTime - this.lastKeyupTime) : 0;
    const interKeyIntervalMs = this.lastKeydownTime > 0 ? Math.max(0, downTime - this.lastKeydownTime) : 0;

    const isBackspace = e.key === 'Backspace' || e.code === 'Backspace' || e.keyCode === 8;

    this.lastKeyupTime = now;

    // STRICT PRIVACY GUARANTEE: No key name, code, char, or input value is included.
    this.emitKeyboardEvent({
      dwell_ms: dwellMs,
      flight_ms: flightTimeMs,
      inter_key_interval_ms: interKeyIntervalMs,
      is_backspace: isBackspace,
      is_paste: false,
    }, now);
  }

  private handlePaste(): void {
    const now = Date.now();
    this.emitKeyboardEvent({
      dwell_ms: 0,
      flight_ms: 0,
      inter_key_interval_ms: 0,
      is_backspace: false,
      is_paste: true,
    }, now);
  }

  private emitKeyboardEvent(payload: KeyMetaPayload, timestamp: number): void {
    this.onEvent({
      event_type: 'key_meta',
      client_timestamp: timestamp,
      event_data: payload,
    });
  }
}
