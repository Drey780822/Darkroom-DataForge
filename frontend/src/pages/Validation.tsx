import React, { useState, useEffect } from 'react';
import { useLocation, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ShieldCheck,
  AlertTriangle,
  XCircle,
  Info,
  CheckCircle2,
  Check,
  Database,
  Search,
  ExternalLink,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';
import { ValidationIssue } from '../types';

export const Validation: React.FC = () => {
  const location = useLocation();
  const queryClient = useQueryClient();
  const { selectedProjectId } = useAppStore();

  const defaultDsId = location.state?.defaultDatasetId;

  const [activeDatasetId, setActiveDatasetId] = useState<string>(defaultDsId || '');
  const [severityFilter, setSeverityFilter] = useState<string>('');
  const [resolvingIssue, setResolvingIssue] = useState<ValidationIssue | null>(null);
  const [correctedValue, setCorrectedValue] = useState<string>('');
  const [resolutionComment, setResolutionComment] = useState<string>('');

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  useEffect(() => {
    if (!activeDatasetId && datasets.length > 0) {
      setActiveDatasetId(datasets[0].id);
    }
  }, [datasets, activeDatasetId]);

  const { data: summary, isLoading } = useQuery({
    queryKey: ['validation-summary', activeDatasetId],
    queryFn: () => apiClient.getValidationSummary(activeDatasetId),
    enabled: !!activeDatasetId,
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      apiClient.resolveValidationIssue(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['validation-summary', activeDatasetId] });
      queryClient.invalidateQueries({ queryKey: ['records', activeDatasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', activeDatasetId] });
      setResolvingIssue(null);
      setCorrectedValue('');
      setResolutionComment('');
    },
  });

  const handleResolveSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!resolvingIssue) return;
    resolveMutation.mutate({
      id: resolvingIssue.id,
      data: {
        is_resolved: true,
        resolved_by: 'Researcher',
        resolution_comment: resolutionComment,
        corrected_value: correctedValue.trim() ? correctedValue : undefined,
      },
    });
  };

  const filteredIssues = (summary?.issues || []).filter((iss) => {
    if (severityFilter && iss.severity !== severityFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight">
            Data Quality & Validation Audit
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Rule-based constraint verification, schema compliance, and exception resolution
          </p>
        </div>

        {/* Dataset Selector */}
        <div className="flex items-center space-x-2">
          <Database className="w-4 h-4 text-darkroom-gold" />
          <select
            value={activeDatasetId}
            onChange={(e) => setActiveDatasetId(e.target.value)}
            className="px-3 py-1.5 bg-darkroom-surface border border-darkroom-border rounded-lg text-xs font-mono text-gray-200 focus:outline-none focus:border-darkroom-gold"
          >
            {datasets.map((d) => (
              <option key={d.id} value={d.id}>
                {d.name} ({d.quality_score}%)
              </option>
            ))}
          </select>
        </div>
      </div>

      {summary && (
        <>
          {/* Quality Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl font-mono">
              <div className="text-xs text-gray-400">Quality Score</div>
              <div className="text-2xl font-bold text-darkroom-gold mt-1">
                {summary.quality_score}%
              </div>
              <div className="text-[11px] text-gray-500 mt-1">
                {summary.valid_records} / {summary.total_records} valid rows
              </div>
            </div>

            <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl font-mono">
              <div className="text-xs text-rose-400 flex items-center space-x-1">
                <XCircle className="w-3.5 h-3.5" />
                <span>Errors</span>
              </div>
              <div className="text-2xl font-bold text-rose-400 mt-1">
                {summary.issues_by_severity.error || 0}
              </div>
              <div className="text-[11px] text-gray-500 mt-1">Requires manual correction</div>
            </div>

            <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl font-mono">
              <div className="text-xs text-amber-400 flex items-center space-x-1">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Warnings</span>
              </div>
              <div className="text-2xl font-bold text-amber-400 mt-1">
                {summary.issues_by_severity.warning || 0}
              </div>
              <div className="text-[11px] text-gray-500 mt-1">Possible formatting anomalies</div>
            </div>

            <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl font-mono">
              <div className="text-xs text-emerald-400 flex items-center space-x-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Resolved</span>
              </div>
              <div className="text-2xl font-bold text-emerald-400 mt-1">
                {summary.issues.filter((i) => i.is_resolved).length}
              </div>
              <div className="text-[11px] text-gray-500 mt-1">Audited exceptions</div>
            </div>
          </div>

          {/* Issues Filter & Table */}
          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl overflow-hidden shadow-sm font-mono text-xs">
            <div className="p-3 bg-darkroom-card border-b border-darkroom-border flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="font-bold text-gray-200">Validation Issues</span>
                <span className="text-gray-500">({filteredIssues.length} found)</span>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setSeverityFilter('')}
                  className={`px-2.5 py-1 rounded text-[11px] ${
                    severityFilter === '' ? 'bg-darkroom-gold text-black font-semibold' : 'text-gray-400'
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setSeverityFilter('error')}
                  className={`px-2.5 py-1 rounded text-[11px] ${
                    severityFilter === 'error' ? 'bg-rose-900 text-rose-200 font-semibold' : 'text-gray-400'
                  }`}
                >
                  Errors
                </button>
                <button
                  onClick={() => setSeverityFilter('warning')}
                  className={`px-2.5 py-1 rounded text-[11px] ${
                    severityFilter === 'warning' ? 'bg-amber-900 text-amber-200 font-semibold' : 'text-gray-400'
                  }`}
                >
                  Warnings
                </button>
              </div>
            </div>

            <div className="overflow-x-auto max-h-[55vh]">
              <table className="w-full text-left">
                <thead className="bg-darkroom-card/60 border-b border-darkroom-border text-gray-400">
                  <tr>
                    <th className="p-3">Row #</th>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Field</th>
                    <th className="p-3">Rule Name</th>
                    <th className="p-3">Message</th>
                    <th className="p-3">Current Value</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-darkroom-border/60 text-gray-300">
                  {filteredIssues.map((iss) => (
                    <tr
                      key={iss.id}
                      className={`hover:bg-darkroom-card/50 transition-colors ${
                        iss.is_resolved ? 'opacity-60 bg-darkroom-card/20' : ''
                      }`}
                    >
                      <td className="p-3 font-bold text-gray-400">{iss.row_index ?? '-'}</td>
                      <td className="p-3">
                        <Badge
                          variant={
                            iss.severity === 'error'
                              ? 'danger'
                              : iss.severity === 'warning'
                              ? 'warning'
                              : 'navy'
                          }
                        >
                          {iss.severity.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="p-3 text-gray-200 font-semibold">{iss.column_name || 'N/A'}</td>
                      <td className="p-3 text-gray-400">{iss.rule_name}</td>
                      <td className="p-3 text-gray-300 max-w-sm">{iss.message}</td>
                      <td className="p-3 max-w-xs truncate text-darkroom-gold">
                        {iss.raw_value || <span className="italic text-gray-600">empty</span>}
                      </td>
                      <td className="p-3">
                        {iss.is_resolved ? (
                          <span className="text-emerald-400 font-bold">Resolved</span>
                        ) : (
                          <span className="text-rose-400">Open</span>
                        )}
                      </td>
                      <td className="p-3 text-right">
                        {!iss.is_resolved ? (
                          <button
                            onClick={() => {
                              setResolvingIssue(iss);
                              setCorrectedValue(iss.raw_value || '');
                              setResolutionComment('');
                            }}
                            className="px-2.5 py-1 bg-darkroom-card hover:bg-darkroom-border text-darkroom-gold border border-darkroom-gold/30 rounded text-[11px] font-semibold"
                          >
                            Resolve & Fix
                          </button>
                        ) : (
                          <span className="text-[11px] text-gray-500">
                            {iss.resolved_by || 'Audited'}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {filteredIssues.length === 0 && (
              <div className="p-10 text-center text-gray-500">
                No validation issues found for the selected filter.
              </div>
            )}
          </div>
        </>
      )}

      {/* Resolve Issue Modal */}
      {resolvingIssue && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-darkroom-surface border border-darkroom-border rounded-xl shadow-2xl p-6">
            <h3 className="text-sm font-bold text-gray-100 font-mono">
              Resolve Exception: {resolvingIssue.rule_name}
            </h3>
            <p className="text-xs text-gray-400 font-mono mt-1">
              Field: <span className="text-darkroom-gold">{resolvingIssue.column_name}</span> (Row #{resolvingIssue.row_index})
            </p>

            <form onSubmit={handleResolveSubmit} className="mt-4 space-y-4 font-mono text-xs">
              <div>
                <label className="block text-gray-300 mb-1">
                  Corrected Value (Will update dataset record)
                </label>
                <input
                  type="text"
                  value={correctedValue}
                  onChange={(e) => setCorrectedValue(e.target.value)}
                  className="w-full px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
                />
              </div>

              <div>
                <label className="block text-gray-300 mb-1">
                  Resolution Rationale / Note
                </label>
                <textarea
                  rows={2}
                  required
                  value={resolutionComment}
                  onChange={(e) => setResolutionComment(e.target.value)}
                  placeholder="e.g. Corrected typo against DHET registration gazette..."
                  className="w-full px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold font-sans"
                />
              </div>

              <div className="pt-3 border-t border-darkroom-border flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setResolvingIssue(null)}
                  className="px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-gray-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={resolveMutation.isPending}
                  className="px-4 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover font-bold rounded-lg shadow-sm"
                >
                  Apply Fix & Audit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
