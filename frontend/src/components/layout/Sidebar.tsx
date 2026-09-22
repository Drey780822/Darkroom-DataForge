import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FolderGit2,
  FileText,
  Workflow,
  Database,
  ShieldCheck,
  History,
  Download,
  Terminal,
  Bot,
  Award,
} from 'lucide-react';

const NAV_ITEMS = [
  { name: 'Dashboard', path: '/', icon: LayoutDashboard },
  { name: 'Projects', path: '/projects', icon: FolderGit2 },
  { name: 'Documents', path: '/documents', icon: FileText },
  { name: 'AI Models & LLMs', path: '/ai-models', icon: Bot },
  { name: 'Pipeline', path: '/pipeline', icon: Workflow },
  { name: 'Datasets', path: '/datasets', icon: Database },
  { name: 'Validation', path: '/validation', icon: ShieldCheck },
  { name: 'Review & Audit', path: '/review', icon: History },
  { name: 'Evaluation Benchmarks', path: '/evaluation', icon: Award },
  { name: 'Exports', path: '/exports', icon: Download },
];

export const Sidebar: React.FC = () => {
  return (
    <aside className="w-60 bg-darkroom-surface border-r border-darkroom-border flex flex-col justify-between py-4">
      {/* Primary Navigation */}
      <nav className="space-y-1 px-3">
        <div className="px-3 pb-2 text-[10px] font-mono uppercase tracking-wider text-gray-400 font-semibold">
          Workstation Navigation
        </div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-darkroom-card text-darkroom-gold border border-darkroom-gold/30 shadow-sm'
                    : 'text-gray-400 hover:text-gray-200 hover:bg-darkroom-card/50'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Info / Provenance Badge */}
      <div className="px-4 py-3 mx-3 bg-darkroom-card/70 border border-darkroom-border rounded-lg text-xs text-gray-400">
        <div className="flex items-center space-x-2 text-darkroom-gold font-mono text-[11px] font-medium mb-1">
          <Terminal className="w-3.5 h-3.5" />
          <span>Research Pipeline</span>
        </div>
        <p className="text-[10px] text-gray-400 leading-relaxed font-mono">
          Provenance tracking active from source PDF page to final dataset record.
        </p>
      </div>
    </aside>
  );
};
