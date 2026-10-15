/**
 * Browser Behavior SDK
 * Production-ready TypeScript behavioral biometrics & integrity telemetry client.
 */

import {
  SDKConfig,
  BehaviorEvent,
  SessionStartResponse,
  SessionEndResponse,
  TelemetryStats,
  SessionStartOptions,
} from './types.js';
import { MouseListener } from './listeners/mouse.js';
import { KeyboardListener } from './listeners/keyboard.js';
import { ScrollListener } from './listeners/scroll.js';
import { NavigationListener } from './listeners/navigation.js';
import { VisibilityListener } from './listeners/visibility.js';
import { EventBuffer } from './buffer.js';

export * from './types.js';

export class BehavioralSDK {
  private config: Required<SDKConfig>;
  private sessionId: string | null = null;
  private isRunning = false;

  private buffer: EventBuffer;
  private mouseListener: MouseListener;
  private keyboardListener: KeyboardListener;
  private scrollListener: ScrollListener;
  private navigationListener: NavigationListener;
  private visibilityListener: VisibilityListener;

  // Bound lifecycle handlers
  private handlePageHideBound = this.handlePageHide.bind(this);
  private handleBeforeUnloadBound = this.handleBeforeUnload.bind(this);

  constructor(config: SDKConfig) {
    this.config = {
      apiBaseUrl: config.apiBaseUrl.replace(/\/+$/, ''),
      sessionId: config.sessionId || '',
      batchIntervalMs: config.batchIntervalMs ?? 1500,
      maxBatchSize: config.maxBatchSize ?? 40,
      sampleRateMouseHz: config.sampleRateMouseHz ?? 30,
      scrollSampleIntervalMs: config.scrollSampleIntervalMs ?? 100,
      maxRetryBufferSize: config.maxRetryBufferSize ?? 150,
      collectionMode: config.collectionMode ?? 'UNSPECIFIED',
      automationCondition: config.automationCondition ?? (config.collectionMode === 'AUTOMATED' ? 'AUTOMATED_DETERMINISTIC' : 'NONE'),
      participantId: config.participantId ?? '',
      taskId: config.taskId ?? 'TASK_01',
      label: config.label ?? (config.collectionMode === 'HUMAN' ? 0 : config.collectionMode === 'AUTOMATED' ? 1 : 0),
      debug: config.debug ?? false,
    };

    if (config.sessionId) {
      this.sessionId = config.sessionId;
    }

    // Initialize Event Buffer
    this.buffer = new EventBuffer({
      apiBaseUrl: this.config.apiBaseUrl,
      sessionIdGetter: () => this.sessionId,
      batchIntervalMs: this.config.batchIntervalMs,
      maxBatchSize: this.config.maxBatchSize,
      maxRetryBufferSize: this.config.maxRetryBufferSize,
      debug: this.config.debug,
    });

    const enqueueCallback = (event: BehaviorEvent) => {
      this.buffer.enqueue(event);
    };

    // Initialize individual behavioral listeners
    this.mouseListener = new MouseListener({
      sampleRateHz: this.config.sampleRateMouseHz,
      onEvent: enqueueCallback,
    });

    this.keyboardListener = new KeyboardListener({
      onEvent: enqueueCallback,
    });

    this.scrollListener = new ScrollListener({
      sampleIntervalMs: this.config.scrollSampleIntervalMs,
      onEvent: enqueueCallback,
    });

    this.navigationListener = new NavigationListener({
      onEvent: enqueueCallback,
    });

    this.visibilityListener = new VisibilityListener({
      onEvent: enqueueCallback,
    });
  }

  /**
   * Initializes or binds a session with the backend API gateway.
   */
  public async startSession(options?: SessionStartOptions): Promise<string> {
    if (this.isRunning && this.sessionId) {
      return this.sessionId;
    }

    const payload = {
      user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Unknown',
      screen_resolution:
        typeof window !== 'undefined'
          ? `${window.screen.width}x${window.screen.height}`
          : '1920x1080',
      client_timezone:
        typeof Intl !== 'undefined'
          ? Intl.DateTimeFormat().resolvedOptions().timeZone
          : 'UTC',
      client_timestamp: Date.now(),
      collection_mode: options?.collectionMode || this.config.collectionMode || 'UNSPECIFIED',
      automation_condition: options?.automationCondition || this.config.automationCondition || undefined,
      participant_id: options?.participantId || this.config.participantId || undefined,
      task_id: options?.taskId || this.config.taskId || 'TASK_01',
      label: options?.label !== undefined ? options.label : this.config.label,
    };

    try {
      const res = await fetch(`${this.config.apiBaseUrl}/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Failed to initialize session: HTTP ${res.status}`);
      }

      const data: SessionStartResponse = await res.json();
      this.sessionId = data.session_id;
      this.log('Session bound successfully:', this.sessionId);
      return this.sessionId;
    } catch (err: unknown) {
      this.log('Session start error:', err);
      // Generate fallback local session ID so app telemetry collection never crashes
      this.sessionId = `sess_local_${Date.now()}`;
      return this.sessionId;
    }
  }

  /**
   * Starts behavioral telemetry collection and background batch dispatcher.
   */
  public async start(options?: SessionStartOptions): Promise<void> {
    if (this.isRunning) return;

    await this.startSession(options);

    // Attach all behavioral listeners
    this.mouseListener.attach();
    this.keyboardListener.attach();
    this.scrollListener.attach();
    this.navigationListener.attach();
    this.visibilityListener.attach();

    // Attach window lifecycle handlers
    if (typeof window !== 'undefined') {
      window.addEventListener('pagehide', this.handlePageHideBound);
      window.addEventListener('beforeunload', this.handleBeforeUnloadBound);
    }

    this.buffer.startTimer();
    this.isRunning = true;
    this.log('Behavioral SDK telemetry started');
  }

  /**
   * Enqueues a manual behavioral event (e.g. synthetic or custom domain event).
   */
  public recordEvent(event: BehaviorEvent): void {
    if (!this.isRunning) return;
    this.buffer.enqueue(event);
  }

  /**
   * Manually flushes buffered events.
   */
  public async flush(): Promise<boolean> {
    return await this.buffer.flush();
  }

  /**
   * Stops telemetry listeners and closes the session.
   */
  public async stop(reason: string = 'USER_EXIT'): Promise<SessionEndResponse | null> {
    if (!this.isRunning) return null;

    this.isRunning = false;
    this.buffer.stopTimer();

    // Detach listeners
    this.mouseListener.detach();
    this.keyboardListener.detach();
    this.scrollListener.detach();
    this.navigationListener.detach();
    this.visibilityListener.detach();

    if (typeof window !== 'undefined') {
      window.removeEventListener('pagehide', this.handlePageHideBound);
      window.removeEventListener('beforeunload', this.handleBeforeUnloadBound);
    }

    // Final flush of remaining events
    await this.buffer.flush();

    const activeSessionId = this.sessionId;
    try {
      if (activeSessionId) {
        const res = await fetch(`${this.config.apiBaseUrl}/session/end`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: activeSessionId,
            end_reason: reason,
          }),
        });

        if (!res.ok) {
          throw new Error(`Failed to end session: HTTP ${res.status}`);
        }

        const result: SessionEndResponse = await res.json();
        this.log('Session ended successfully:', result);
        return result;
      }
      return null;
    } catch (err: unknown) {
      this.log('Session end error:', err);
      return null;
    } finally {
      this.sessionId = null;
      this.buffer.reset();
    }
  }

  public endSession(reason?: string): Promise<SessionEndResponse | null> {
    return this.stop(reason);
  }

  public getSessionId(): string | null {
    return this.sessionId;
  }

  public getStats(): TelemetryStats {
    return this.buffer.getStats(this.sessionId, this.isRunning);
  }

  private handlePageHide(): void {
    this.buffer.flushSyncBeacon();
  }

  private handleBeforeUnload(): void {
    this.buffer.flushSyncBeacon();
  }

  private log(...args: unknown[]): void {
    if (this.config.debug) {
      console.log('[BehavioralSDK]', ...args);
    }
  }
}
