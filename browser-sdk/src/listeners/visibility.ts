import { BehaviorEvent, VisibilityPayload } from '../types.js';

export interface VisibilityListenerOptions {
  onEvent: (event: BehaviorEvent) => void;
}

export class VisibilityListener {
  private onEvent: (event: BehaviorEvent) => void;
  private isListening = false;

  private lastHiddenTime = 0;
  private lastBlurTime = 0;

  private handleVisibilityChangeBound = this.handleVisibilityChange.bind(this);
  private handleFocusBound = this.handleFocus.bind(this);
  private handleBlurBound = this.handleBlur.bind(this);

  constructor(options: VisibilityListenerOptions) {
    this.onEvent = options.onEvent;
  }

  public attach(): void {
    if (this.isListening || typeof window === 'undefined') return;

    document.addEventListener('visibilitychange', this.handleVisibilityChangeBound);
    window.addEventListener('focus', this.handleFocusBound);
    window.addEventListener('blur', this.handleBlurBound);
    this.isListening = true;
  }

  public detach(): void {
    if (!this.isListening || typeof window === 'undefined') return;

    document.removeEventListener('visibilitychange', this.handleVisibilityChangeBound);
    window.removeEventListener('focus', this.handleFocusBound);
    window.removeEventListener('blur', this.handleBlurBound);
    this.isListening = false;
  }

  private handleVisibilityChange(): void {
    const now = Date.now();
    const isHidden = document.hidden || document.visibilityState === 'hidden';

    let durationAwayMs = 0;
    if (isHidden) {
      this.lastHiddenTime = now;
    } else {
      if (this.lastHiddenTime > 0) {
        durationAwayMs = now - this.lastHiddenTime;
        this.lastHiddenTime = 0;
      }
    }

    const payload: VisibilityPayload = {
      state: isHidden ? 'hidden' : 'visible',
      duration_away_ms: durationAwayMs,
    };

    this.onEvent({
      event_type: 'visibility',
      client_timestamp: now,
      event_data: payload,
    });
  }

  private handleFocus(): void {
    const now = Date.now();
    let durationAwayMs = 0;
    if (this.lastBlurTime > 0) {
      durationAwayMs = now - this.lastBlurTime;
      this.lastBlurTime = 0;
    }

    const payload: VisibilityPayload = {
      state: 'focus',
      duration_away_ms: durationAwayMs,
    };

    this.onEvent({
      event_type: 'visibility',
      client_timestamp: now,
      event_data: payload,
    });
  }

  private handleBlur(): void {
    const now = Date.now();
    this.lastBlurTime = now;

    const payload: VisibilityPayload = {
      state: 'blur',
      duration_away_ms: 0,
    };

    this.onEvent({
      event_type: 'visibility',
      client_timestamp: now,
      event_data: payload,
    });
  }
}
