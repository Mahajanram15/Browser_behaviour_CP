import test from 'node:test';
import assert from 'node:assert/strict';
import { EventBuffer } from '../dist/buffer.js';
import { MouseListener } from '../dist/listeners/mouse.js';
import { KeyboardListener } from '../dist/listeners/keyboard.js';
import { ScrollListener } from '../dist/listeners/scroll.js';
import { NavigationListener } from '../dist/listeners/navigation.js';
import { VisibilityListener } from '../dist/listeners/visibility.js';
import { BehavioralSDK } from '../dist/index.js';

test('1. EventBuffer: enqueues and flushes events correctly', async () => {
  const dispatchedBatches = [];

  globalThis.fetch = async (url, options) => {
    dispatchedBatches.push(JSON.parse(options.body));
    return {
      ok: true,
      status: 202,
      json: async () => ({ session_id: 'test_sess_1', processed_events: 2, status: 'INGESTED' }),
    };
  };

  const buffer = new EventBuffer({
    apiBaseUrl: 'http://localhost:8000/api',
    sessionIdGetter: () => 'test_sess_1',
    maxBatchSize: 3,
    debug: false,
  });

  buffer.enqueue({
    event_type: 'mouse_move',
    client_timestamp: Date.now(),
    event_data: { x: 100, y: 150, velocity_px_s: 20, acceleration_px_s2: 0, angle_degrees: 0, direction_change_deg: 0, distance_px: 10, time_delta_ms: 30 },
  });
  buffer.enqueue({
    event_type: 'mouse_click',
    client_timestamp: Date.now(),
    event_data: { x: 100, y: 150, button: 0, click_type: 'single', time_since_last_click_ms: 0, target_category: 'button' },
  });

  assert.equal(buffer.getStats('test_sess_1', true).eventsBuffered, 2);

  const flushed = await buffer.flush();
  assert.equal(flushed, true);
  assert.equal(dispatchedBatches.length, 1);
  assert.equal(dispatchedBatches[0].session_id, 'test_sess_1');
  assert.equal(dispatchedBatches[0].events.length, 2);
  assert.equal(buffer.getStats('test_sess_1', true).eventsBuffered, 0);
});

test('2. EventBuffer: network error resilience without application crash', async () => {
  globalThis.fetch = async () => {
    throw new Error('Network timeout (simulated)');
  };

  const buffer = new EventBuffer({
    apiBaseUrl: 'http://localhost:8000/api',
    sessionIdGetter: () => 'test_sess_fail',
    maxRetryBufferSize: 5,
    debug: false,
  });

  buffer.enqueue({
    event_type: 'scroll',
    client_timestamp: Date.now(),
    event_data: { scroll_x: 0, scroll_y: 50, delta_x: 0, delta_y: 50, velocity_px_s: 10, direction: 'down', time_since_last_scroll_ms: 0 },
  });

  const result = await buffer.flush();
  assert.equal(result, false);
  const stats = buffer.getStats('test_sess_fail', true);
  assert.equal(stats.eventsBuffered, 1);
  assert.match(stats.lastError, /Network timeout/);
});

test('3. Privacy Safeguard: Keyboard telemetry NEVER captures raw key characters, codes, or text values', async () => {
  const emittedEvents = [];
  const listener = new KeyboardListener({
    onEvent: (event) => emittedEvents.push(event),
  });

  const fakeKeyDownEvent = {
    key: 'MySecretPassword123',
    code: 'KeyP',
    keyCode: 80,
    ctrlKey: false,
    metaKey: false,
  };

  const fakeKeyUpEvent = {
    key: 'MySecretPassword123',
    code: 'KeyP',
    keyCode: 80,
  };

  listener['handleKeyDown'](fakeKeyDownEvent);
  await new Promise((r) => setTimeout(r, 20));
  listener['handleKeyUp'](fakeKeyUpEvent);

  assert.equal(emittedEvents.length, 1);
  const event = emittedEvents[0];
  assert.equal(event.event_type, 'key_meta');

  const payload = event.event_data;
  const serialized = JSON.stringify(event);

  // STRICT PRIVACY VERIFICATION:
  assert.equal(serialized.includes('MySecretPassword123'), false, 'FATAL: Raw key string leaked in telemetry!');
  assert.equal(serialized.includes('KeyP'), false, 'FATAL: Physical key code leaked in telemetry!');
  assert.equal('key' in payload, false, 'FATAL: Payload must not have "key" property!');
  assert.equal('code' in payload, false, 'FATAL: Payload must not have "code" property!');
  assert.equal('value' in payload, false, 'FATAL: Payload must not have "value" property!');
  assert.equal('character' in payload, false, 'FATAL: Payload must not have "character" property!');
  assert.equal('char' in payload, false, 'FATAL: Payload must not have "char" property!');

  // Validate allowed behavioral timing properties
  assert.equal(typeof payload.dwell_ms, 'number');
  assert.equal(typeof payload.flight_ms, 'number');
  assert.equal(typeof payload.inter_key_interval_ms, 'number');
  assert.equal(typeof payload.is_backspace, 'boolean');
  assert.equal(typeof payload.is_paste, 'boolean');
});

test('4. Mouse dynamics: correctly calculates velocity, acceleration, and angle', () => {
  const events = [];
  const mouseListener = new MouseListener({
    sampleRateHz: 60,
    onEvent: (e) => events.push(e),
  });

  mouseListener['handleMouseMove']({ clientX: 0, clientY: 0 });
  mouseListener['lastMoveTime'] = Date.now() - 100;
  mouseListener['lastX'] = 0;
  mouseListener['lastY'] = 0;
  mouseListener['handleMouseMove']({ clientX: 30, clientY: 40 });

  assert.equal(events.length, 2);
  const moveEvent = events[1];
  assert.equal(moveEvent.event_type, 'mouse_move');
  assert.equal(moveEvent.event_data.x, 30);
  assert.equal(moveEvent.event_data.y, 40);
  assert.equal(moveEvent.event_data.distance_px, 50);
  assert.ok(moveEvent.event_data.velocity_px_s > 0);
  assert.ok(moveEvent.event_data.angle_degrees > 0);
});

test('5. BehavioralSDK: start and stop lifecycle execution', async () => {
  globalThis.fetch = async (url) => {
    if (url.includes('/session/start')) {
      return {
        ok: true,
        json: async () => ({
          session_id: 'sess_sdk_test_100',
          status: 'ACTIVE',
          start_time: new Date().toISOString(),
          config: { batch_interval_ms: 1500, sampling_rate_mouse_hz: 30 },
        }),
      };
    }
    if (url.includes('/behavior/events')) {
      return {
        ok: true,
        status: 202,
        json: async () => ({ session_id: 'sess_sdk_test_100', processed_events: 1, status: 'INGESTED' }),
      };
    }
    if (url.includes('/session/end')) {
      return {
        ok: true,
        json: async () => ({
          session_id: 'sess_sdk_test_100',
          status: 'COMPLETED',
          duration_seconds: 5.2,
          total_events_captured: 12,
          final_integrity_score: 0.12,
        }),
      };
    }
    return { ok: true, json: async () => ({}) };
  };

  const sdk = new BehavioralSDK({
    apiBaseUrl: 'http://localhost:8000/api',
    debug: false,
  });

  await sdk.start();
  const sessionId = sdk.getSessionId();
  assert.equal(sessionId, 'sess_sdk_test_100');

  const stats = sdk.getStats();
  assert.equal(stats.sessionId, 'sess_sdk_test_100');
  assert.equal(stats.isRunning, true);

  const endResult = await sdk.stop('USER_EXIT');
  assert.equal(endResult.status, 'COMPLETED');
  assert.equal(sdk.getSessionId(), null);
  assert.equal(sdk.getStats().sessionId, null);
  assert.equal(sdk.getStats().isRunning, false);
});

test('6. Sequential session lifecycle: single SDK instance resets session ID and creates unique session on restart', async () => {
  let sessionCounter = 0;
  const createdSessions = [];
  const endedSessions = [];
  const ingestedBatches = [];

  globalThis.fetch = async (url, options) => {
    if (url.includes('/session/start')) {
      sessionCounter++;
      const sessId = `sess_seq_${sessionCounter}`;
      createdSessions.push(sessId);
      return {
        ok: true,
        json: async () => ({
          session_id: sessId,
          status: 'ACTIVE',
          start_time: new Date().toISOString(),
          config: { batch_interval_ms: 1500, sampling_rate_mouse_hz: 30 },
        }),
      };
    }
    if (url.includes('/behavior/events')) {
      const payload = JSON.parse(options.body);
      ingestedBatches.push(payload);
      return {
        ok: true,
        status: 202,
        json: async () => ({ session_id: payload.session_id, processed_events: payload.events.length, status: 'INGESTED' }),
      };
    }
    if (url.includes('/session/end')) {
      const payload = JSON.parse(options.body);
      endedSessions.push(payload.session_id);
      return {
        ok: true,
        json: async () => ({
          session_id: payload.session_id,
          status: 'COMPLETED',
          duration_seconds: 3.5,
          total_events_captured: 1,
          final_integrity_score: 0.15,
        }),
      };
    }
    return { ok: true, json: async () => ({}) };
  };

  const sdk = new BehavioralSDK({
    apiBaseUrl: 'http://localhost:8000/api',
    debug: false,
  });

  // --- Session 1 ---
  await sdk.start({ collectionMode: 'HUMAN', participantId: 'p_01', taskId: 'TASK_01', label: 0 });
  const session1 = sdk.getSessionId();
  assert.equal(session1, 'sess_seq_1');
  assert.equal(sdk.getStats().sessionId, 'sess_seq_1');
  assert.equal(sdk.getStats().isRunning, true);

  sdk.recordEvent({
    event_type: 'mouse_click',
    client_timestamp: Date.now(),
    event_data: { x: 10, y: 20, button: 0, click_type: 'single', time_since_last_click_ms: 0, target_category: 'button' },
  });

  const endResult1 = await sdk.stop('USER_EXIT');
  assert.equal(endResult1.status, 'COMPLETED');
  assert.equal(sdk.getSessionId(), null);
  assert.equal(sdk.getStats().sessionId, null);
  assert.equal(sdk.getStats().isRunning, false);
  assert.equal(sdk.getStats().eventsCollected, 0); // buffer counters reset

  // --- Session 2 (sequential on SAME sdk instance) ---
  await sdk.start({ collectionMode: 'HUMAN', participantId: 'p_01', taskId: 'TASK_02', label: 0 });
  const session2 = sdk.getSessionId();
  assert.equal(session2, 'sess_seq_2');
  assert.notEqual(session1, session2, 'FATAL: Session 2 reused Session 1 ID!');
  assert.equal(sdk.getStats().sessionId, 'sess_seq_2');
  assert.equal(sdk.getStats().isRunning, true);

  sdk.recordEvent({
    event_type: 'mouse_click',
    client_timestamp: Date.now(),
    event_data: { x: 50, y: 60, button: 0, click_type: 'single', time_since_last_click_ms: 0, target_category: 'link' },
  });

  const endResult2 = await sdk.stop('USER_EXIT');
  assert.equal(endResult2.status, 'COMPLETED');
  assert.equal(sdk.getSessionId(), null);
  assert.equal(sdk.getStats().sessionId, null);
  assert.equal(sdk.getStats().isRunning, false);

  // Assert API calls
  assert.deepEqual(createdSessions, ['sess_seq_1', 'sess_seq_2']);
  assert.deepEqual(endedSessions, ['sess_seq_1', 'sess_seq_2']);
  assert.equal(ingestedBatches.length, 2);
  assert.equal(ingestedBatches[0].session_id, 'sess_seq_1');
  assert.equal(ingestedBatches[1].session_id, 'sess_seq_2');
});

test('7. Duplicate session prevention: startSession() followed by start() reuses bound session ID', async () => {
  let sessionCounter = 0;
  const createdSessions = [];

  globalThis.fetch = async (url) => {
    if (url.includes('/session/start')) {
      sessionCounter++;
      const sessId = `sess_dup_check_${sessionCounter}`;
      createdSessions.push(sessId);
      return {
        ok: true,
        json: async () => ({
          session_id: sessId,
          status: 'ACTIVE',
          start_time: new Date().toISOString(),
        }),
      };
    }
    if (url.includes('/session/end')) {
      return {
        ok: true,
        json: async () => ({ session_id: 'test', status: 'COMPLETED' }),
      };
    }
    return { ok: true, json: async () => ({}) };
  };

  const sdk = new BehavioralSDK({
    apiBaseUrl: 'http://localhost:8000/api',
    debug: false,
  });

  // Call startSession then start
  const sId1 = await sdk.startSession({ collectionMode: 'AUTOMATED', taskId: 'TASK_LEARN_AUTOMATION', label: 1 });
  assert.equal(sId1, 'sess_dup_check_1');
  assert.equal(sdk.getSessionId(), 'sess_dup_check_1');

  // Starting when already bound should NOT issue a second POST /session/start
  await sdk.start({ collectionMode: 'AUTOMATED', taskId: 'TASK_LEARN_AUTOMATION', label: 1 });
  assert.equal(sdk.getSessionId(), 'sess_dup_check_1');
  assert.deepEqual(createdSessions, ['sess_dup_check_1'], 'Must only create ONE session on backend');

  await sdk.stop('SIMULATION_DONE');
  assert.equal(sdk.getSessionId(), null);

  // Subsequent start after stop creates fresh session
  await sdk.start({ collectionMode: 'AUTOMATED', taskId: 'TASK_LEARN_AUTOMATION', label: 1 });
  assert.equal(sdk.getSessionId(), 'sess_dup_check_2');
  assert.deepEqual(createdSessions, ['sess_dup_check_1', 'sess_dup_check_2']);

  await sdk.stop('CLEANUP');
});

test('8. Synthetic-only mode: excludes physical DOM mouse events while accepting explicit synthetic events', async () => {
  const ingestedBatches = [];

  globalThis.fetch = async (url, options) => {
    if (url.includes('/session/start')) {
      return {
        ok: true,
        json: async () => ({
          session_id: 'sess_synth_iso_1',
          status: 'ACTIVE',
          start_time: new Date().toISOString(),
          config: { batch_interval_ms: 1500, sampling_rate_mouse_hz: 30 },
        }),
      };
    }
    if (url.includes('/behavior/events')) {
      const payload = JSON.parse(options.body);
      ingestedBatches.push(payload);
      return {
        ok: true,
        status: 202,
        json: async () => ({ session_id: payload.session_id, processed_events: payload.events.length, status: 'INGESTED' }),
      };
    }
    if (url.includes('/session/end')) {
      return {
        ok: true,
        json: async () => ({ session_id: 'sess_synth_iso_1', status: 'COMPLETED', duration_seconds: 2.0, total_events_captured: 1 }),
      };
    }
    return { ok: true, json: async () => ({}) };
  };

  const sdk = new BehavioralSDK({
    apiBaseUrl: 'http://localhost:8000/api',
    debug: false,
  });

  // Start in synthetic-only mode
  await sdk.start({
    collectionMode: 'AUTOMATED',
    automationCondition: 'AUTOMATED_DETERMINISTIC',
    taskId: 'TASK_LEARN_AUTOMATION',
    label: 1,
    syntheticOnly: true,
  });

  assert.equal(sdk.isSyntheticOnly(), true, 'SDK must report isSyntheticOnly() = true');

  // Attempt to feed physical DOM mouse movement events
  sdk['mouseListener']['handleMouseMove']({ clientX: 100, clientY: 100 });
  sdk['mouseListener']['lastMoveTime'] = Date.now() - 100;
  sdk['mouseListener']['handleMouseMove']({ clientX: 200, clientY: 200 });

  // Verify that physical DOM events are completely excluded from buffer
  assert.equal(sdk.getStats().eventsBuffered, 0, 'Physical DOM mouse events must NOT enter synthetic session buffer');

  // Explicitly inject a synthetic event via recordEvent
  sdk.recordEvent({
    event_type: 'mouse_move',
    client_timestamp: Date.now(),
    event_data: {
      x: 120,
      y: 180,
      distance_px: 32.0,
      time_delta_ms: 33,
      velocity_px_s: 960.0,
      acceleration_px_s2: 0.0,
      angle_degrees: 38.6,
      direction_change_deg: 0.0,
    },
  });

  // Explicit synthetic event must be accepted
  assert.equal(sdk.getStats().eventsBuffered, 1, 'Explicit synthetic events must be accepted');

  await sdk.stop('SYNTHETIC_TEST_COMPLETED');
  assert.equal(sdk.getSessionId(), null);
  assert.equal(sdk.isSyntheticOnly(), false, 'syntheticOnly must reset on session end');
});

test('9. Lifecycle isolation: stopping a synthetic-only session restores normal physical telemetry collection', async () => {
  globalThis.fetch = async (url) => {
    if (url.includes('/session/start')) {
      return {
        ok: true,
        json: async () => ({
          session_id: 'sess_lifecycle_iso_2',
          status: 'ACTIVE',
          start_time: new Date().toISOString(),
          config: { batch_interval_ms: 1500, sampling_rate_mouse_hz: 30 },
        }),
      };
    }
    if (url.includes('/session/end')) {
      return {
        ok: true,
        json: async () => ({ session_id: 'sess_lifecycle_iso_2', status: 'COMPLETED' }),
      };
    }
    return { ok: true, json: async () => ({}) };
  };

  const sdk = new BehavioralSDK({
    apiBaseUrl: 'http://localhost:8000/api',
    debug: false,
  });

  // Session 1: Synthetic
  await sdk.start({
    collectionMode: 'AUTOMATED',
    automationCondition: 'AUTOMATED_DETERMINISTIC',
    syntheticOnly: true,
  });
  assert.equal(sdk.isSyntheticOnly(), true);

  // Stop session 1
  await sdk.stop('BOT_DONE');
  assert.equal(sdk.isSyntheticOnly(), false, 'syntheticOnly must reset after stop()');

  // Session 2: Human session (normal mode)
  await sdk.start({
    collectionMode: 'HUMAN',
    label: 0,
  });
  assert.equal(sdk.isSyntheticOnly(), false, 'Normal human session must NOT inherit syntheticOnly');

  // In normal mode, physical DOM events must be accepted
  sdk['mouseListener']['handleMouseMove']({ clientX: 10, clientY: 20 });
  sdk['mouseListener']['lastMoveTime'] = Date.now() - 100;
  sdk['mouseListener']['handleMouseMove']({ clientX: 40, clientY: 60 });

  assert.ok(sdk.getStats().eventsBuffered > 0, 'Normal human session must collect physical mouse events');

  await sdk.stop('USER_EXIT');
});

test('10. Event listener attachment guard: DOM listeners are not attached during synthetic-only mode and cleaned up on stop', async () => {
  const addedListeners = [];
  const removedListeners = [];

  const originalWindow = globalThis.window;
  const originalDocument = globalThis.document;

  globalThis.document = {
    referrer: '',
    addEventListener: (type) => addedListeners.push(type),
    removeEventListener: (type) => removedListeners.push(type),
  };

  globalThis.window = {
    addEventListener: (type) => addedListeners.push(type),
    removeEventListener: (type) => removedListeners.push(type),
    screen: { width: 1920, height: 1080 },
    location: { pathname: '/test', href: 'http://localhost/test' },
    history: { pushState: () => {}, replaceState: () => {} },
    setTimeout: (...args) => globalThis.setTimeout(...args),
    clearTimeout: (...args) => globalThis.clearTimeout(...args),
    setInterval: (...args) => globalThis.setInterval(...args),
    clearInterval: (...args) => globalThis.clearInterval(...args),
  };

  try {
    globalThis.fetch = async (url) => {
      if (url.includes('/session/start')) {
        return {
          ok: true,
          json: async () => ({
            session_id: 'sess_listener_check',
            status: 'ACTIVE',
            start_time: new Date().toISOString(),
          }),
        };
      }
      if (url.includes('/session/end')) {
        return {
          ok: true,
          json: async () => ({ session_id: 'sess_listener_check', status: 'COMPLETED' }),
        };
      }
      return { ok: true, json: async () => ({}) };
    };

    const sdk = new BehavioralSDK({
      apiBaseUrl: 'http://localhost:8000/api',
      debug: false,
    });

    // 1. Synthetic session: verify mousemove/click listeners are NOT attached
    await sdk.start({
      collectionMode: 'AUTOMATED',
      syntheticOnly: true,
    });

    assert.equal(addedListeners.includes('mousemove'), false, 'mousemove listener must NOT be attached in synthetic-only mode');
    assert.equal(addedListeners.includes('click'), false, 'click listener must NOT be attached in synthetic-only mode');
    assert.equal(addedListeners.includes('keydown'), false, 'keydown listener must NOT be attached in synthetic-only mode');
    assert.equal(addedListeners.includes('scroll'), false, 'scroll listener must NOT be attached in synthetic-only mode');

    await sdk.stop('SYNTH_END');

    // 2. Normal human session: verify mousemove/click listeners ARE attached
    addedListeners.length = 0;
    await sdk.start({
      collectionMode: 'HUMAN',
    });

    assert.equal(addedListeners.includes('mousemove'), true, 'mousemove listener MUST be attached in normal mode');
    assert.equal(addedListeners.includes('click'), true, 'click listener MUST be attached in normal mode');
    assert.equal(addedListeners.includes('keydown'), true, 'keydown listener MUST be attached in normal mode');
    assert.equal(addedListeners.includes('scroll'), true, 'scroll listener MUST be attached in normal mode');

    // Stop and verify cleanup
    await sdk.stop('HUMAN_END');
    assert.equal(removedListeners.includes('mousemove'), true, 'mousemove listener MUST be removed on stop');
    assert.equal(removedListeners.includes('click'), true, 'click listener MUST be removed on stop');
    assert.equal(removedListeners.includes('keydown'), true, 'keydown listener MUST be removed on stop');
    assert.equal(removedListeners.includes('scroll'), true, 'scroll listener MUST be removed on stop');
  } finally {
    globalThis.window = originalWindow;
    globalThis.document = originalDocument;
  }
});

