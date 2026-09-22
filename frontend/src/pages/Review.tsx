import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  History,
  Database,
  ArrowRight,
  ShieldAlert,
  GitCompare,
  FileText,
  Eye,
  CheckCircle,
  XCircle,
  Edit3,
  AlertTriangle,
  Layers,
  Filter,
  Check,
  X,
  Bot,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';
import { ConflictRecord, ExtractionJob, ValidationIssue } from '../types';

export const Review: React.FC = () => {
  const queryClient = useQueryClient();
  const { selectedProjectId, openSourceModal } = useAppStore();

  const [activeTab, setActiveTab] = useState<'conflicts' | 'validation' | 'audit'>('conflicts');
  const [selectedJobId, setSelectedJobId] = useState<string>('');
  const [activeDatasetId, setActiveDatasetId] = useState<string>('');
  const [conflictFilter, setConflictFilter] = useState<string>('all');
  const [customOverrideModal, setCustomOverrideModal] = useState<ConflictRecord | null>(null);
  const [customValue, setCustomValue] = useState<string>('');
  const [customComment, setCustomComment] = useState<string>('');
  const [reviewerName, setReviewerName] = useState<string>('Lead Researcher');

  // Fetch extraction jobs to get jobs with conflicts
  const { data: jobs = [] } = useQuery({
    queryKey: ['jobs', selectedProjectId],
    queryFn: () => apiClient.getJobs(selectedProjectId || undefined),
  });

  // Fetch datasets
  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  // Set default active job
  useEffect(() => {
    if (!selectedJobId && jobs.length > 0) {
      // Prefer job with conflicts or high_accuracy
      const jobWithConflicts = jobs.find((j) => (j.conflicts && j.conflicts.length > 0));
      setSelectedJobId(jobWithConflicts ? jobWithConflicts.id : jobs[0].id);
    }
  }, [jobs, selectedJobId]);

  // Set default active dataset
  useEffect(() => {
    if (!activeDatasetId && datasets.length > 0) {
      setActiveDatasetId(datasets[0].id);
    }
  }, [datasets, activeDatasetId]);

  // Active Job Details
  const activeJob = jobs.find((j) => j.id === selectedJobId);

  // Fetch conflicts for active job
  const { data: conflicts = [], isLoading: isLoadingConflicts } = useQuery({
    queryKey: ['conflicts', selectedJobId],
    queryFn: () => apiClient.getJobConflicts(selectedJobId),
    enabled: !!selectedJobId,
  });

  // Fetch validation issues for active dataset
  const { data: validationSummary, isLoading: isLoadingValidation } = useQuery({
    queryKey: ['validation-summary', activeDatasetId],
    queryFn: () => apiClient.getValidationSummary(activeDatasetId),
    enabled: !!activeDatasetId,
  });

  // Fetch audit reviews for active dataset
  const { data: reviews = [], isLoading: isLoadingReviews } = useQuery({
    queryKey: ['reviews', activeDatasetId],
    queryFn: () => apiClient.getDatasetReviews(activeDatasetId),
    enabled: !!activeDatasetId,
  });

  // Resolve conflict mutation
  const resolveConflictMutation = useMutation({
    mutationFn: ({
      conflictId,
      resolution,
      resolvedValue,
      comment,
    }: {
      conflictId: string;
      resolution: string;
      resolvedValue?: any;
      comment?: string;
    }) =>
      apiClient.resolveJobConflict(selectedJobId, {
        conflict_id: conflictId,
        resolution,
        resolved_value: resolvedValue,
        comment,
        resolved_by: reviewerName,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conflicts', selectedJobId] });
      queryClient.invalidateQueries({ queryKey: ['jobs', selectedProjectId] });
      setCustomOverrideModal(null);
      setCustomValue('');
      setCustomComment('');
    },
  });

  // Filtered conflicts
  const filteredConflicts = conflicts.filter((c) => {
    if (conflictFilter === 'requires_review') return c.resolution === 'requires_review';
    if (conflictFilter === 'resolved') return c.resolution !== 'requires_review';
    return true;
  });

  const pendingConflictCount = conflicts.filter((c) => c.resolution === 'requires_review').length;
  const validationIssues: ValidationIssue[] = validationSummary?.issues || [];
  const pendingValidationCount = validationIssues.filter((i) => !i.is_resolved).length;

  const handleOpenSource = (page: number) => {
    const docId = activeJob?.parameters?.document_id || activeJob?.parameters?.document_ids?.[0];
    openSourceModal({
      documentId: docId || '',
      documentName: 'Source Document',
      pageNumber: page,
    });
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight flex items-center space-x-2">
            <span>Human-in-the-Loop Review Queue</span>
            <span className="text-xs px-2 py-0.5 rounded bg-darkroom-gold/10 text-darkroom-gold border border-darkroom-gold/30">
              Workstation Audit
            </span>
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Single-source-of-truth reconciliation: verify multi-model discrepancies, resolve schema validation flags, and maintain immutable provenance.
          </p>
        </div>

        {/* Global Reviewer Identity */}
        <div className="flex items-center space-x-3 text-xs font-mono">
          <span className="text-gray-400">Reviewer:</span>
          <input
            type="text"
            value={reviewerName}
            onChange={(e) => setReviewerName(e.target.value)}
            className="px-2.5 py-1 bg-darkroom-surface border border-darkroom-border rounded text-darkroom-gold focus:outline-none focus:border-darkroom-gold text-xs"
            placeholder="Researcher Name"
          />
        </div>
      </div>

      {/* Primary Tab Navigation */}
      <div className="flex border-b border-darkroom-border space-x-2">
        <button
          onClick={() => setActiveTab('conflicts')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-all ${
            activeTab === 'conflicts'
              ? 'border-darkroom-gold text-darkroom-gold bg-darkroom-surface/50'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <GitCompare className="w-4 h-4" />
          <span>Multi-Model Discrepancies</span>
          {pendingConflictCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30">
              {pendingConflictCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('validation')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-all ${
            activeTab === 'validation'
              ? 'border-darkroom-gold text-darkroom-gold bg-darkroom-surface/50'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <ShieldAlert className="w-4 h-4" />
          <span>Validation Exceptions</span>
          {pendingValidationCount > 0 && (
            <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500/20 text-amber-300 font-bold border border-amber-500/30">
              {pendingValidationCount}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('audit')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-mono font-medium border-b-2 transition-all ${
            activeTab === 'audit'
              ? 'border-darkroom-gold text-darkroom-gold bg-darkroom-surface/50'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Audit Log & Provenance</span>
          <span className="text-gray-500">({reviews.length})</span>
        </button>
      </div>

      {/* TAB 1: MULTI-MODEL CONFLICTS */}
      {activeTab === 'conflicts' && (
        <div className="space-y-4">
          {/* Sub-bar: Job Selector & Filter */}
          <div className="flex flex-wrap items-center justify-between gap-3 bg-darkroom-surface p-3.5 rounded-xl border border-darkroom-border font-mono text-xs">
            <div className="flex items-center space-x-3">
              <span className="text-gray-400">Extraction Job:</span>
              <select
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                className="px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
              >
                {jobs.map((job) => (
                  <option key={job.id} value={job.id}>
                    Job #{job.id.slice(0, 8)} ({job.extraction_mode || 'standard'}) • {job.status} • {job.conflicts?.length || 0} conflicts
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center space-x-3">
              <span className="text-gray-400">Filter:</span>
              <select
                value={conflictFilter}
                onChange={(e) => setConflictFilter(e.target.value)}
                className="px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
              >
                <option value="all">All Conflicts ({conflicts.length})</option>
                <option value="requires_review">Requires Review ({pendingConflictCount})</option>
                <option value="resolved">Resolved ({conflicts.length - pendingConflictCount})</option>
              </select>
            </div>
          </div>

          {/* Job Overview Metadata Banner */}
          {activeJob && (
            <div className="bg-darkroom-card/80 border border-darkroom-border p-3.5 rounded-xl font-mono text-xs flex flex-wrap items-center justify-between gap-4">
              <div className="flex items-center space-x-4">
                <div>
                  <span className="text-gray-500 text-[10px] block uppercase">Primary Model</span>
                  <span className="text-sky-300 font-bold flex items-center space-x-1 mt-0.5">
                    <Bot className="w-3.5 h-3.5" />
                    <span>{activeJob.primary_model || 'Primary LLM'}</span>
                  </span>
                </div>
                <div className="text-gray-600 font-bold">vs</div>
                <div>
                  <span className="text-gray-500 text-[10px] block uppercase">Secondary Model</span>
                  <span className="text-emerald-300 font-bold flex items-center space-x-1 mt-0.5">
                    <Sparkles className="w-3.5 h-3.5" />
                    <span>{activeJob.secondary_model || 'Secondary LLM'}</span>
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-6">
                <div>
                  <span className="text-gray-500 text-[10px] block uppercase">Extraction Mode</span>
                  <span className="text-darkroom-gold font-bold uppercase">{activeJob.extraction_mode || 'BALANCED'}</span>
                </div>
                <div>
                  <span className="text-gray-500 text-[10px] block uppercase">Total Conflicts</span>
                  <span className="text-gray-200 font-bold">{conflicts.length}</span>
                </div>
                <div>
                  <span className="text-gray-500 text-[10px] block uppercase">Action Required</span>
                  <span className={pendingConflictCount > 0 ? 'text-rose-400 font-bold' : 'text-emerald-400 font-bold'}>
                    {pendingConflictCount} pending
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Conflicts Table */}
          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl overflow-hidden shadow-sm font-mono text-xs">
            <div className="overflow-x-auto max-h-[60vh]">
              <table className="w-full text-left">
                <thead className="bg-darkroom-card/90 sticky top-0 z-10 border-b border-darkroom-border text-gray-300">
                  <tr>
                    <th className="p-3 w-16 text-center">Row</th>
                    <th className="p-3">Field</th>
                    <th className="p-3">Source Page</th>
                    <th className="p-3">Model A Extraction</th>
                    <th className="p-3">Model B Extraction</th>
                    <th className="p-3">Status</th>
                    <th className="p-3 text-right">Human Resolution</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-darkroom-border/60 text-gray-300">
                  {filteredConflicts.map((c, idx) => {
                    const isPending = c.resolution === 'requires_review';
                    const conflictId = c.id || String(idx);
                    return (
                      <tr key={conflictId} className="hover:bg-darkroom-card/50 transition-colors">
                        <td className="p-3 text-center text-gray-400 font-bold">
                          #{c.row_index}
                        </td>
                        <td className="p-3 font-semibold text-gray-100">
                          {c.field_name}
                        </td>
                        <td className="p-3">
                          <button
                            onClick={() => handleOpenSource(c.source_page)}
                            className="flex items-center space-x-1.5 px-2 py-1 bg-darkroom-navy/60 hover:bg-darkroom-navy text-darkroom-gold border border-darkroom-gold/30 rounded text-[11px] transition-colors"
                            title="Jump to source PDF page"
                          >
                            <FileText className="w-3 h-3 text-darkroom-gold" />
                            <span>Page {c.source_page}</span>
                            <Eye className="w-3 h-3 ml-0.5 opacity-70" />
                          </button>
                        </td>

                        {/* Model A */}
                        <td className="p-3 max-w-xs">
                          <div className="p-2 bg-sky-950/30 border border-sky-900/50 rounded-lg">
                            <div className="text-[10px] text-sky-400 font-semibold mb-0.5">
                              {c.model_a}
                            </div>
                            <div className="text-gray-100 break-words font-mono font-medium">
                              {c.value_a !== null && c.value_a !== undefined ? String(c.value_a) : <span className="italic text-gray-500">null</span>}
                            </div>
                          </div>
                        </td>

                        {/* Model B */}
                        <td className="p-3 max-w-xs">
                          <div className="p-2 bg-emerald-950/30 border border-emerald-900/50 rounded-lg">
                            <div className="text-[10px] text-emerald-400 font-semibold mb-0.5">
                              {c.model_b}
                            </div>
                            <div className="text-gray-100 break-words font-mono font-medium">
                              {c.value_b !== null && c.value_b !== undefined ? String(c.value_b) : <span className="italic text-gray-500">null</span>}
                            </div>
                          </div>
                        </td>

                        {/* Status */}
                        <td className="p-3">
                          {c.resolution === 'requires_review' && (
                            <Badge variant="danger">NEEDS REVIEW</Badge>
                          )}
                          {c.resolution === 'accepted_a' && (
                            <Badge variant="navy">ACCEPTED A</Badge>
                          )}
                          {c.resolution === 'accepted_b' && (
                            <Badge variant="success">ACCEPTED B</Badge>
                          )}
                          {c.resolution === 'manual_override' && (
                            <Badge variant="gold">MANUAL OVERRIDE</Badge>
                          )}
                          {c.resolution === 'rejected' && (
                            <Badge variant="default">REJECTED</Badge>
                          )}
                          {c.resolved_by && (
                            <div className="text-[10px] text-gray-500 mt-1">
                              by {c.resolved_by}
                            </div>
                          )}
                        </td>

                        {/* Resolution Actions */}
                        <td className="p-3 text-right">
                          {isPending ? (
                            <div className="flex items-center justify-end space-x-1.5">
                              <button
                                onClick={() =>
                                  resolveConflictMutation.mutate({
                                    conflictId,
                                    resolution: 'accepted_a',
                                    resolvedValue: c.value_a,
                                    comment: `Accepted Model A (${c.model_a}) extraction`,
                                  })
                                }
                                disabled={resolveConflictMutation.isPending}
                                className="px-2 py-1 bg-sky-900/60 hover:bg-sky-800 text-sky-200 border border-sky-700/60 rounded text-[11px] font-semibold transition-colors"
                                title="Accept Model A value"
                              >
                                Accept A
                              </button>
                              <button
                                onClick={() =>
                                  resolveConflictMutation.mutate({
                                    conflictId,
                                    resolution: 'accepted_b',
                                    resolvedValue: c.value_b,
                                    comment: `Accepted Model B (${c.model_b}) extraction`,
                                  })
                                }
                                disabled={resolveConflictMutation.isPending}
                                className="px-2 py-1 bg-emerald-900/60 hover:bg-emerald-800 text-emerald-200 border border-emerald-700/60 rounded text-[11px] font-semibold transition-colors"
                                title="Accept Model B value"
                              >
                                Accept B
                              </button>
                              <button
                                onClick={() => {
                                  setCustomOverrideModal(c);
                                  setCustomValue(String(c.value_a ?? ''));
                                }}
                                className="px-2 py-1 bg-darkroom-gold/20 hover:bg-darkroom-gold/30 text-darkroom-gold border border-darkroom-gold/40 rounded text-[11px] font-semibold transition-colors"
                                title="Enter custom researcher value"
                              >
                                Edit
                              </button>
                              <button
                                onClick={() =>
                                  resolveConflictMutation.mutate({
                                    conflictId,
                                    resolution: 'rejected',
                                    comment: 'Discrepant record rejected by researcher',
                                  })
                                }
                                disabled={resolveConflictMutation.isPending}
                                className="p-1 hover:bg-rose-950/50 text-gray-500 hover:text-rose-400 rounded transition-colors"
                                title="Reject Both"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ) : (
                            <div className="text-[11px] text-gray-400 text-right">
                              <span className="text-emerald-400 font-semibold">Resolved: </span>
                              <span className="text-gray-200 font-mono">
                                {c.resolved_value !== undefined ? String(c.resolved_value) : '-'}
                              </span>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {filteredConflicts.length === 0 && !isLoadingConflicts && (
              <div className="p-12 text-center text-gray-400 font-mono text-xs">
                {conflicts.length === 0
                  ? 'No model discrepancies detected for this job. Both extractors agree or single-model mode was used.'
                  : 'No conflicts matching filter.'}
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: VALIDATION EXCEPTIONS */}
      {activeTab === 'validation' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 bg-darkroom-surface p-3.5 rounded-xl border border-darkroom-border font-mono text-xs">
            <div className="flex items-center space-x-3">
              <span className="text-gray-400">Target Dataset:</span>
              <select
                value={activeDatasetId}
                onChange={(e) => setActiveDatasetId(e.target.value)}
                className="px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.quality_score}% Quality)
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center space-x-2 text-gray-400">
              <span>Total Exceptions: {validationIssues.length}</span>
              <span>•</span>
              <span className="text-rose-400 font-semibold">{pendingValidationCount} Pending</span>
            </div>
          </div>

          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl overflow-hidden shadow-sm font-mono text-xs">
            <div className="overflow-x-auto max-h-[60vh]">
              <table className="w-full text-left">
                <thead className="bg-darkroom-card/90 sticky top-0 z-10 border-b border-darkroom-border text-gray-300">
                  <tr>
                    <th className="p-3 w-16 text-center">Row</th>
                    <th className="p-3">Severity</th>
                    <th className="p-3">Column</th>
                    <th className="p-3">Validation Message</th>
                    <th className="p-3">Source Evidence</th>
                    <th className="p-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-darkroom-border/60 text-gray-300">
                  {validationIssues.map((issue) => (
                    <tr key={issue.id} className="hover:bg-darkroom-card/50 transition-colors">
                      <td className="p-3 text-center text-gray-400 font-bold">
                        #{issue.row_index}
                      </td>
                      <td className="p-3">
                        <Badge
                          variant={
                            issue.severity === 'error'
                              ? 'danger'
                              : issue.severity === 'warning'
                              ? 'warning'
                              : 'navy'
                          }
                        >
                          {issue.severity.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="p-3 font-semibold text-gray-100">
                        {issue.column_name || 'Generic'}
                      </td>
                      <td className="p-3 max-w-md text-gray-200">
                        {issue.message}
                      </td>
                      <td className="p-3">
                        <span className="text-gray-400 text-[11px]">
                          {issue.rule_name || 'Validation Rule'}
                        </span>
                      </td>
                      <td className="p-3">
                        {issue.is_resolved ? (
                          <Badge variant="success">RESOLVED</Badge>
                        ) : (
                          <Badge variant="danger">OPEN</Badge>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {validationIssues.length === 0 && !isLoadingValidation && (
              <div className="p-12 text-center text-gray-400 font-mono text-xs">
                Zero validation issues found! Dataset passed all deterministic and LLM consistency checks.
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: AUDIT TRAIL */}
      {activeTab === 'audit' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between bg-darkroom-surface p-3.5 rounded-xl border border-darkroom-border font-mono text-xs">
            <div className="flex items-center space-x-3">
              <Database className="w-4 h-4 text-darkroom-gold" />
              <span className="text-gray-400">Dataset Audit Log:</span>
              <select
                value={activeDatasetId}
                onChange={(e) => setActiveDatasetId(e.target.value)}
                className="px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
              >
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="text-gray-400 font-mono">
              Total Recorded Overrides: {reviews.length}
            </div>
          </div>

          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl overflow-hidden shadow-sm font-mono text-xs">
            <div className="overflow-x-auto max-h-[60vh]">
              <table className="w-full text-left">
                <thead className="bg-darkroom-card/90 sticky top-0 z-10 border-b border-darkroom-border text-gray-300">
                  <tr>
                    <th className="p-3">Timestamp</th>
                    <th className="p-3">Action</th>
                    <th className="p-3">Record ID</th>
                    <th className="p-3">Field</th>
                    <th className="p-3">Change (Old → New)</th>
                    <th className="p-3">Reviewer Rationale</th>
                    <th className="p-3">Reviewer</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-darkroom-border/60 text-gray-300">
                  {reviews.map((rev) => (
                    <tr key={rev.id} className="hover:bg-darkroom-card/50 transition-colors">
                      <td className="p-3 text-gray-400 text-[11px]">
                        {new Date(rev.created_at).toLocaleString()}
                      </td>
                      <td className="p-3">
                        <Badge
                          variant={
                            rev.action.includes('approve')
                              ? 'success'
                              : rev.action.includes('reject')
                              ? 'danger'
                              : rev.action.includes('flag')
                              ? 'warning'
                              : 'gold'
                          }
                        >
                          {rev.action.replace('_', ' ').toUpperCase()}
                        </Badge>
                      </td>
                      <td className="p-3 text-gray-400 text-[11px] font-mono">
                        #{rev.record_id.slice(0, 8)}
                      </td>
                      <td className="p-3 font-semibold text-gray-200">
                        {rev.field_name || '-'}
                      </td>
                      <td className="p-3 max-w-xs">
                        {rev.field_name ? (
                          <div className="flex items-center space-x-1.5 text-[11px]">
                            <span className="text-rose-400 line-through truncate max-w-[100px]">
                              {rev.old_value || 'empty'}
                            </span>
                            <ArrowRight className="w-3 h-3 text-gray-500 flex-shrink-0" />
                            <span className="text-emerald-400 font-bold truncate max-w-[100px]">
                              {rev.new_value}
                            </span>
                          </div>
                        ) : (
                          <span className="text-gray-500 text-[11px]">-</span>
                        )}
                      </td>
                      <td className="p-3 text-gray-300 max-w-sm">
                        {rev.reason || 'Manual review verified'}
                      </td>
                      <td className="p-3 text-darkroom-gold font-medium">
                        {rev.reviewed_by}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {reviews.length === 0 && !isLoadingReviews && (
              <div className="p-12 text-center text-gray-400 font-mono text-xs">
                No manual review modifications logged yet for this dataset.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Custom Override Modal */}
      {customOverrideModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono text-xs">
          <div className="w-full max-w-md bg-darkroom-surface border border-darkroom-border rounded-xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-darkroom-border">
              <h3 className="text-sm font-bold text-gray-100 flex items-center space-x-2">
                <Edit3 className="w-4 h-4 text-darkroom-gold" />
                <span>Resolve Conflict: {customOverrideModal.field_name}</span>
              </h3>
              <button
                onClick={() => setCustomOverrideModal(null)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3 bg-darkroom-card rounded-lg border border-darkroom-border space-y-2">
              <div className="flex justify-between text-gray-400">
                <span>Model A ({customOverrideModal.model_a}):</span>
                <span className="text-sky-300 font-semibold">{String(customOverrideModal.value_a)}</span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Model B ({customOverrideModal.model_b}):</span>
                <span className="text-emerald-300 font-semibold">{String(customOverrideModal.value_b)}</span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Source PDF:</span>
                <span className="text-darkroom-gold font-semibold">Page {customOverrideModal.source_page}</span>
              </div>
            </div>

            <div>
              <label className="block text-gray-300 mb-1">
                Researcher Corrected Value <span className="text-darkroom-gold">*</span>
              </label>
              <input
                type="text"
                value={customValue}
                onChange={(e) => setCustomValue(e.target.value)}
                placeholder="Enter verified value..."
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-100 focus:outline-none focus:border-darkroom-gold"
              />
            </div>

            <div>
              <label className="block text-gray-300 mb-1">
                Audit Rationale / Document Reference
              </label>
              <textarea
                rows={2}
                value={customComment}
                onChange={(e) => setCustomComment(e.target.value)}
                placeholder="e.g. Verified from Table 4 footnote on page 14..."
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-100 focus:outline-none focus:border-darkroom-gold"
              />
            </div>

            <div className="pt-3 border-t border-darkroom-border flex justify-end space-x-2">
              <button
                type="button"
                onClick={() => setCustomOverrideModal(null)}
                className="px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-gray-300 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={resolveConflictMutation.isPending || !customValue.trim()}
                onClick={() =>
                  resolveConflictMutation.mutate({
                    conflictId: customOverrideModal.id || '',
                    resolution: 'manual_override',
                    resolvedValue: customValue,
                    comment: customComment,
                  })
                }
                className="px-4 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover font-semibold rounded-lg shadow-sm disabled:opacity-50"
              >
                Save & Apply Resolution
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
