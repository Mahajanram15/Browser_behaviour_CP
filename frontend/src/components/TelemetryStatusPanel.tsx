import React from 'react';
import { Play, Square, RefreshCw, Radio, AlertCircle, Bot, User, Target } from 'lucide-react';
import { TelemetryStats } from '@behavioral-integrity/sdk';

interface TelemetryStatusPanelProps {
  stats: TelemetryStats;
  selectedTask: string;
  onTaskChange: (taskId: string) => void;
  collectionMode: 'HUMAN' | 'AUTOMATED';
  onModeChange: (mode: 'HUMAN' | 'AUTOMATED') => void;
  automationCondition: 'AUTOMATED_DETERMINISTIC' | 'AUTOMATED_VARIABLE';
  onAutomationConditionChange: (cond: 'AUTOMATED_DETERMINISTIC' | 'AUTOMATED_VARIABLE') => void;
  participantId: string;
  onParticipantIdChange: (id: string) => void;
  onStart: () => void;
  onStop: () => void;
  onFlush: () => void;
  loading: boolean;
}

export const TelemetryStatusPanel: React.FC<TelemetryStatusPanelProps> = ({
  stats,
  selectedTask,
  onTaskChange,
  collectionMode,
  onModeChange,
  automationCondition,
  onAutomationConditionChange,
  participantId,
  onParticipantIdChange,
  onStart,
  onStop,
  onFlush,
  loading,
}) => {
  return (
    <div className="glass-panel p-5 rounded-xl border border-primary-500/30 bg-surface/90 shadow-xl space-y-4">
      {/* Top Header & Session State */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-border/80">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-primary-500/10 border border-primary-500/30">
            <Radio className={`w-5 h-5 ${stats.isRunning ? 'text-cyber-emerald animate-pulse' : 'text-slate-400'}`} />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-semibold text-white">Controlled Telemetry Collection Controller</h3>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full uppercase ${
                stats.isRunning
                  ? 'bg-cyber-emerald/15 text-cyber-emerald border border-cyber-emerald/30'
                  : 'bg-slate-700 text-slate-300'
              }`}>
                {stats.isRunning ? 'Streaming Active' : 'Idle'}
              </span>
            </div>
            <p className="text-xs font-mono text-slate-400 mt-0.5">
              Session ID: <span className="text-primary-400 font-semibold">{stats.sessionId || 'None (Click Start Session)'}</span>
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2.5">
          {!stats.isRunning ? (
            <button
              onClick={onStart}
              disabled={loading}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-cyber-emerald hover:bg-emerald-600 text-slate-950 font-medium text-xs shadow-md transition-colors"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Start Labeled Session</span>
            </button>
          ) : (
            <button
              onClick={onStop}
              disabled={loading}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-cyber-rose hover:bg-rose-600 text-white font-medium text-xs shadow-md transition-colors"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>Complete & Label Session</span>
            </button>
          )}

          <button
            onClick={onFlush}
            disabled={!stats.isRunning || loading}
            title="Force Flush In-Memory Buffer"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-surface-elevated hover:bg-slate-700 text-slate-200 border border-border text-xs transition-colors disabled:opacity-40"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Flush Buffer</span>
          </button>
        </div>
      </div>

      {/* Controlled Experiment Selectors: Mode, Condition, Task, Entity */}
      <div className="flex flex-wrap items-center justify-between gap-4 p-3 rounded-lg bg-surface-elevated/40 border border-border/60 text-xs">
        {/* Mode Selector */}
        <div className="flex items-center space-x-2">
          <span className="text-slate-400 font-mono">Mode:</span>
          <div className="inline-flex rounded-md p-0.5 bg-surface border border-border">
            <button
              onClick={() => onModeChange('HUMAN')}
              disabled={stats.isRunning}
              className={`flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                collectionMode === 'HUMAN'
                  ? 'bg-cyber-emerald/20 text-cyber-emerald border border-cyber-emerald/40'
                  : 'text-slate-400 hover:text-slate-200'
              } disabled:opacity-60`}
            >
              <User className="w-3 h-3" />
              <span>HUMAN (0)</span>
            </button>

            <button
              onClick={() => onModeChange('AUTOMATED')}
              disabled={stats.isRunning}
              className={`flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                collectionMode === 'AUTOMATED'
                  ? 'bg-cyber-amber/20 text-cyber-amber border border-cyber-amber/40'
                  : 'text-slate-400 hover:text-slate-200'
              } disabled:opacity-60`}
            >
              <Bot className="w-3 h-3" />
              <span>AUTOMATED (1)</span>
            </button>
          </div>
        </div>

        {/* Automation Condition (Only visible if AUTOMATED) */}
        {collectionMode === 'AUTOMATED' && (
          <div className="flex items-center space-x-2">
            <span className="text-slate-400 font-mono">Condition:</span>
            <div className="inline-flex rounded-md p-0.5 bg-surface border border-border">
              <button
                onClick={() => onAutomationConditionChange('AUTOMATED_DETERMINISTIC')}
                disabled={stats.isRunning}
                className={`px-2 py-0.5 rounded text-xs font-mono transition-colors ${
                  automationCondition === 'AUTOMATED_DETERMINISTIC'
                    ? 'bg-primary-500/20 text-primary-300 border border-primary-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                } disabled:opacity-60`}
              >
                DETERMINISTIC (Baseline)
              </button>
              <button
                onClick={() => onAutomationConditionChange('AUTOMATED_VARIABLE')}
                disabled={stats.isRunning}
                className={`px-2 py-0.5 rounded text-xs font-mono transition-colors ${
                  automationCondition === 'AUTOMATED_VARIABLE'
                    ? 'bg-cyber-cyan/20 text-cyber-cyan border border-cyber-cyan/40'
                    : 'text-slate-400 hover:text-slate-200'
                } disabled:opacity-60`}
              >
                VARIABLE (Challenge)
              </button>
            </div>
          </div>
        )}

        {/* Task Selector */}
        <div className="flex items-center space-x-2">
          <Target className="w-3.5 h-3.5 text-primary-400" />
          <span className="text-slate-400 font-mono">Task:</span>
          <select
            value={selectedTask}
            onChange={(e) => onTaskChange(e.target.value)}
            disabled={stats.isRunning}
            className="px-2.5 py-1 rounded-md bg-surface border border-border text-slate-200 text-xs font-mono focus:outline-none focus:border-primary-500 disabled:opacity-60"
          >
            <option value="TASK_01">TASK_01: Catalog Browsing</option>
            <option value="TASK_02">TASK_02: Search & Query Filtering</option>
            <option value="TASK_03">TASK_03: Multi-Page Exploration</option>
          </select>
        </div>

        {/* Participant / Entity ID (Provenance only) */}
        <div className="flex items-center space-x-2">
          <span className="text-slate-400 font-mono">Entity ID:</span>
          <input
            type="text"
            value={participantId}
            onChange={(e) => onParticipantIdChange(e.target.value)}
            disabled={stats.isRunning}
            placeholder={collectionMode === 'HUMAN' ? 'p_01' : 'bot_entity'}
            className="w-24 px-2 py-0.5 rounded-md bg-surface border border-border text-slate-200 text-xs font-mono focus:outline-none focus:border-primary-500 disabled:opacity-60"
          />
        </div>
      </div>

      {/* Live Telemetry Counter Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-lg bg-surface-elevated/40 border border-border/60">
          <span className="text-[11px] font-mono text-slate-400 uppercase">Captured</span>
          <div className="text-lg font-mono font-bold text-white mt-0.5">{stats.eventsCollected}</div>
        </div>

        <div className="p-3 rounded-lg bg-surface-elevated/40 border border-border/60">
          <span className="text-[11px] font-mono text-slate-400 uppercase">Dispatched (API)</span>
          <div className="text-lg font-mono font-bold text-cyber-cyan mt-0.5">{stats.eventsSent}</div>
        </div>

        <div className="p-3 rounded-lg bg-surface-elevated/40 border border-border/60">
          <span className="text-[11px] font-mono text-slate-400 uppercase">In Buffer</span>
          <div className="text-lg font-mono font-bold text-cyber-amber mt-0.5">{stats.eventsBuffered}</div>
        </div>

        <div className="p-3 rounded-lg bg-surface-elevated/40 border border-border/60">
          <span className="text-[11px] font-mono text-slate-400 uppercase">Last Flush</span>
          <div className="text-xs font-mono text-slate-300 mt-1.5 truncate">
            {stats.lastFlushTime ? new Date(stats.lastFlushTime).toLocaleTimeString() : 'Never'}
          </div>
        </div>
      </div>

      {stats.lastError && (
        <div className="p-2.5 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0" />
          <span className="font-mono">{stats.lastError}</span>
        </div>
      )}
    </div>
  );
};
