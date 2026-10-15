import React, { useState, useEffect, useMemo } from 'react';
import { MousePointer, Key, ArrowUpDown, Compass, Check, Bot, User, ListChecks, Download, Activity, AlertCircle } from 'lucide-react';
import { BehavioralSDK, TelemetryStats } from '@behavioral-integrity/sdk';
import { TelemetryStatusPanel } from '../components/TelemetryStatusPanel';
import { createAppApiClient } from '../services/api';
import { ApiTelemetryRecord } from '../types';

interface TelemetryDemoPageProps {
  sdk: BehavioralSDK;
  stats: TelemetryStats;
  onRefreshStats: () => void;
}

interface TaskInstruction {
  name: string;
  description: string;
  steps: string[];
}

const TASK_INSTRUCTIONS: Record<string, TaskInstruction> = {
  TASK_01: {
    name: "Catalog Browsing & Product Inspection",
    description: "Navigate to the catalog, inspect product cards, scroll specifications, and return home.",
    steps: [
      "1. Move cursor across the Mouse Telemetry Zone to simulate pointer navigation.",
      "2. Click the 'Catalog Route' navigation button below.",
      "3. Scroll inside the Scrollable Test Viewport.",
      "4. Click on 'Standard Button' to simulate inspecting a product card.",
      "5. Click 'Landing Route' to return home."
    ]
  },
  TASK_02: {
    name: "Search & Query Filtering",
    description: "Focus search, type a non-sensitive query, inspect results, and scroll through listings.",
    steps: [
      "1. Click inside the Interactive Typing Sandbox to focus.",
      "2. Type a non-sensitive query (e.g. 'laptop filter 16gb').",
      "3. Scroll inside the Scrollable Viewport to review results.",
      "4. Click 'Anchor Link' to inspect a result item."
    ]
  },
  TASK_03: {
    name: "Multi-Page Exploration & Form Interaction",
    description: "Traverse multiple application routes, perform clicks, test keyboard cadences, and include natural pauses.",
    steps: [
      "1. Navigate across all 4 route buttons below (landing -> catalog -> cart -> checkout).",
      "2. Perform several clicks on button and dropdown elements.",
      "3. Scroll up and down inside the scroll zone.",
      "4. Type naturally in the sandbox with realistic pause intervals."
    ]
  }
};

export const TelemetryDemoPage: React.FC<TelemetryDemoPageProps> = ({
  sdk,
  stats,
  onRefreshStats,
}) => {
  const [loading, setLoading] = useState(false);
  const [collectionMode, setCollectionMode] = useState<'HUMAN' | 'AUTOMATED'>('HUMAN');
  const [automationCondition, setAutomationCondition] = useState<'AUTOMATED_DETERMINISTIC' | 'AUTOMATED_VARIABLE'>('AUTOMATED_DETERMINISTIC');
  const [participantId, setParticipantId] = useState<string>('p_01');
  const [selectedTask, setSelectedTask] = useState<string>('TASK_01');
  const [clickCount, setClickCount] = useState(0);
  const [lastClickedCategory, setLastClickedCategory] = useState<string>('None');
  const [activeRoute, setActiveRoute] = useState<string>('/demo/landing');
  const [demoTextInput, setDemoTextInput] = useState<string>('');
  const [exportNotice, setExportNotice] = useState<string | null>(null);

  // Live Observed API Telemetry State (Experiment B)
  const [lastApiTelemetry, setLastApiTelemetry] = useState<ApiTelemetryRecord | null>(null);
  const [apiActivityLog, setApiActivityLog] = useState<string[]>([]);
  const [apiError, setApiError] = useState<string | null>(null);

  // Initialize explicit domain API client with active SDK session binding
  const appClient = useMemo(() => {
    return createAppApiClient({
      getSessionId: () => sdk.getSessionId(),
      onTelemetryEmitted: (rec) => {
        setLastApiTelemetry(rec);
        const logEntry = `[${rec.http_method}] ${rec.endpoint} (${rec.status_code}) - ${rec.response_time_ms}ms`;
        setApiActivityLog((prev) => [logEntry, ...prev.slice(0, 3)]);
        onRefreshStats();
      },
    });
  }, [sdk, onRefreshStats]);

  // TASK_02: Debounced search triggering when typing query in sandbox (500ms delay)
  useEffect(() => {
    if (selectedTask !== 'TASK_02' || !demoTextInput.trim() || demoTextInput.trim().length < 2) return;
    const timer = setTimeout(async () => {
      const res = await appClient.search(demoTextInput.trim(), 5);
      if (res.error) {
        setApiError(res.error.message);
      } else {
        setApiError(null);
      }
    }, 500);
    return () => clearTimeout(timer);
  }, [demoTextInput, selectedTask, appClient]);

  const handleStart = async () => {
    setLoading(true);
    setExportNotice(null);
    setClickCount(0);
    setDemoTextInput('');
    setLastClickedCategory('None');
    setLastApiTelemetry(null);
    setApiActivityLog([]);
    setApiError(null);
    try {
      await sdk.start({
        collectionMode,
        automationCondition: collectionMode === 'AUTOMATED' ? automationCondition : 'NONE',
        participantId: participantId.trim() || (collectionMode === 'HUMAN' ? 'p_01' : automationCondition === 'AUTOMATED_VARIABLE' ? 'bot_var' : 'bot_det'),
        taskId: selectedTask,
        label: collectionMode === 'HUMAN' ? 0 : 1,
      });
      onRefreshStats();
    } catch (err) {
      console.error('Failed to start SDK:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await sdk.stop(`${collectionMode}_${selectedTask}_COMPLETED`);
      onRefreshStats();
    } catch (err) {
      console.error('Failed to stop SDK:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleFlush = async () => {
    setLoading(true);
    try {
      await sdk.flush();
      onRefreshStats();
    } catch (err) {
      console.error('Failed to flush buffer:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulatedNavigation = async (route: string) => {
    setActiveRoute(route);
    if (typeof window !== 'undefined' && window.history) {
      window.history.pushState({}, '', route);
    }
    onRefreshStats();

    // Trigger task-appropriate application API endpoint
    try {
      if (route === '/demo/catalog') {
        if (selectedTask === 'TASK_01') {
          await appClient.getProducts({ category: 'laptops', page: 1 });
        } else if (selectedTask === 'TASK_03') {
          await appClient.getCatalog('laptops');
        }
      } else if (route === '/demo/landing') {
        await appClient.getCatalog();
      } else if (route === '/demo/cart') {
        if (selectedTask === 'TASK_03') {
          await appClient.addCartItem('prod_01', 1);
        }
      } else if (route === '/demo/checkout') {
        if (selectedTask === 'TASK_03') {
          await appClient.verifyCheckout('express', 'USD');
        }
      }
    } catch (err: any) {
      setApiError(err.message || 'API call failed');
    }
  };

  const handleStandardButtonClick = async () => {
    setClickCount((c) => c + 1);
    setLastClickedCategory('button');
    onRefreshStats();

    if (selectedTask === 'TASK_01') {
      await appClient.getProductDetails('prod_01');
    } else if (selectedTask === 'TASK_03') {
      await appClient.addCartItem('prod_02', 1);
    }
  };

  const handleAnchorLinkClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    setClickCount((c) => c + 1);
    setLastClickedCategory('link');
    onRefreshStats();

    if (selectedTask === 'TASK_02') {
      await appClient.filterSearch('peripherals', 'price_asc');
    }
  };

  const handleSelectChange = async (opt: string) => {
    setClickCount((c) => c + 1);
    setLastClickedCategory('select');
    onRefreshStats();

    if (selectedTask === 'TASK_02') {
      const sort = opt === 'opt2' ? 'rating' : 'price_desc';
      await appClient.filterSearch('monitors', sort);
    }
  };

  const handleExportDataset = async () => {
    try {
      const res = await fetch('/api/dataset/export', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setExportNotice(`Exported ${data.usable_sessions} sessions to ml/data/features.csv and ml/data/metadata.csv`);
      }
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  // Run automated bot simulation directly in the browser
  const handleRunAutomatedSimulation = async () => {
    setLoading(true);
    setExportNotice(null);
    try {
      // 1. Start automated session
      await sdk.start({
        collectionMode: 'AUTOMATED',
        automationCondition: automationCondition,
        participantId: participantId.trim() || (automationCondition === 'AUTOMATED_VARIABLE' ? 'bot_sim_var' : 'bot_sim_det'),
        taskId: selectedTask,
        label: 1,
      });
      onRefreshStats();

      const baseT = Date.now();
      const isVariable = automationCondition === 'AUTOMATED_VARIABLE';

      // 2. Synthesize mouse trajectory
      if (!isVariable) {
        for (let i = 0; i < 15; i++) {
          sdk.recordEvent({
            event_type: 'mouse_move',
            client_timestamp: baseT + i * 33,
            event_data: {
              x: 100 + i * 20,
              y: 150 + i * 20,
              distance_px: 28.28,
              time_delta_ms: 33,
              velocity_px_s: 850.0,
              acceleration_px_s2: 0.0,
              angle_degrees: 45.0,
              direction_change_deg: 0.0,
            },
          });
        }
      } else {
        for (let i = 0; i < 18; i++) {
          const u = (i + 1) / 18.0;
          const curveX = 100 + i * 18 + Math.sin(u * Math.PI) * 25;
          const curveY = 150 + i * 18 - Math.sin(u * Math.PI) * 15;
          const vel = 400 + Math.sin(u * Math.PI) * 350;
          sdk.recordEvent({
            event_type: 'mouse_move',
            client_timestamp: baseT + i * 35,
            event_data: {
              x: Math.round(curveX),
              y: Math.round(curveY),
              distance_px: 26.5,
              time_delta_ms: 35,
              velocity_px_s: Math.round(vel),
              acceleration_px_s2: Math.round((vel - 400) * 1.5),
              angle_degrees: Math.round(45.0 + Math.cos(u * Math.PI) * 12.0),
              direction_change_deg: i > 0 ? 3.5 : 0.0,
            },
          });
        }
      }

      // 3. Automated robotic click
      sdk.recordEvent({
        event_type: 'mouse_click',
        client_timestamp: baseT + (isVariable ? 680 : 550),
        event_data: {
          x: 400,
          y: 450,
          button: 0,
          click_type: 'single',
          time_since_last_click_ms: isVariable ? 540 : 500,
          target_category: 'button',
        },
      });

      // 4. Automated robotic typing
      for (let k = 0; k < 6; k++) {
        const dwell = isVariable ? (45 + (k % 4) * 6) : 50;
        const flight = isVariable ? (65 + (k % 5) * 8) : 70;
        sdk.recordEvent({
          event_type: 'key_meta',
          client_timestamp: baseT + (isVariable ? 800 : 700) + k * (dwell + flight),
          event_data: {
            dwell_ms: dwell,
            flight_ms: flight,
            inter_key_interval_ms: dwell + flight,
            is_backspace: false,
            is_paste: false,
          },
        });
      }

      // 5. Automated scroll bursts
      sdk.recordEvent({
        event_type: 'scroll',
        client_timestamp: baseT + 1500,
        event_data: {
          scroll_x: 0,
          scroll_y: isVariable ? 240 : 200,
          delta_x: 0,
          delta_y: isVariable ? 240 : 200,
          velocity_px_s: isVariable ? 1600.0 : 1500.0,
          direction: 'down',
          time_since_last_scroll_ms: isVariable ? 110 : 100,
        },
      });

      // 6. Automated route navigation
      sdk.recordEvent({
        event_type: 'navigation',
        client_timestamp: baseT + 1800,
        event_data: {
          path: '/demo/catalog',
          referrer: '/demo/landing',
          dwell_time_ms: 1800,
          sequence_number: 2,
        },
      });

      // 7. Flush and stop
      await sdk.flush();
      await sdk.stop(`${automationCondition}_SIMULATION_COMPLETED`);
      onRefreshStats();
      setExportNotice(`Completed ${automationCondition} simulation for ${selectedTask} (Label: 1)`);
    } catch (err) {
      console.error('Automated simulation failed:', err);
    } finally {
      setLoading(false);
    }
  };

  const currentTask = TASK_INSTRUCTIONS[selectedTask] || TASK_INSTRUCTIONS["TASK_01"];

  return (
    <div className="space-y-6">
      {/* Telemetry Controller & Live Metrics */}
      <TelemetryStatusPanel
        stats={stats}
        selectedTask={selectedTask}
        onTaskChange={setSelectedTask}
        collectionMode={collectionMode}
        onModeChange={setCollectionMode}
        automationCondition={automationCondition}
        onAutomationConditionChange={setAutomationCondition}
        participantId={participantId}
        onParticipantIdChange={setParticipantId}
        onStart={handleStart}
        onStop={handleStop}
        onFlush={handleFlush}
        loading={loading}
      />

      {/* Controlled Research Protocol Guidance Banner */}
      <div className="glass-panel p-5 rounded-xl border border-primary-500/20 bg-surface/80 space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-border/60 pb-3">
          <div className="flex items-center space-x-2.5">
            <ListChecks className="w-5 h-5 text-primary-400" />
            <div>
              <span className="text-xs font-mono uppercase text-primary-400">Research Task Protocol</span>
              <h2 className="text-base font-bold text-white tracking-tight">{currentTask.name} ({selectedTask})</h2>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <span className={`px-2.5 py-1 rounded text-xs font-mono font-medium border flex items-center space-x-1.5 ${
              collectionMode === 'HUMAN'
                ? 'bg-cyber-emerald/10 border-cyber-emerald/30 text-cyber-emerald'
                : 'bg-cyber-amber/10 border-cyber-amber/30 text-cyber-amber'
            }`}>
              {collectionMode === 'HUMAN' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
              <span>Mode: {collectionMode} (Label: {collectionMode === 'HUMAN' ? '0' : '1'})</span>
            </span>

            {collectionMode === 'AUTOMATED' && !stats.isRunning && (
              <button
                onClick={handleRunAutomatedSimulation}
                disabled={loading}
                className="flex items-center space-x-1.5 px-3 py-1 rounded bg-cyber-amber hover:bg-amber-600 text-slate-950 font-semibold text-xs transition-colors shadow"
              >
                <Bot className="w-3.5 h-3.5" />
                <span>Run Automated Simulation</span>
              </button>
            )}

            <button
              onClick={handleExportDataset}
              className="flex items-center space-x-1.5 px-3 py-1 rounded bg-surface-elevated hover:bg-slate-700 text-slate-200 border border-border text-xs transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV Dataset</span>
            </button>
          </div>
        </div>

        <p className="text-xs text-slate-300">{currentTask.description}</p>

        {/* Task Steps Checklist */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono text-slate-300 pt-1">
          {currentTask.steps.map((step, idx) => (
            <div key={idx} className="p-2 rounded bg-surface-elevated/40 border border-border/40 flex items-start space-x-2">
              <span className="text-primary-400 font-bold">[{idx + 1}]</span>
              <span className="text-slate-300">{step}</span>
            </div>
          ))}
        </div>

        {exportNotice && (
          <div className="p-2.5 rounded bg-emerald-950/40 border border-emerald-800/60 text-xs text-emerald-300 font-mono flex items-center space-x-2">
            <Check className="w-4 h-4 text-cyber-emerald flex-shrink-0" />
            <span>{exportNotice}</span>
          </div>
        )}

        {/* Live Observed API Telemetry Feedback Panel */}
        <div className="p-3.5 rounded-lg bg-surface-elevated/70 border border-primary-500/30 text-xs font-mono space-y-2">
          <div className="flex items-center justify-between text-slate-300">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-cyber-cyan" />
              <span className="font-semibold text-white">Live Application API Telemetry (Experiment B)</span>
            </div>
            <span className="text-[11px] text-slate-400">
              Session: <span className="text-primary-300 font-bold">{sdk.getSessionId() || 'Inactive (Standby)'}</span>
            </span>
          </div>

          {lastApiTelemetry ? (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] text-slate-300 pt-1 border-t border-border/50">
              <div>
                <span className="text-slate-400">Endpoint: </span>
                <span className="text-cyber-emerald font-bold">[{lastApiTelemetry.http_method}] {lastApiTelemetry.endpoint}</span>
              </div>
              <div>
                <span className="text-slate-400">Status / Latency: </span>
                <span className={`font-bold ${lastApiTelemetry.status_code >= 200 && lastApiTelemetry.status_code < 300 ? 'text-cyber-emerald' : 'text-cyber-amber'}`}>
                  HTTP {lastApiTelemetry.status_code} ({lastApiTelemetry.response_time_ms}ms)
                </span>
              </div>
              <div>
                <span className="text-slate-400">Parameters Logged: </span>
                <span className="text-primary-300">
                  {lastApiTelemetry.param_keys?.length ? `params: [${lastApiTelemetry.param_keys.join(', ')}]` : lastApiTelemetry.payload_keys?.length ? `payload: [${lastApiTelemetry.payload_keys.join(', ')}]` : 'None (Keys only)'}
                </span>
              </div>
            </div>
          ) : (
            <div className="text-[11px] text-slate-400 italic pt-1 border-t border-border/50">
              No application API requests dispatched in current session yet. Start session and perform task actions to observe live telemetry.
            </div>
          )}

          {apiActivityLog.length > 0 && (
            <div className="pt-1.5 border-t border-border/40 space-y-1">
              <span className="text-[10px] uppercase text-slate-500 font-semibold tracking-wider">Recent Dispatched Activity:</span>
              <div className="flex flex-wrap gap-1.5">
                {apiActivityLog.map((log, idx) => (
                  <span key={idx} className="px-2 py-0.5 rounded bg-surface border border-border/50 text-[10px] text-slate-300">
                    {log}
                  </span>
                ))}
              </div>
            </div>
          )}

          {apiError && (
            <div className="text-[11px] text-cyber-rose font-mono flex items-center space-x-1.5 pt-1">
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
              <span>{apiError}</span>
            </div>
          )}
        </div>
      </div>

      {/* Interactive Behavioral Collection Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Zone 1: Mouse Dynamics & Click Targets */}
        <div className="glass-panel p-6 rounded-xl space-y-4">
          <div className="flex items-center space-x-2 text-white font-semibold text-base border-b border-border/60 pb-3">
            <MousePointer className="w-4 h-4 text-cyber-cyan" />
            <span>Mouse Dynamics & Click Classification</span>
          </div>

          <p className="text-xs text-slate-300">
            Move pointer freely inside the interaction zone below. The SDK samples trajectory dynamics (~30Hz) and computes distance, velocity, acceleration, and angle deltas.
          </p>

          {/* Mouse Movement Canvas / Pad */}
          <div
            className="h-40 rounded-lg border-2 border-dashed border-primary-500/40 bg-surface-elevated/40 flex flex-col items-center justify-center cursor-crosshair relative overflow-hidden group hover:border-primary-400 transition-colors"
          >
            <div className="text-xs font-mono text-slate-400 text-center pointer-events-none px-4">
              <span className="text-primary-400 font-semibold">Mouse Telemetry Zone</span>
              <br />
              <span className="text-[11px] text-slate-500">Move cursor or click here</span>
            </div>
          </div>

          {/* Click Classification Test Targets */}
          <div className="space-y-2">
            <span className="text-xs font-mono text-slate-400 uppercase">Classified Click Elements:</span>
            <div className="flex flex-wrap gap-2.5">
              <button
                onClick={handleStandardButtonClick}
                className="px-3 py-1.5 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium transition-colors"
                title="TASK_01: Product details (/api/products/details) | TASK_03: Add cart item (/api/cart/items)"
              >
                Standard Button (Inspect Card)
              </button>

              <a
                href="#link-test"
                onClick={handleAnchorLinkClick}
                className="px-3 py-1.5 rounded-lg bg-surface-elevated hover:bg-slate-700 text-cyber-cyan border border-cyber-cyan/30 text-xs font-medium transition-colors inline-flex items-center"
                title="TASK_02: Search filter (/api/search/filter)"
              >
                Anchor Link (Filter Search)
              </a>

              <select
                onChange={(e) => handleSelectChange(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-surface-elevated border border-border text-slate-200 text-xs font-mono"
              >
                <option value="opt1">Sort: Relevance (Filter)</option>
                <option value="opt2">Sort: Rating (Filter)</option>
              </select>
            </div>
            <div className="text-[11px] font-mono text-slate-400 pt-1">
              Clicks: <span className="text-white font-bold">{clickCount}</span> | Last Target: <span className="text-cyber-cyan font-bold uppercase">{lastClickedCategory}</span>
            </div>
          </div>
        </div>

        {/* Zone 2: Privacy-Preserving Keystroke Timing */}
        <div className="glass-panel p-6 rounded-xl space-y-4">
          <div className="flex items-center space-x-2 text-white font-semibold text-base border-b border-border/60 pb-3">
            <Key className="w-4 h-4 text-cyber-emerald" />
            <span>Privacy-Preserving Keyboard Metadata</span>
          </div>

          <div className="p-3 rounded-lg bg-emerald-950/30 border border-emerald-800/40 text-xs text-emerald-300 flex items-start space-x-2.5">
            <Check className="w-4 h-4 text-cyber-emerald flex-shrink-0 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Zero Keystroke Content Capture:</strong> Type whatever you want. The SDK records only inter-key flight time (<span className="font-mono">flight_ms</span>) and dwell hold time (<span className="font-mono">dwell_ms</span>). Raw characters and typed words are permanently discarded.
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-mono text-slate-300">
              Interactive Typing Sandbox (TASK_02 Search Query):
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={demoTextInput}
                onChange={(e) => {
                  setDemoTextInput(e.target.value);
                  onRefreshStats();
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && demoTextInput.trim()) {
                    appClient.search(demoTextInput.trim(), 5);
                  }
                }}
                placeholder="Type query (e.g. 'laptop'). Debounced 500ms or press Enter..."
                className="flex-1 px-3.5 py-2 rounded-lg bg-surface-elevated border border-border text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 font-sans"
              />
              <button
                onClick={() => {
                  if (demoTextInput.trim()) {
                    appClient.search(demoTextInput.trim(), 5);
                  }
                }}
                className="px-3 py-2 rounded-lg bg-primary-600 hover:bg-primary-500 text-white text-xs font-medium transition-colors"
              >
                Search
              </button>
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-elevated/40 border border-border/60 text-xs font-mono text-slate-400 space-y-1">
            <div className="flex justify-between">
              <span>Keystrokes Typed:</span>
              <span className="text-white font-bold">{demoTextInput.length}</span>
            </div>
            <div className="flex justify-between">
              <span>Payload Keystroke Characters:</span>
              <span className="text-cyber-emerald font-bold uppercase">0 (STRICTLY OMITTED)</span>
            </div>
          </div>
        </div>

        {/* Zone 3: Scroll Burst Dynamics */}
        <div className="glass-panel p-6 rounded-xl space-y-4">
          <div className="flex items-center space-x-2 text-white font-semibold text-base border-b border-border/60 pb-3">
            <ArrowUpDown className="w-4 h-4 text-cyber-amber" />
            <span>Scroll Dynamics & Burst Detection</span>
          </div>

          <p className="text-xs text-slate-300">
            Scroll inside the overflow viewport below to trigger debounced scroll burst telemetry (direction, velocity, and delta deltas).
          </p>

          <div className="h-36 overflow-y-auto p-4 rounded-lg bg-surface-elevated/50 border border-border/60 space-y-3 font-mono text-xs text-slate-400">
            <p className="text-slate-300 font-semibold">[Scrollable Test Viewport]</p>
            <p>1. Scroll down to generate downward displacement.</p>
            <p>2. Pause to trigger scroll burst finalization.</p>
            <p>3. Scroll back up to test direction inversion frequency.</p>
            <p>4. SDK throttles rapid events to ~100ms intervals to optimize bandwidth.</p>
            <p>5. End of test buffer reached.</p>
          </div>
        </div>

        {/* Zone 4: Sequence Navigation Markov Preparation */}
        <div className="glass-panel p-6 rounded-xl space-y-4">
          <div className="flex items-center space-x-2 text-white font-semibold text-base border-b border-border/60 pb-3">
            <Compass className="w-4 h-4 text-primary-400" />
            <span>Session Sequence Route Simulation</span>
          </div>

          <p className="text-xs text-slate-300">
            Simulates SPA route transitions to construct session sequence vectors $(S_1 \to S_2 \to S_3)$ with dwell timing for the Markov Sequence engine.
          </p>

          <div className="grid grid-cols-2 gap-2">
            {[
              '/demo/landing',
              '/demo/catalog',
              '/demo/cart',
              '/demo/checkout',
            ].map((route) => (
              <button
                key={route}
                onClick={() => handleSimulatedNavigation(route)}
                className={`px-3 py-2 rounded-lg text-xs font-mono font-medium text-left transition-all border ${
                  activeRoute === route
                    ? 'bg-primary-600/30 border-primary-500 text-primary-200'
                    : 'bg-surface-elevated/60 border-border hover:bg-slate-700 text-slate-300'
                }`}
              >
                {route}
              </button>
            ))}
          </div>

          <div className="text-[11px] font-mono text-slate-400">
            Current Sequence Step: <span className="text-white font-bold">{activeRoute}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
