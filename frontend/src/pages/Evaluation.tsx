import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Award,
  Upload,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  FileSpreadsheet,
  BarChart2,
  Layers,
  ArrowRight,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { Badge } from '../components/common/Badge';
import { EvaluationReport } from '../types';

export const Evaluation: React.FC = () => {
  const queryClient = useQueryClient();
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [goldenFile, setGoldenFile] = useState<File | null>(null);
  const [goldenName, setGoldenName] = useState<string>('');
  const [currentReport, setCurrentReport] = useState<EvaluationReport | null>(null);

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => apiClient.getDatasets(),
  });

  const { data: historicalRuns = [] } = useQuery({
    queryKey: ['evaluation-runs', selectedDatasetId],
    queryFn: () => apiClient.getEvaluationRuns(selectedDatasetId || undefined),
  });

  const runMutation = useMutation({
    mutationFn: apiClient.runEvaluation,
    onSuccess: (report) => {
      setCurrentReport(report);
      queryClient.invalidateQueries({ queryKey: ['evaluation-runs'] });
    },
    onError: (err: any) => {
      alert('Evaluation benchmark failed: ' + (err.response?.data?.detail || err.message));
    },
  });

  const handleRunEvaluation = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDatasetId) {
      alert('Please select a dataset to evaluate.');
      return;
    }

    const formData = new FormData();
    formData.append('dataset_id', selectedDatasetId);
    if (goldenName) {
      formData.append('golden_name', goldenName);
    }
    if (goldenFile) {
      formData.append('golden_file', goldenFile);
    }

    runMutation.mutate(formData);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight flex items-center space-x-2">
          <Award className="w-5 h-5 text-darkroom-gold" />
          <span>Golden Dataset Evaluation Benchmarking</span>
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Benchmark LLM extraction precision, recall, and field accuracy against verified ground-truth research datasets
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Benchmark Runner Form */}
        <div className="lg:col-span-1 bg-darkroom-surface border border-darkroom-border rounded-xl p-5 space-y-4 font-mono text-xs">
          <div className="flex items-center space-x-2 text-darkroom-gold pb-2 border-b border-darkroom-border font-bold uppercase tracking-wider">
            <Play className="w-4 h-4" />
            <span>Configure Benchmark Run</span>
          </div>

          <form onSubmit={handleRunEvaluation} className="space-y-4">
            <div>
              <label className="block text-gray-300 mb-1">Target Extracted Dataset *</label>
              <select
                value={selectedDatasetId}
                onChange={(e) => {
                  setSelectedDatasetId(e.target.value);
                  setCurrentReport(null);
                }}
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
                required
              >
                <option value="">Select Dataset...</option>
                {datasets.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name} ({d.record_count} rows)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-gray-300 mb-1">Golden Benchmark Name (Optional)</label>
              <input
                type="text"
                value={goldenName}
                onChange={(e) => setGoldenName(e.target.value)}
                placeholder="e.g. DHET TVET 2024 Verified Master"
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
              />
            </div>

            <div>
              <label className="block text-gray-300 mb-1">Upload Ground-Truth Golden CSV *</label>
              <div className="border border-dashed border-darkroom-border rounded-lg p-4 text-center bg-darkroom-bg hover:border-darkroom-gold transition-colors cursor-pointer">
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => e.target.files && setGoldenFile(e.target.files[0])}
                  className="hidden"
                  id="golden-file-input"
                />
                <label htmlFor="golden-file-input" className="cursor-pointer block">
                  <Upload className="w-6 h-6 text-gray-400 mx-auto mb-1" />
                  <span className="text-gray-300 font-semibold block">
                    {goldenFile ? goldenFile.name : 'Choose Ground-Truth CSV'}
                  </span>
                  <span className="text-[10px] text-gray-500">
                    {goldenFile ? `${(goldenFile.size / 1024).toFixed(1)} KB` : 'Or leave empty to test against built-in benchmarks'}
                  </span>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={runMutation.isPending || !selectedDatasetId}
              className="w-full py-2.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover disabled:opacity-50 font-bold rounded-lg transition-colors flex items-center justify-center space-x-2"
            >
              <Play className="w-4 h-4" />
              <span>{runMutation.isPending ? 'Benchmarking Quality...' : 'Execute Evaluation Run'}</span>
            </button>
          </form>

          {/* Past Runs for selected dataset */}
          {historicalRuns.length > 0 && (
            <div className="pt-4 border-t border-darkroom-border space-y-2">
              <div className="font-bold text-gray-400 uppercase tracking-wider text-[11px]">
                Historical Runs
              </div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {historicalRuns.map((r) => (
                  <div
                    key={r.id}
                    onClick={() => setCurrentReport(r)}
                    className="p-2 bg-darkroom-card hover:bg-darkroom-border rounded cursor-pointer flex items-center justify-between text-[11px]"
                  >
                    <span className="truncate flex-1 text-gray-300">{r.golden_dataset_name}</span>
                    <span className="font-bold text-darkroom-gold ml-2">{r.field_accuracy}% Acc</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Evaluation Report Display */}
        <div className="lg:col-span-2 bg-darkroom-surface border border-darkroom-border rounded-xl p-6 space-y-6 font-mono text-xs">
          {currentReport ? (
            <>
              {/* Top Summary Banner */}
              <div className="border-b border-darkroom-border pb-4 flex items-start justify-between">
                <div>
                  <h2 className="text-base font-bold text-gray-100 flex items-center space-x-2">
                    <Award className="w-5 h-5 text-darkroom-gold" />
                    <span>Evaluation Report: {currentReport.golden_dataset_name}</span>
                  </h2>
                  <div className="text-[11px] text-gray-400 mt-1">
                    Evaluated on {new Date(currentReport.evaluated_at).toLocaleString()}
                  </div>
                </div>
                <Badge variant={currentReport.field_accuracy > 90 ? 'success' : 'warning'}>
                  {currentReport.field_accuracy > 90 ? 'HIGH FIDELITY' : 'REVIEW RECOMMENDED'}
                </Badge>
              </div>

              {/* KPI Cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3.5 bg-darkroom-card border border-darkroom-border rounded-lg space-y-1">
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider">Record Recall</div>
                  <div className="text-xl font-bold text-emerald-400">{currentReport.record_recall}%</div>
                  <div className="text-[10px] text-gray-500">
                    {currentReport.matched_records_count} / {currentReport.total_expected_records} captured
                  </div>
                </div>

                <div className="p-3.5 bg-darkroom-card border border-darkroom-border rounded-lg space-y-1">
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider">Record Precision</div>
                  <div className="text-xl font-bold text-sky-400">{currentReport.record_precision}%</div>
                  <div className="text-[10px] text-gray-500">
                    {currentReport.matched_records_count} / {currentReport.total_actual_records} valid
                  </div>
                </div>

                <div className="p-3.5 bg-darkroom-card border border-darkroom-border rounded-lg space-y-1">
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider">Field Accuracy</div>
                  <div className="text-xl font-bold text-darkroom-gold">{currentReport.field_accuracy}%</div>
                  <div className="text-[10px] text-gray-500">
                    {currentReport.field_mismatches_count} mismatched cells
                  </div>
                </div>

                <div className="p-3.5 bg-darkroom-card border border-darkroom-border rounded-lg space-y-1">
                  <div className="text-[10px] text-gray-400 uppercase tracking-wider">F1 Score</div>
                  <div className="text-xl font-bold text-indigo-400">{currentReport.record_f1_score}%</div>
                  <div className="text-[10px] text-gray-500">Harmonic mean</div>
                </div>
              </div>

              {/* Detailed Breakdown */}
              <div className="grid grid-cols-3 gap-2 py-2 border-y border-darkroom-border text-[11px]">
                <div className="text-gray-400">
                  Expected Records: <span className="font-bold text-gray-200">{currentReport.total_expected_records}</span>
                </div>
                <div className="text-rose-400">
                  Missing Records: <span className="font-bold">{currentReport.missing_records_count}</span>
                </div>
                <div className="text-amber-400">
                  Extra/Hallucinated: <span className="font-bold">{currentReport.extra_records_count}</span>
                </div>
              </div>

              {/* Mismatches List */}
              <div className="space-y-3">
                <div className="font-bold text-gray-300">
                  Field Mismatches ({currentReport.mismatches.length})
                </div>
                {currentReport.mismatches.length > 0 ? (
                  <div className="max-h-64 overflow-y-auto border border-darkroom-border rounded-lg">
                    <table className="w-full text-left border-collapse">
                      <thead className="bg-darkroom-card border-b border-darkroom-border sticky top-0 text-[10px] text-gray-400">
                        <tr>
                          <th className="p-2">Row</th>
                          <th className="p-2">Field</th>
                          <th className="p-2">Expected (Golden)</th>
                          <th className="p-2">Actual (Extracted)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-darkroom-border text-[11px]">
                        {currentReport.mismatches.map((m, idx) => (
                          <tr key={idx} className="hover:bg-darkroom-card/50">
                            <td className="p-2 text-gray-500">#{m.row_index}</td>
                            <td className="p-2 font-bold text-darkroom-gold">{m.field_name}</td>
                            <td className="p-2 text-emerald-400 bg-emerald-950/20">{String(m.expected_value)}</td>
                            <td className="p-2 text-rose-400 bg-rose-950/20">{String(m.actual_value)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="p-6 text-center text-emerald-400 bg-emerald-950/20 border border-emerald-800/40 rounded-lg">
                    <CheckCircle2 className="w-6 h-6 mx-auto mb-1" />
                    <span>Zero field mismatches! Every matched field corresponds 100% to the ground truth.</span>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="py-24 text-center text-gray-500 space-y-2">
              <BarChart2 className="w-8 h-8 mx-auto text-gray-600" />
              <div className="text-sm font-bold text-gray-400">No Evaluation Report Selected</div>
              <p className="text-xs max-w-sm mx-auto">
                Select a dataset and ground-truth CSV on the left to compute research precision, recall, and field accuracy metrics.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
