import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  FolderGit2,
  FileText,
  Database,
  ShieldCheck,
  ArrowUpRight,
  Upload,
  Play,
  Activity,
  RotateCcw,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
} from 'recharts';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';

export const Dashboard: React.FC = () => {
  const { selectedProjectId, openResetModal } = useAppStore();

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const { data: documents = [] } = useQuery({
    queryKey: ['documents', selectedProjectId],
    queryFn: () => apiClient.getDocuments(selectedProjectId || undefined),
  });

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  const { data: activities = [] } = useQuery({
    queryKey: ['activity', selectedProjectId],
    queryFn: () => apiClient.getActivity(selectedProjectId || undefined, 8),
  });

  // Aggregate Metrics
  const totalRecords = datasets.reduce((sum, d) => sum + d.record_count, 0);
  const totalValid = datasets.reduce((sum, d) => sum + d.valid_record_count, 0);
  const totalWarnings = datasets.reduce((sum, d) => sum + d.warning_record_count, 0);
  const totalErrors = datasets.reduce((sum, d) => sum + d.error_record_count, 0);

  const avgQualityScore =
    datasets.length > 0
      ? (datasets.reduce((sum, d) => sum + d.quality_score, 0) / datasets.length).toFixed(1)
      : '100.0';

  const chartData = [
    { name: 'Valid', count: totalValid, color: '#10B981' },
    { name: 'Warnings', count: totalWarnings, color: '#F59E0B' },
    { name: 'Errors', count: totalErrors, color: '#EF4444' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight">
            Workstation Overview
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Wits–merSETA Darkroom document intelligence pipelines & structured datasets
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={openResetModal}
            title="Reset SQLite Database (Run python reset_db.py)"
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-rose-950/40 hover:bg-rose-900/60 text-xs font-medium text-rose-300 hover:text-rose-100 border border-rose-800/50 rounded-lg transition-colors font-mono cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5 text-rose-400" />
            <span>Reset DB</span>
          </button>
          <Link
            to="/documents"
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-xs font-medium text-gray-200 border border-darkroom-border rounded-lg transition-colors"
          >
            <Upload className="w-3.5 h-3.5 text-darkroom-gold" />
            <span>Upload Documents</span>
          </Link>
          <Link
            to="/pipeline"
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            <Play className="w-3.5 h-3.5" />
            <span>Run Pipeline</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">Total Projects</span>
            <FolderGit2 className="w-4 h-4 text-darkroom-gold" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-gray-100">
            {projects.length}
          </div>
          <div className="mt-1 text-[11px] text-gray-400">
            {selectedProjectId ? 'Active filter applied' : 'Across all research units'}
          </div>
        </div>

        <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">Ingested Documents</span>
            <FileText className="w-4 h-4 text-sky-400" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-gray-100">
            {documents.length}
          </div>
          <div className="mt-1 text-[11px] text-gray-400">
            PDFs classified & inspected
          </div>
        </div>

        <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">Extracted Records</span>
            <Database className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-gray-100">
            {totalRecords.toLocaleString()}
          </div>
          <div className="mt-1 text-[11px] text-emerald-400 font-mono">
            {totalValid.toLocaleString()} validated
          </div>
        </div>

        <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">Quality Score</span>
            <ShieldCheck className="w-4 h-4 text-darkroom-gold" />
          </div>
          <div className="mt-2 text-2xl font-bold font-mono text-gray-100">
            {avgQualityScore}%
          </div>
          <div className="mt-1 text-[11px] text-gray-400">
            Across {datasets.length} active dataset(s)
          </div>
        </div>
      </div>

      {/* Main Grid: Quality Chart & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Record Integrity Distribution Chart */}
        <div className="lg:col-span-2 bg-darkroom-surface border border-darkroom-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-gray-100 font-mono">
                Record Quality Distribution
              </h2>
              <p className="text-xs text-gray-400">
                Data validation status across all extracted table rows
              </p>
            </div>
            <Link
              to="/validation"
              className="text-xs text-darkroom-gold hover:underline flex items-center space-x-1 font-mono"
            >
              <span>View Audit</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          <div className="h-60 w-full">
            {totalRecords > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} layout="vertical" margin={{ left: 10, right: 30, top: 10, bottom: 10 }}>
                  <XAxis type="number" stroke="#6B7280" fontSize={11} />
                  <YAxis dataKey="name" type="category" stroke="#9CA3AF" fontSize={12} width={70} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#111827',
                      borderColor: '#374151',
                      borderRadius: '8px',
                      fontSize: '12px',
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-gray-400 text-xs font-mono">
                <Database className="w-8 h-8 text-gray-600 mb-2" />
                <span>No dataset records generated yet. Ingest documents to view metrics.</span>
              </div>
            )}
          </div>
        </div>

        {/* Activity Feed */}
        <div className="bg-darkroom-surface border border-darkroom-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Activity className="w-4 h-4 text-darkroom-gold" />
              <h2 className="text-sm font-semibold text-gray-100 font-mono">
                Recent Audit Trail
              </h2>
            </div>
          </div>

          <div className="space-y-3">
            {activities.length > 0 ? (
              activities.map((act) => (
                <div
                  key={act.id}
                  className="p-2.5 bg-darkroom-card/60 border border-darkroom-border/60 rounded-lg text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-darkroom-gold text-[11px] uppercase font-semibold">
                      {act.action}
                    </span>
                    <span className="text-[10px] text-gray-400 font-mono">
                      {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p className="text-gray-200 mt-1 line-clamp-2">{act.description}</p>
                  <div className="mt-1 text-[10px] text-gray-400 font-mono">
                    by {act.user}
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-center text-gray-400 text-xs font-mono">
                No activity records yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
