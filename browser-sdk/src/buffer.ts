import { BehaviorEvent, TelemetryStats } from './types.js';

export interface EventBufferOptions {
  apiBaseUrl: string;
  sessionIdGetter: () => string | null;
  batchIntervalMs?: number;
  maxBatchSize?: number;
  maxRetryBufferSize?: number;
  debug?: boolean;
}

export class EventBuffer {
  private apiBaseUrl: string;
  private sessionIdGetter: () => string | null;
  private batchIntervalMs: number;
  private maxBatchSize: number;
  private maxRetryBufferSize: number;
  private debug: boolean;

  private primaryBuffer: BehaviorEvent[] = [];
  private retryBuffer: BehaviorEvent[] = [];
  private isFlushing = false;
  private timer: number | null = null;

  // Telemetry metrics
  private totalCollected = 0;
  private totalSent = 0;
  private lastFlushTimestamp: number | null = null;
  private lastErrorMessage: string | null = null;

  constructor(options: EventBufferOptions) {
    this.apiBaseUrl = options.apiBaseUrl.replace(/\/+$/, '');
    this.sessionIdGetter = options.sessionIdGetter;
    this.batchIntervalMs = options.batchIntervalMs ?? 1500;
    this.maxBatchSize = options.maxBatchSize ?? 40;
    this.maxRetryBufferSize = options.maxRetryBufferSize ?? 150;
    this.debug = options.debug ?? false;
  }

  public startTimer(): void {
    if (this.timer !== null || typeof window === 'undefined') return;

    this.timer = window.setInterval(() => {
      this.flush();
    }, this.batchIntervalMs);
  }

  public stopTimer(): void {
    if (this.timer !== null && typeof window !== 'undefined') {
      window.clearInterval(this.timer);
      this.timer = null;
    }
  }

  /**
   * Enqueues an event into the primary buffer.
   */
  public enqueue(event: BehaviorEvent): void {
    this.totalCollected++;
    this.primaryBuffer.push(event);

    if (this.primaryBuffer.length >= this.maxBatchSize) {
      this.flush();
    }
  }

  /**
   * Flushes buffered events to backend API via standard POST.
   */
  public async flush(): Promise<boolean> {
    const sessionId = this.sessionIdGetter();
    if (!sessionId || (this.primaryBuffer.length === 0 && this.retryBuffer.length === 0)) {
      return true;
    }

    if (this.isFlushing) {
      return false;
    }

    this.isFlushing = true;

    // Drain retry items first + current primary buffer
    const batchToSend = [...this.retryBuffer, ...this.primaryBuffer];
    this.retryBuffer = [];
    this.primaryBuffer = [];

    const endpoint = `${this.apiBaseUrl}/behavior/events`;
    const payload = {
      session_id: sessionId,
      events: batchToSend,
    };

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }

      this.totalSent += batchToSend.length;
      this.lastFlushTimestamp = Date.now();
      this.lastErrorMessage = null;
      this.log(`Successfully dispatched ${batchToSend.length} telemetry events.`);
      this.isFlushing = false;
      return true;
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      this.lastErrorMessage = errMsg;
      this.log(`Telemetry dispatch failed: ${errMsg}`);

      // Re-queue events up to maxRetryBufferSize (drop oldest if exceeded)
      const merged = [...batchToSend, ...this.retryBuffer];
      if (merged.length > this.maxRetryBufferSize) {
        this.retryBuffer = merged.slice(merged.length - this.maxRetryBufferSize);
      } else {
        this.retryBuffer = merged;
      }

      this.isFlushing = false;
      return false;
    }
  }

  /**
   * Flushes final events on page teardown using sendBeacon or keepalive fetch.
   */
  public flushSyncBeacon(): boolean {
    const sessionId = this.sessionIdGetter();
    const batchToSend = [...this.retryBuffer, ...this.primaryBuffer];
    if (!sessionId || batchToSend.length === 0) return true;

    this.retryBuffer = [];
    this.primaryBuffer = [];

    const endpoint = `${this.apiBaseUrl}/behavior/events`;
    const payload = JSON.stringify({
      session_id: sessionId,
      events: batchToSend,
    });

    if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
      const blob = new Blob([payload], { type: 'application/json' });
      const queued = navigator.sendBeacon(endpoint, blob);
      if (queued) {
        this.totalSent += batchToSend.length;
        return true;
      }
    }

    // Fallback to fetch with keepalive: true
    if (typeof fetch === 'function') {
      try {
        fetch(endpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: payload,
          keepalive: true,
        }).catch(() => {});
        return true;
      } catch {
        return false;
      }
    }

    return false;
  }

  public getStats(sessionId: string | null, isRunning: boolean): TelemetryStats {
    return {
      sessionId,
      isRunning,
      eventsCollected: this.totalCollected,
      eventsSent: this.totalSent,
      eventsBuffered: this.primaryBuffer.length + this.retryBuffer.length,
      lastFlushTime: this.lastFlushTimestamp,
      lastError: this.lastErrorMessage,
    };
  }

  public clear(): void {
    this.primaryBuffer = [];
    this.retryBuffer = [];
  }

  public reset(): void {
    this.primaryBuffer = [];
    this.retryBuffer = [];
    this.totalCollected = 0;
    this.totalSent = 0;
    this.lastFlushTimestamp = null;
    this.lastErrorMessage = null;
  }

  private log(...args: unknown[]): void {
    if (this.debug) {
      console.log('[EventBuffer]', ...args);
    }
  }
}
