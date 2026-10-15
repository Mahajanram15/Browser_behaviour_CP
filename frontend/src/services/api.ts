import {
  HealthResponse,
  DashboardStats,
  RiskResponse,
  ProductListResponse,
  ProductDetailResponse,
  SearchResponse,
  SearchFilterResponse,
  CatalogResponse,
  CartItemResponse,
  CheckoutVerifyResponse,
  ApiTelemetryRecord,
  DomainApiResult,
} from '../types';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/+$/, '');

// ------------------------------------------------------------------------------
// 1. Existing System Health & Dashboard API Client
// ------------------------------------------------------------------------------

export const apiClient = {
  async getHealth(): Promise<HealthResponse> {
    const res = await fetch('/health');
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  },

  async getDashboardStats(): Promise<DashboardStats> {
    const res = await fetch(`${API_BASE}/dashboard/stats`);
    if (!res.ok) throw new Error('Failed to fetch dashboard statistics');
    return res.json();
  },

  async getRiskScore(sessionId: string): Promise<RiskResponse> {
    const res = await fetch(`${API_BASE}/risk/${encodeURIComponent(sessionId)}`);
    if (!res.ok) throw new Error(`Failed to fetch risk score for session ${sessionId}`);
    return res.json();
  },
};


// ------------------------------------------------------------------------------
// 2. Instrumented Application Domain API Client (Experiment B)
// Captures timing and structural metadata for genuine application traffic.
// PRIVACY: Never stores query values, payload values, auth tokens, or PII.
// ------------------------------------------------------------------------------

export interface AppApiClientOptions {
  apiBase?: string;
  getSessionId?: () => string | null;
  onTelemetryEmitted?: (record: ApiTelemetryRecord) => void;
}

export interface AppApiClient {
  getProducts(params?: { category?: string; page?: number; page_size?: number }): Promise<DomainApiResult<ProductListResponse>>;
  getProductDetails(id: string): Promise<DomainApiResult<ProductDetailResponse>>;
  search(q: string, limit?: number): Promise<DomainApiResult<SearchResponse>>;
  filterSearch(filter: string, sort?: string): Promise<DomainApiResult<SearchFilterResponse>>;
  getCatalog(category?: string): Promise<DomainApiResult<CatalogResponse>>;
  addCartItem(itemId: string, quantity: number): Promise<DomainApiResult<CartItemResponse>>;
  verifyCheckout(shippingMethod: string, currency: string): Promise<DomainApiResult<CheckoutVerifyResponse>>;
}

/**
 * Creates an instrumented domain API client.
 * Calls application endpoints and emits privacy-preserving telemetry to POST /api/api-requests.
 */
export function createAppApiClient(options: AppApiClientOptions = {}): AppApiClient {
  const base = (options.apiBase || API_BASE).replace(/\/+$/, '');
  const getSessionId = options.getSessionId || (() => null);

  /**
   * Internal helper executing domain HTTP requests and logging sanitized telemetry.
   * Telemetry submission is strictly isolated to prevent recursive instrumentation loops.
   */
  async function executeDomainRequest<T>(
    method: 'GET' | 'POST',
    path: string,
    queryParams?: Record<string, any>,
    bodyPayload?: Record<string, any>
  ): Promise<DomainApiResult<T>> {
    // 1. Normalize endpoint path (without query parameters)
    const cleanPath = path.startsWith('/') ? path : `/${path}`;
    const endpointPath = cleanPath.startsWith('/api') ? cleanPath : `/api${cleanPath}`;

    // 2. Extract parameter names ONLY (privacy safeguard)
    const paramKeys = queryParams ? Object.keys(queryParams).sort() : [];

    // 3. Extract payload field names ONLY (privacy safeguard)
    const payloadKeys = bodyPayload ? Object.keys(bodyPayload).sort() : [];

    // 4. Construct request URL
    let fullUrl = `${base}${cleanPath}`;
    if (queryParams && Object.keys(queryParams).length > 0) {
      const searchParams = new URLSearchParams();
      for (const [k, v] of Object.entries(queryParams)) {
        if (v !== undefined && v !== null) {
          searchParams.append(k, String(v));
        }
      }
      const qs = searchParams.toString();
      if (qs) {
        fullUrl += `?${qs}`;
      }
    }

    // 5. Serialize request payload if POST
    let bodyStr: string | undefined = undefined;
    let requestSizeBytes = 0;
    if (bodyPayload && method === 'POST') {
      bodyStr = JSON.stringify(bodyPayload);
      requestSizeBytes = new Blob([bodyStr]).size;
    }

    // 6. Measure request duration
    const t0 = performance.now();
    const clientTimestamp = Date.now();
    let statusCode = 0;
    let responseSizeBytes = 0;
    let resultData: T | null = null;
    let resultError: Error | null = null;

    try {
      const headers: Record<string, string> = {};
      if (bodyStr) {
        headers['Content-Type'] = 'application/json';
      }

      const response = await fetch(fullUrl, {
        method,
        headers,
        body: bodyStr,
      });

      statusCode = response.status;

      // Extract response size safely if available
      const cl = response.headers.get('content-length');
      if (cl && !isNaN(parseInt(cl, 10))) {
        responseSizeBytes = parseInt(cl, 10);
      }

      const responseText = await response.text();
      if (!responseSizeBytes && responseText) {
        responseSizeBytes = new Blob([responseText]).size;
      }

      if (response.ok) {
        try {
          resultData = JSON.parse(responseText) as T;
        } catch {
          resultData = null;
        }
      } else {
        resultError = new Error(`Domain request to ${endpointPath} failed with HTTP ${statusCode}: ${responseText}`);
      }
    } catch (err: any) {
      statusCode = 0; // Network failure or dropped connection
      resultError = err instanceof Error ? err : new Error(String(err));
    } finally {
      const responseTimeMs = Math.round((performance.now() - t0) * 100) / 100;

      // 7. Emit API Telemetry ONLY if an active session is currently bound
      const activeSessionId = getSessionId();
      if (activeSessionId && activeSessionId.trim().length > 0) {
        const telemetryRecord: ApiTelemetryRecord = {
          session_id: activeSessionId,
          endpoint: endpointPath,
          http_method: method,
          status_code: statusCode,
          response_time_ms: responseTimeMs,
          request_size_bytes: requestSizeBytes,
          response_size_bytes: responseSizeBytes,
          headers_fingerprint: 'browser_fetch_v1',
          client_timestamp: clientTimestamp,
          param_keys: paramKeys,
          payload_keys: payloadKeys,
        };

        // Submit via direct fetch() to /api/api-requests (NON-RECURSIVE)
        sendTelemetryRecord(base, telemetryRecord)
          .then(() => {
            options.onTelemetryEmitted?.(telemetryRecord);
          })
          .catch((tErr) => {
            console.warn('[Telemetry] API access log emission failed:', tErr);
          });
      }
    }

    return {
      data: resultData,
      error: resultError,
      status: statusCode,
      responseTimeMs: Math.round((performance.now() - t0) * 100) / 100,
    };
  }

  return {
    async getProducts(params = {}) {
      return executeDomainRequest<ProductListResponse>('GET', '/products', params);
    },

    async getProductDetails(id: string) {
      return executeDomainRequest<ProductDetailResponse>('GET', '/products/details', { id });
    },

    async search(q: string, limit = 10) {
      return executeDomainRequest<SearchResponse>('GET', '/search', { q, limit });
    },

    async filterSearch(filter: string, sort = 'relevance') {
      return executeDomainRequest<SearchFilterResponse>('GET', '/search/filter', { filter, sort });
    },

    async getCatalog(category?: string) {
      return executeDomainRequest<CatalogResponse>('GET', '/catalog', category ? { category } : undefined);
    },

    async addCartItem(itemId: string, quantity = 1) {
      return executeDomainRequest<CartItemResponse>('POST', '/cart/items', undefined, {
        item_id: itemId,
        quantity,
      });
    },

    async verifyCheckout(shippingMethod = 'standard', currency = 'USD') {
      return executeDomainRequest<CheckoutVerifyResponse>('POST', '/checkout/verify', undefined, {
        shipping_method: shippingMethod,
        currency,
      });
    },
  };
}

/**
 * Direct non-recursive dispatcher to POST /api/api-requests.
 * NEVER passes through executeDomainRequest to avoid infinite loops.
 */
async function sendTelemetryRecord(apiBase: string, record: ApiTelemetryRecord): Promise<void> {
  const telemetryEndpoint = `${apiBase}/api-requests`;
  const res = await fetch(telemetryEndpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  });
  if (!res.ok) {
    throw new Error(`Telemetry ingestion failed with HTTP ${res.status}`);
  }
}
