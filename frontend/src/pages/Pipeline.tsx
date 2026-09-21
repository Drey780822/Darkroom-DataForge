import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Workflow,
  Play,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
  RefreshCw,
  FileText,
  Sliders,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { ProgressBar } from '../components/common/ProgressBar';
import { Badge } from '../components/common/Badge';

export const Pipeline: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedProjectId } = useAppStore();

  const preselectedDocs: string[] = location.state?.documentIds || [];

  const [projectId, setProjectId] = useState<string>(selectedProjectId || '');
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>(preselectedDocs);
  const [pipelineType, setPipelineType] = useState<string>('auto');
  const [datasetName, setDatasetName] = useState<string>('');
  const [pageRange, setPageRange] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const { data: documents = [] } = useQuery({
    queryKey: ['documents', projectId],
    queryFn: () => apiClient.getDocuments(projectId || undefined),
  });

  const { data: jobs = [] } = useQuery({
    queryKey: ['extraction-jobs', projectId],
    queryFn: () => apiClient.getJobs(projectId || undefined),
    refetchInterval: (query) => {
      // If any job is running or pending, poll every 2s
      const data = query.state.data;
      if (data && data.some((j) => j.status === 'running' || j.status === 'pending')) {
        return 2000;
      }
      return 10000;
    },
  });

  useEffect(() => {
    if (!projectId && projects.length > 0) {
      setProjectId(projects[0].id);
    }
  }, [projects, projectId]);

  const runMutation = useMutation({
    mutationFn: apiClient.createJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['extraction-jobs'] });
      setIsSubmitting(false);
      setDatasetName('');
      setPageRange('');
    },
    onError: (err: any) => {
      setIsSubmitting(false);
      alert('Failed to start extraction job: ' + (err.response?.data?.detail || err.message));
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId) {
      alert('Please choose a target project.');
      return;
    }
    if (selectedDocIds.length === 0) {
      alert('Please select at least one document to process.');
      return;
    }

    setIsSubmitting(true);

    const parameters: Record<string, any> = {};
    if (pageRange.trim()) {
      const parsedPages = pageRange
        .split(',')
        .map((p) => parseInt(p.trim(), 10))
        .filter((n) => !isNaN(n) && n > 0);
      if (parsedPages.length > 0) {
        parameters.pages = parsedPages;
      }
    }

    runMutation.mutate({
      project_id: projectId,
      document_ids: selectedDocIds,
      pipeline_type: pipelineType,
      parameters,
      target_dataset_name: datasetName.trim() || undefined,
    });
  };

  const toggleSelectDoc = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight">
          Extraction Pipeline Runner
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Execute automated document intelligence, normalization, and validation pipelines
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline Configuration Form */}
        <div className="lg:col-span-1 bg-darkroom-surface border border-darkroom-border rounded-xl p-5 space-y-4">
          <div className="flex items-center space-x-2 text-darkroom-gold pb-2 border-b border-darkroom-border font-mono text-xs font-bold uppercase tracking-wider">
            <Sliders className="w-4 h-4" />
            <span>Pipeline Configuration</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Target Project */}
            <div>
              <label className="block text-xs font-mono text-gray-300 mb-1">
                Target Project *
              </label>
              <select
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 font-mono focus:outline-none focus:border-darkroom-gold"
              >
                <option value="">Select Project...</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Pipeline Strategy */}
            <div>
              <label className="block text-xs font-mono text-gray-300 mb-1">
                Extraction Pipeline Model *
              </label>
              <select
                value={pipelineType}
                onChange={(e) => setPipelineType(e.target.value)}
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 font-mono focus:outline-none focus:border-darkroom-gold"
              >
                <option value="auto">Auto-Select Model by Document Profile</option>
                <option value="qualifications">DHET TVET Qualifications Parser</option>
                <option value="occupations">OIHD High-Demand Occupations & OFO</option>
                <option value="codebook">Survey Metadata Codebook (QLFS)</option>
                <option value="pdf_tables">Native Lattice / Stream Tables</option>
              </select>
            </div>

            {/* Custom Dataset Name */}
            <div>
              <label className="block text-xs font-mono text-gray-300 mb-1">
                Dataset Name (Optional)
              </label>
              <input
                type="text"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                placeholder="Defaults to document name"
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 font-mono focus:outline-none focus:border-darkroom-gold"
              />
            </div>

            {/* Page Range */}
            <div>
              <label className="block text-xs font-mono text-gray-300 mb-1">
                Page Selection (Optional)
              </label>
              <input
                type="text"
                value={pageRange}
                onChange={(e) => setPageRange(e.target.value)}
                placeholder="e.g. 1, 2, 3 or leave blank for all"
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 font-mono focus:outline-none focus:border-darkroom-gold"
              />
            </div>

            {/* Select Documents */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-mono text-gray-300">
                  Select Documents ({selectedDocIds.length} chosen) *
                </label>
                {documents.length > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      if (selectedDocIds.length === documents.length) {
                        setSelectedDocIds([]);
                      } else {
                        setSelectedDocIds(documents.map((d) => d.id));
                      }
                    }}
                    className="text-[11px] font-mono text-darkroom-gold hover:underline"
                  >
                    {selectedDocIds.length === documents.length ? 'Clear' : 'Select All'}
                  </button>
                )}
              </div>

              <div className="max-h-48 overflow-y-auto bg-darkroom-bg border border-darkroom-border rounded-lg p-2 space-y-1">
                {documents.map((doc) => {
                  const isChecked = selectedDocIds.includes(doc.id);
                  return (
                    <label
                      key={doc.id}
                      className="flex items-center space-x-2 p-1.5 hover:bg-darkroom-card rounded cursor-pointer text-xs font-mono text-gray-300"
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelectDoc(doc.id)}
                        className="rounded bg-darkroom-surface border-gray-700 text-darkroom-gold focus:ring-0"
                      />
                      <span className="truncate flex-1" title={doc.original_name}>
                        {doc.original_name}
                      </span>
                      <span className="text-[10px] text-gray-500">{doc.page_count}p</span>
                    </label>
                  );
                })}
                {documents.length === 0 && (
                  <div className="p-4 text-center text-gray-500 text-xs font-mono">
                    No documents available in this project.
                  </div>
                )}
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || selectedDocIds.length === 0}
              className="w-full flex items-center justify-center space-x-2 py-2.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover disabled:opacity-50 text-xs font-bold rounded-lg shadow-sm font-mono transition-colors"
            >
              <Play className="w-4 h-4" />
              <span>{isSubmitting ? 'Starting Job...' : 'Execute Extraction Pipeline'}</span>
            </button>
          </form>
        </div>

        {/* Extraction Jobs Queue */}
        <div className="lg:col-span-2 bg-darkroom-surface border border-darkroom-border rounded-xl p-5 space-y-4 flex flex-col">
          <div className="flex items-center justify-between pb-2 border-b border-darkroom-border font-mono text-xs">
            <div className="flex items-center space-x-2 text-gray-200 font-bold uppercase tracking-wider">
              <Workflow className="w-4 h-4 text-emerald-400" />
              <span>Pipeline Execution Queue</span>
            </div>
            <button
              onClick={() => queryClient.invalidateQueries({ queryKey: ['extraction-jobs'] })}
              className="p-1 text-gray-400 hover:text-white rounded"
              title="Refresh queue"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3">
            {jobs.map((job) => {
              const isRunning = job.status === 'running';
              const isCompleted = job.status === 'completed';
              const isFailed = job.status === 'failed';

              return (
                <div
                  key={job.id}
                  className="p-4 bg-darkroom-card border border-darkroom-border rounded-xl space-y-3 font-mono text-xs"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-gray-200">
                          Job #{job.id.slice(0, 8)}
                        </span>
                        <Badge
                          variant={
                            isCompleted ? 'success' : isFailed ? 'danger' : isRunning ? 'gold' : 'default'
                          }
                        >
                          {job.status.toUpperCase()}
                        </Badge>
                        <span className="text-[11px] text-gray-400">
                          Model: {job.pipeline_type}
                        </span>
                      </div>
                      <div className="text-[11px] text-gray-500 mt-1">
                        Started: {new Date(job.created_at).toLocaleString()}
                      </div>
                    </div>

                    {isCompleted && job.dataset_id && (
                      <Link
                        to={`/datasets/${job.dataset_id}`}
                        className="flex items-center space-x-1.5 px-3 py-1 bg-darkroom-gold text-black hover:bg-darkroom-goldHover rounded text-xs font-semibold"
                      >
                        <span>Inspect Dataset</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    )}
                  </div>

                  {/* Progress Bar */}
                  <ProgressBar progress={job.progress} showPercentage />

                  {/* Execution Metrics */}
                  {job.metrics && Object.keys(job.metrics).length > 0 && (
                    <div className="grid grid-cols-4 gap-2 pt-2 border-t border-darkroom-border/60 text-[11px] text-gray-400">
                      <div>
                        Rows: <span className="text-gray-200 font-bold">{job.metrics.records_extracted}</span>
                      </div>
                      <div>
                        Valid: <span className="text-emerald-400 font-bold">{job.metrics.valid_records}</span>
                      </div>
                      <div>
                        Score: <span className="text-darkroom-gold font-bold">{job.metrics.quality_score}%</span>
                      </div>
                      <div>
                        Duration: <span className="text-gray-200">{job.metrics.duration_ms}ms</span>
                      </div>
                    </div>
                  )}

                  {isFailed && job.error_message && (
                    <div className="p-2.5 bg-rose-950/40 border border-rose-800/60 rounded text-rose-300 text-xs">
                      Error: {job.error_message}
                    </div>
                  )}
                </div>
              );
            })}

            {jobs.length === 0 && (
              <div className="py-12 text-center text-gray-500 font-mono text-xs">
                No jobs executed yet. Use the configuration form on the left to trigger a pipeline.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
