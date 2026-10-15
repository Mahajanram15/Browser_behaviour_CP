import React from 'react';
import { ShieldCheck, Activity, Users, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { DashboardStats, HealthResponse } from '../types';

interface DashboardShellProps {
  stats: DashboardStats | null;
  health: HealthResponse | null;
  loading: boolean;
}

export const DashboardShell: React.FC<DashboardShellProps> = ({ stats, health, loading: _loading }) => {
  return (
    <div className="space-y-6">
      {/* Top Banner: Research Foundation Overview */}
      <div className="glass-panel p-6 rounded-xl relative overflow-hidden">
        <div className="absolute -right-10 -top-10 w-48 h-48 bg-primary-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-3xl">
          <div className="inline-flex items-center space-x-2 px-2.5 py-1 rounded-full bg-primary-500/10 border border-primary-500/20 text-primary-400 text-xs font-mono mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-400 animate-pulse" />
            <span>Research USP: Cross-Layer Behavioral Integrity</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white mb-2">
            Cross-Layer Behavioral Security Architecture
          </h1>
          <p className="text-slate-300 text-sm leading-relaxed">
            Evaluates cross-layer consistency between real-time browser motor dynamics (pointer curves, typing intervals, scroll cadence) and backend API access telemetry to detect botnets, headless automation, and replay fraud.
          </p>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Sessions */}
        <div className="glass-panel p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Tracked</span>
            <Users className="w-4 h-4 text-slate-400" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-white">
              {stats?.total_sessions ?? 0}
            </span>
            <span className="text-xs text-cyber-emerald flex items-center font-mono">
              Active: {stats?.active_sessions ?? 0}
            </span>
          </div>
        </div>

        {/* Avg Risk Score */}
        <div className="glass-panel p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Fleet Risk Score</span>
            <Activity className="w-4 h-4 text-cyber-cyan" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-cyber-cyan">
              {stats?.average_risk_score !== undefined ? stats.average_risk_score.toFixed(2) : '0.00'}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Range: [0.0 - 1.0]
            </span>
          </div>
        </div>

        {/* Allow Decisions */}
        <div className="glass-panel p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Allow Rate</span>
            <CheckCircle2 className="w-4 h-4 text-cyber-emerald" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-cyber-emerald">
              {stats?.decision_distribution?.ALLOW ?? 0}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Risk &lt; 0.35
            </span>
          </div>
        </div>

        {/* Challenge / Rate Limit */}
        <div className="glass-panel p-5 rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Flagged / Blocked</span>
            <AlertTriangle className="w-4 h-4 text-cyber-amber" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold font-mono text-cyber-amber">
              {(stats?.decision_distribution?.CHALLENGE ?? 0) + (stats?.decision_distribution?.BLOCK ?? 0)}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Risk &ge; 0.35
            </span>
          </div>
        </div>
      </div>

      {/* Subsystem & Foundation Status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Architecture Components Card */}
        <div className="glass-panel p-6 rounded-xl">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center space-x-2">
            <ShieldCheck className="w-4 h-4 text-primary-400" />
            <span>Subsystem Foundation Matrix</span>
          </h2>
          <div className="space-y-3">
            {health?.components ? (
              Object.entries(health.components).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between p-3 rounded-lg bg-surface-elevated/50 border border-border/60">
                  <div className="flex items-center space-x-3">
                    <span className="w-2 h-2 rounded-full bg-cyber-emerald" />
                    <span className="font-mono text-xs text-slate-200 capitalize">
                      {key.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <span className="text-xs font-mono uppercase text-cyber-emerald px-2 py-0.5 rounded bg-cyber-emerald/10 border border-cyber-emerald/20">
                    {val}
                  </span>
                </div>
              ))
            ) : (
              <div className="text-xs font-mono text-slate-400">Loading component health...</div>
            )}
          </div>
        </div>

        {/* Privacy & Research Guardrails */}
        <div className="glass-panel p-6 rounded-xl">
          <h2 className="text-base font-semibold text-white mb-4 flex items-center space-x-2">
            <Activity className="w-4 h-4 text-cyber-cyan" />
            <span>Privacy-Preserving Telemetry Design</span>
          </h2>
          <div className="space-y-3 text-xs text-slate-300">
            <div className="p-3 rounded-lg bg-surface-elevated/50 border border-border/60 flex items-start space-x-3">
              <span className="text-cyber-cyan font-bold font-mono">01</span>
              <div>
                <p className="font-medium text-slate-200">Zero Keystroke Content Capture</p>
                <p className="text-slate-400 mt-0.5">Captures only inter-key flight timing ($\Delta t$) and dwell duration. Character codes are discarded at listener invocation.</p>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-surface-elevated/50 border border-border/60 flex items-start space-x-3">
              <span className="text-cyber-cyan font-bold font-mono">02</span>
              <div>
                <p className="font-medium text-slate-200">Form Isolation</p>
                <p className="text-slate-400 mt-0.5">Form inputs, passwords, and user values are never read or transmitted by the Browser SDK.</p>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-surface-elevated/50 border border-border/60 flex items-start space-x-3">
              <span className="text-cyber-cyan font-bold font-mono">03</span>
              <div>
                <p className="font-medium text-slate-200">Continuous Behavioral Integrity Scoring</p>
                <p className="text-slate-400 mt-0.5">Continuous risk assessment $[0.0 - 1.0]$ rather than binary human classification.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
