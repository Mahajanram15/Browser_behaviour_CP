import { BehaviorEvent, MouseMovePayload, MouseClickPayload, TargetCategory } from '../types.js';

export interface MouseListenerOptions {
  sampleRateHz?: number; // e.g. 25-30Hz
  onEvent: (event: BehaviorEvent) => void;
}

export class MouseListener {
  private sampleIntervalMs: number;
  private onEvent: (event: BehaviorEvent) => void;
  private isListening = false;

  // Movement tracking state
  private lastMoveTime = 0;
  private lastX = 0;
  private lastY = 0;
  private lastVelocity = 0;
  private lastAngle = 0;

  // Click tracking state
  private lastClickTime = 0;
  private clickTimer: number | null = null;
  private clickCount = 0;

  // Bound event handlers
  private handleMouseMoveBound = this.handleMouseMove.bind(this);
  private handleClickBound = this.handleClick.bind(this);

  constructor(options: MouseListenerOptions) {
    const rate = options.sampleRateHz ?? 30;
    this.sampleIntervalMs = Math.max(16, Math.floor(1000 / rate)); // e.g. ~33ms for 30Hz
    this.onEvent = options.onEvent;
  }

  public attach(): void {
    if (this.isListening || typeof window === 'undefined') return;

    window.addEventListener('mousemove', this.handleMouseMoveBound, { passive: true });
    window.addEventListener('click', this.handleClickBound, { passive: true });
    window.addEventListener('contextmenu', this.handleClickBound, { passive: true });
    this.isListening = true;
  }

  public detach(): void {
    if (!this.isListening || typeof window === 'undefined') return;

    window.removeEventListener('mousemove', this.handleMouseMoveBound);
    window.removeEventListener('click', this.handleClickBound);
    window.removeEventListener('contextmenu', this.handleClickBound);

    if (this.clickTimer !== null) {
      window.clearTimeout(this.clickTimer);
      this.clickTimer = null;
    }
    this.isListening = false;
  }

  private handleMouseMove(e: MouseEvent): void {
    const now = Date.now();
    const timeDeltaMs = this.lastMoveTime > 0 ? now - this.lastMoveTime : 0;

    // Apply sampling/throttling to keep rate within 20-30Hz maximum
    if (this.lastMoveTime > 0 && timeDeltaMs < this.sampleIntervalMs) {
      return;
    }

    const currentX = e.clientX;
    const currentY = e.clientY;

    let distance = 0;
    let velocity = 0;
    let acceleration = 0;
    let angleDegrees = 0;
    let directionChangeDeg = 0;

    if (this.lastMoveTime > 0 && timeDeltaMs > 0) {
      const dx = currentX - this.lastX;
      const dy = currentY - this.lastY;
      distance = Math.sqrt(dx * dx + dy * dy);
      const dtSeconds = timeDeltaMs / 1000;
      velocity = distance / dtSeconds;
      acceleration = (velocity - this.lastVelocity) / dtSeconds;

      angleDegrees = (Math.atan2(dy, dx) * 180) / Math.PI;
      directionChangeDeg = Math.abs(angleDegrees - this.lastAngle);
      if (directionChangeDeg > 180) {
        directionChangeDeg = 360 - directionChangeDeg;
      }
    }

    const payload: MouseMovePayload = {
      x: Math.round(currentX),
      y: Math.round(currentY),
      distance_px: Math.round(distance * 10) / 10,
      time_delta_ms: timeDeltaMs,
      velocity_px_s: Math.round(velocity * 10) / 10,
      acceleration_px_s2: Math.round(acceleration * 10) / 10,
      angle_degrees: Math.round(angleDegrees * 10) / 10,
      direction_change_deg: Math.round(directionChangeDeg * 10) / 10,
    };

    this.lastMoveTime = now;
    this.lastX = currentX;
    this.lastY = currentY;
    this.lastVelocity = velocity;
    this.lastAngle = angleDegrees;

    this.onEvent({
      event_type: 'mouse_move',
      client_timestamp: now,
      event_data: payload,
    });
  }

  private handleClick(e: MouseEvent): void {
    const now = Date.now();
    const timeSinceLastClickMs = this.lastClickTime > 0 ? now - this.lastClickTime : 0;
    this.lastClickTime = now;

    this.clickCount++;
    const isDoubleClick = this.clickCount >= 2 && timeSinceLastClickMs < 400;

    if (this.clickTimer !== null) {
      window.clearTimeout(this.clickTimer);
    }

    this.clickTimer = window.setTimeout(() => {
      this.clickCount = 0;
      this.clickTimer = null;
    }, 400);

    const targetCategory = this.classifyElement(e.target as HTMLElement | null);

    const payload: MouseClickPayload = {
      x: Math.round(e.clientX),
      y: Math.round(e.clientY),
      button: e.button,
      click_type: isDoubleClick ? 'double' : 'single',
      time_since_last_click_ms: timeSinceLastClickMs,
      target_category: targetCategory,
    };

    this.onEvent({
      event_type: 'mouse_click',
      client_timestamp: now,
      event_data: payload,
    });
  }

  private classifyElement(el: HTMLElement | null): TargetCategory {
    if (!el || typeof el.tagName !== 'string') return 'other';

    const tag = el.tagName.toLowerCase();
    if (tag === 'button' || el.getAttribute('role') === 'button') return 'button';
    if (tag === 'a') return 'link';
    if (tag === 'input' || tag === 'textarea') return 'input';
    if (tag === 'select' || tag === 'option') return 'select';
    if (tag === 'canvas' || tag === 'svg') return 'canvas';

    return 'other';
  }
}
