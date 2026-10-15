import React from 'react';
import { Shield, Radio, LayoutDashboard } from 'lucide-react';

interface NavbarProps {
  systemHealth: string;
  activeTab: 'overview' | 'sandbox';
  onTabChange: (tab: 'overview' | 'sandbox') => void;
  isStreaming: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  systemHealth,
  activeTab,
  onTabChange,
  isStreaming,
}) => {
  return (
    <header className="sticky top-0 z-50 border-b border-border/80 bg-surface/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-primary-600 to-cyber-cyan flex items-center justify-center shadow-lg shadow-primary-500/20">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-slate-100 tracking-tight text-base">
                Behavioral Integrity
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full font-mono bg-cyber-emerald/10 text-cyber-emerald border border-cyber-emerald/30">
                Phase 2: Browser SDK
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono">
              Cross-Layer Behavioral Verification
            </p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center space-x-1 bg-surface-elevated/80 p-1 rounded-lg border border-border/70">
          <button
            onClick={() => onTabChange('sandbox')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'sandbox'
                ? 'bg-primary-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Radio className={`w-3.5 h-3.5 ${isStreaming ? 'text-cyber-emerald animate-pulse' : ''}`} />
            <span>Telemetry Sandbox</span>
          </button>

          <button
            onClick={() => onTabChange('overview')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
              activeTab === 'overview'
                ? 'bg-primary-600 text-white shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>System Matrix</span>
          </button>
        </div>

        {/* System Status Indicator */}
        <div className="flex items-center space-x-2 px-3 py-1 rounded-md bg-surface-elevated border border-border">
          <span
            className={`w-2 h-2 rounded-full ${
              systemHealth === 'healthy'
                ? 'bg-cyber-emerald animate-pulse'
                : 'bg-cyber-amber'
            }`}
          />
          <span className="text-xs font-mono uppercase text-slate-300">
            {systemHealth}
          </span>
        </div>
      </div>
    </header>
  );
};
