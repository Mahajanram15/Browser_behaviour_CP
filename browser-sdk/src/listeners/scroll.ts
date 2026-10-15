import { BehaviorEvent, ScrollPayload } from '../types.js';

export interface ScrollListenerOptions {
  sampleIntervalMs?: number; // default ~100ms
  onEvent: (event: BehaviorEvent) => void;
}

export class ScrollListener {
  private sampleIntervalMs: number;
  private onEvent: (event: BehaviorEvent) => void;
  private isListening = false;

  private lastScrollTime = 0;
  private lastScrollX = 0;
  private lastScrollY = 0;
  private accumulatedDeltaX = 0;
  private accumulatedDeltaY = 0;
  private debounceTimer: number | null = null;

  private handleScrollBound = this.handleScroll.bind(this);

  constructor(options: ScrollListenerOptions) {
    this.sampleIntervalMs = options.sampleIntervalMs ?? 100;
    this.onEvent = options.onEvent;
  }

  public attach(): void {
    if (this.isListening || typeof window === 'undefined') return;

    this.lastScrollX = window.scrollX || window.pageXOffset || 0;
    this.lastScrollY = window.scrollY || window.pageYOffset || 0;
    window.addEventListener('scroll', this.handleScrollBound, { passive: true });
    this.isListening = true;
  }

  public detach(): void {
    if (!this.isListening || typeof window === 'undefined') return;

    window.removeEventListener('scroll', this.handleScrollBound);
    if (this.debounceTimer !== null) {
      window.clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
    this.isListening = false;
  }

  private handleScroll(): void {
    const now = Date.now();
    const currentX = window.scrollX || window.pageXOffset || 0;
    const currentY = window.scrollY || window.pageYOffset || 0;

    const dx = currentX - this.lastScrollX;
    const dy = currentY - this.lastScrollY;

    this.accumulatedDeltaX += dx;
    this.accumulatedDeltaY += dy;
    this.lastScrollX = currentX;
    this.lastScrollY = currentY;

    const timeSinceLastEmit = this.lastScrollTime > 0 ? now - this.lastScrollTime : Infinity;

    if (timeSinceLastEmit >= this.sampleIntervalMs) {
      this.emitScrollEvent(now, currentX, currentY);
    } else {
      if (this.debounceTimer !== null) {
        window.clearTimeout(this.debounceTimer);
      }
      this.debounceTimer = window.setTimeout(() => {
        this.emitScrollEvent(Date.now(), this.lastScrollX, this.lastScrollY);
        this.debounceTimer = null;
      }, this.sampleIntervalMs);
    }
  }

  private emitScrollEvent(now: number, currentX: number, currentY: number): void {
    const timeDeltaMs = this.lastScrollTime > 0 ? now - this.lastScrollTime : 100;
    const dtSeconds = Math.max(0.016, timeDeltaMs / 1000);

    const deltaX = this.accumulatedDeltaX;
    const deltaY = this.accumulatedDeltaY;
    this.accumulatedDeltaX = 0;
    this.accumulatedDeltaY = 0;

    const totalDistance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    const velocity = totalDistance / dtSeconds;

    let direction: 'up' | 'down' | 'left' | 'right' | 'none' = 'none';
    if (Math.abs(deltaY) >= Math.abs(deltaX)) {
      if (deltaY > 0) direction = 'down';
      else if (deltaY < 0) direction = 'up';
    } else {
      if (deltaX > 0) direction = 'right';
      else if (deltaX < 0) direction = 'left';
    }

    const payload: ScrollPayload = {
      scroll_x: Math.round(currentX),
      scroll_y: Math.round(currentY),
      delta_x: Math.round(deltaX),
      delta_y: Math.round(deltaY),
      velocity_px_s: Math.round(velocity * 10) / 10,
      direction,
      time_since_last_scroll_ms: this.lastScrollTime > 0 ? timeDeltaMs : 0,
    };

    this.lastScrollTime = now;

    this.onEvent({
      event_type: 'scroll',
      client_timestamp: now,
      event_data: payload,
    });
  }
}
