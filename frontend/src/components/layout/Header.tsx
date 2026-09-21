import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { FolderGit2, CheckCircle2, AlertCircle, Database, ChevronDown } from 'lucide-react';
import { apiClient } from '../../services/api';
import { useAppStore } from '../../store/useAppStore';

export const Header: React.FC = () => {
  const { selectedProjectId, setSelectedProjectId } = useAppStore();

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: apiClient.getHealth,
    refetchInterval: 15000,
  });

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const isHealthy = health?.status === 'healthy';

  return (
    <header className="h-14 bg-darkroom-surface border-b border-darkroom-border flex items-center justify-between px-6 z-20">
      {/* Brand & Sub-brand */}
      <div className="flex items-center space-x-4">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-darkroom-navy via-slate-800 to-darkroom-gold flex items-center justify-center font-bold text-darkroom-gold border border-darkroom-gold/40 shadow-sm">
            DF
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold tracking-wider text-sm text-gray-100 uppercase font-mono">
                Darkroom DataForge
              </span>
              <span className="px-1.5 py-0.2 bg-darkroom-goldLight text-darkroom-gold text-[10px] font-mono rounded border border-darkroom-gold/30">
                v2.0
              </span>
            </div>
            <p className="text-[11px] text-gray-400 font-mono tracking-tight -mt-0.5">
              Wits–merSETA Darkroom • Document Intelligence & Structured Data
            </p>
          </div>
        </div>
      </div>

      {/* Right controls: Project selector & System telemetry */}
      <div className="flex items-center space-x-4">
        {/* Project Selector */}
        <div className="flex items-center space-x-2 bg-darkroom-bg border border-darkroom-border px-3 py-1.5 rounded-lg">
          <FolderGit2 className="w-4 h-4 text-darkroom-gold" />
          <select
            value={selectedProjectId || ''}
            onChange={(e) => setSelectedProjectId(e.target.value || null)}
            className="bg-transparent text-xs text-gray-200 focus:outline-none cursor-pointer pr-4 font-mono"
          >
            <option value="" className="bg-darkroom-surface text-gray-400">
              All Projects (Global Scope)
            </option>
            {projects.map((p) => (
              <option key={p.id} value={p.id} className="bg-darkroom-surface text-gray-200">
                {p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Database & System Status */}
        <div className="flex items-center space-x-2 border-l border-darkroom-border pl-4">
          <div
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded text-xs font-mono ${
              isHealthy
                ? 'text-emerald-400 bg-emerald-950/40 border border-emerald-800/50'
                : 'text-rose-400 bg-rose-950/60 border border-rose-800/80'
            }`}
          >
            {isHealthy ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>
                  Online ({health?.database?.engine === 'postgresql' ? 'PostgreSQL' : 'SQLite'})
                </span>
              </>
            ) : (
              <>
                <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
                <span className="font-semibold">
                  Backend Offline (:8000)
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
