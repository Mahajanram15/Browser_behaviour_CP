import { BehaviorEvent, NavigationPayload } from '../types.js';

export interface NavigationListenerOptions {
  onEvent: (event: BehaviorEvent) => void;
}

export class NavigationListener {
  private onEvent: (event: BehaviorEvent) => void;
  private isListening = false;

  private lastNavTime = 0;
  private lastPath = '';
  private sequenceNumber = 0;

  private handlePopStateBound = this.handleLocationChange.bind(this);
  private handleHashChangeBound = this.handleLocationChange.bind(this);

  private originalPushState: typeof window.history.pushState | null = null;
  private originalReplaceState: typeof window.history.replaceState | null = null;

  constructor(options: NavigationListenerOptions) {
    this.onEvent = options.onEvent;
  }

  public attach(): void {
    if (this.isListening || typeof window === 'undefined') return;

    this.lastNavTime = Date.now();
    this.lastPath = this.getSanitizedPath(window.location.pathname);

    this.recordNavigation(this.lastPath, this.getSanitizedPath(document.referrer));

    window.addEventListener('popstate', this.handlePopStateBound);
    window.addEventListener('hashchange', this.handleHashChangeBound);

    if (window.history) {
      this.originalPushState = window.history.pushState;
      this.originalReplaceState = window.history.replaceState;

      const self = this;
      window.history.pushState = function (...args) {
        const result = self.originalPushState?.apply(this, args);
        self.handleLocationChange();
        return result;
      };

      window.history.replaceState = function (...args) {
        const result = self.originalReplaceState?.apply(this, args);
        self.handleLocationChange();
        return result;
      };
    }

    this.isListening = true;
  }

  public detach(): void {
    if (!this.isListening || typeof window === 'undefined') return;

    window.removeEventListener('popstate', this.handlePopStateBound);
    window.removeEventListener('hashchange', this.handleHashChangeBound);

    if (this.originalPushState) {
      window.history.pushState = this.originalPushState;
      this.originalPushState = null;
    }
    if (this.originalReplaceState) {
      window.history.replaceState = this.originalReplaceState;
      this.originalReplaceState = null;
    }

    this.isListening = false;
  }

  private handleLocationChange(): void {
    if (typeof window === 'undefined') return;

    const currentPath = this.getSanitizedPath(window.location.pathname);
    if (currentPath === this.lastPath) return;

    this.recordNavigation(currentPath, this.lastPath);
    this.lastPath = currentPath;
  }

  private recordNavigation(path: string, referrer: string): void {
    const now = Date.now();
    const dwellTimeMs = this.lastNavTime > 0 ? now - this.lastNavTime : 0;
    this.sequenceNumber++;
    this.lastNavTime = now;

    const payload: NavigationPayload = {
      path,
      referrer,
      dwell_time_ms: dwellTimeMs,
      sequence_number: this.sequenceNumber,
    };

    this.onEvent({
      event_type: 'navigation',
      client_timestamp: now,
      event_data: payload,
    });
  }

  private getSanitizedPath(rawPathOrUrl: string): string {
    if (!rawPathOrUrl) return '/';
    try {
      if (rawPathOrUrl.startsWith('http://') || rawPathOrUrl.startsWith('https://')) {
        const parsed = new URL(rawPathOrUrl);
        return parsed.pathname || '/';
      }
      return rawPathOrUrl.split('?')[0].split('#')[0] || '/';
    } catch {
      return rawPathOrUrl.split('?')[0].split('#')[0] || '/';
    }
  }
}
