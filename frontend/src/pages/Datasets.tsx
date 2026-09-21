import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  Database,
  ArrowRight,
  Trash2,
  Download,
  ShieldCheck,
  FileSpreadsheet,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';

export const Datasets: React.FC = () => {
  const queryClient = useQueryClient();
  const { selectedProjectId } = useAppStore();

  const { data: datasets = [], isLoading } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteDataset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight">
            Extracted Structured Datasets
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Database-ready tables normalized and verified from research documents
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {datasets.map((dataset) => {
          const score = dataset.quality_score;
          const scoreVariant =
            score >= 90 ? 'success' : score >= 75 ? 'warning' : 'danger';

          return (
            <div
              key={dataset.id}
              className="flex flex-col justify-between p-5 bg-darkroom-surface border border-darkroom-border hover:border-darkroom-borderLight rounded-xl transition-all font-mono"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <Database className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    <h2 className="text-sm font-bold text-gray-100 line-clamp-1">
                      {dataset.name}
                    </h2>
                  </div>
                  <button
                    onClick={() => {
                      if (confirm(`Delete dataset "${dataset.name}" and all records?`)) {
                        deleteMutation.mutate(dataset.id);
                      }
                    }}
                    className="p-1 text-gray-400 hover:text-rose-400 rounded"
                    title="Delete dataset"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>

                <p className="text-xs text-gray-400 mt-2 line-clamp-2 min-h-[2.5rem]">
                  {dataset.description || 'Normalized structured dataset.'}
                </p>

                {/* Badges */}
                <div className="flex items-center space-x-2 mt-3">
                  <Badge variant="gold">{dataset.schema_name}</Badge>
                  <Badge variant={scoreVariant}>{score}% Quality</Badge>
                  <span className="text-[11px] text-gray-500 capitalize">
                    {dataset.status}
                  </span>
                </div>
              </div>

              {/* Stats & Link */}
              <div className="mt-5 pt-3 border-t border-darkroom-border/80 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-3 text-gray-400">
                  <span className="text-gray-200 font-bold">
                    {dataset.record_count.toLocaleString()}
                  </span>
                  <span>records</span>
                </div>

                <Link
                  to={`/datasets/${dataset.id}`}
                  className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-darkroom-gold rounded-lg border border-darkroom-gold/30 text-xs font-semibold transition-colors"
                >
                  <span>Inspect Data</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          );
        })}
      </div>

      {datasets.length === 0 && !isLoading && (
        <div className="p-12 text-center bg-darkroom-surface border border-dashed border-darkroom-border rounded-xl">
          <Database className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-gray-300 font-mono">No Datasets Available</h3>
          <p className="text-xs text-gray-400 mt-1 max-w-sm mx-auto">
            Run an extraction pipeline on your uploaded PDF documents to generate validated datasets.
          </p>
          <Link
            to="/pipeline"
            className="inline-block mt-4 px-3 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            Launch Extraction Pipeline
          </Link>
        </div>
      )}
    </div>
  );
};
