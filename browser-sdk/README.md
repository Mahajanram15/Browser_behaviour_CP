# @behavioral-integrity/sdk

Client-side TypeScript Behavioral Telemetry SDK for the **Browser-to-Backend Behavioral Integrity Verification System**.

## Key Privacy Guarantees

- **NO Keystroke Logging**: Only inter-key flight times and dwell durations are collected. Key identity (`event.key` / `event.code`) is discarded at listener invocation.
- **NO Form Field Scraping**: Input values, search queries, passwords, and form bodies are strictly ignored.
- **Micro-batching**: Emits throttled JSON batches over standard HTTPS transport to minimize client CPU and network footprint.

## Quick Start (Preview)

```typescript
import { BehavioralSDK } from '@behavioral-integrity/sdk';

const sdk = new BehavioralSDK({
  apiBaseUrl: 'http://localhost:8000/api',
  batchIntervalMs: 2000,
  debug: true,
});

// Initialize session and start telemetry capture
await sdk.start();
```
