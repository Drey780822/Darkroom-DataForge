import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { History, Database, UserCheck, ArrowRight, ShieldAlert } from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';

export const Review: React.FC = () => {
  const { selectedProjectId } = useAppStore();
  const [activeDatasetId, setActiveDatasetId] = useState<string>('');

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  useEffect(() => {
    if (!activeDatasetId && datasets.length > 0) {
      setActiveDatasetId(datasets[0].id);
    }
  }, [datasets, activeDatasetId]);

  const { data: reviews = [], isLoading } = useQuery({
    queryKey: ['reviews', activeDatasetId],
    queryFn: () => apiClient.getDatasetReviews(activeDatasetId),
    enabled: !!activeDatasetId,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight">
            Human-in-the-Loop Review & Audit Trail
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Immutable log of all researcher overrides, validation resolutions, and manual edits
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
                {d.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Review Log Table */}
      <div className="bg-darkroom-surface border border-darkroom-border rounded-xl overflow-hidden shadow-sm font-mono text-xs">
        <div className="p-3 bg-darkroom-card border-b border-darkroom-border flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <History className="w-4 h-4 text-darkroom-gold" />
            <span className="font-bold text-gray-200">Audit History Entries</span>
            <span className="text-gray-500">({reviews.length} logs)</span>
          </div>
        </div>

        <div className="overflow-x-auto max-h-[65vh]">
          <table className="w-full text-left">
            <thead className="bg-darkroom-card/60 border-b border-darkroom-border text-gray-400">
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

        {reviews.length === 0 && !isLoading && (
          <div className="p-12 text-center text-gray-400 font-mono text-xs">
            No manual review modifications logged yet for this dataset.
          </div>
        )}
      </div>
    </div>
  );
};
