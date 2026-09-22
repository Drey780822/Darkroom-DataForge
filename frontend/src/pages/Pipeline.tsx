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
  Cpu,
  ShieldAlert,
  Eye,
  Layers,
  Sparkles,
  Zap,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { ProgressBar } from '../components/common/ProgressBar';
import { Badge } from '../components/common/Badge';
import { DocumentIntelligenceMap, SchemaInferenceResponse } from '../types';

export const Pipeline: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedProjectId } = useAppStore();

  const preselectedDocs: string[] = location.state?.documentIds || [];

  const [projectId, setProjectId] = useState<string>(selectedProjectId || '');
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>(preselectedDocs);
  const [pipelineType, setPipelineType] = useState<string>('auto');
  const [extractionMode, setExtractionMode] = useState<string>('high_accuracy');
  const [selectedProvider, setSelectedProvider] = useState<string>('deepseek');
  const [selectedModel, setSelectedModel] = useState<string>('deepseek-reasoner');
  const [secondaryModel, setSecondaryModel] = useState<string>('qwen2.5');
  const [useVision, setUseVision] = useState<'auto' | 'never' | 'always'>('auto');
  const [datasetName, setDatasetName] = useState<string>('');
  const [pageRange, setPageRange] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Pre-extraction Intelligence & Schema Preview State
  const [inspectionMap, setInspectionMap] = useState<DocumentIntelligenceMap | null>(null);
  const [inspectingDoc, setInspectingDoc] = useState<boolean>(false);
  const [inferredSchema, setInferredSchema] = useState<SchemaInferenceResponse | null>(null);
  const [inferringSchema, setInferringSchema] = useState<boolean>(false);
  const [showSchemaModal, setShowSchemaModal] = useState<boolean>(false);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const { data: documents = [] } = useQuery({
    queryKey: ['documents', projectId],
    queryFn: () => apiClient.getDocuments(projectId || undefined),
  });

  const { data: providers = [] } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: apiClient.getProviders,
  });

  const { data: availableModels = [] } = useQuery({
    queryKey: ['ai-models-available'],
    queryFn: apiClient.getAvailableModels,
  });

  const { data: presets = [] } = useQuery({
    queryKey: ['ai-presets'],
    queryFn: apiClient.getAIConfigs,
  });

  const { data: jobs = [] } = useQuery({
    queryKey: ['extraction-jobs', projectId],
    queryFn: () => apiClient.getJobs(projectId || undefined),
    refetchInterval: (query) => {
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
      setInspectionMap(null);
      setInferredSchema(null);
      setShowSchemaModal(false);
    },
    onError: (err: any) => {
      setIsSubmitting(false);
      alert('Failed to start extraction job: ' + (err.response?.data?.detail || err.message));
    },
  });

  const handleInspectDocument = async (docId: string) => {
    setInspectingDoc(true);
    try {
      const map = await apiClient.inspectDocumentLayout(docId);
      setInspectionMap(map);
    } catch (e: any) {
      alert('Inspection failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setInspectingDoc(false);
    }
  };

  const handleInferSchema = async (docId: string) => {
    setInferringSchema(true);
    try {
      const sch = await apiClient.inferSchema({
        document_id: docId,
        dataset_name: datasetName.trim() || 'Dataset',
        provider: selectedProvider,
        model: selectedModel,
      });
      setInferredSchema(sch);
      setShowSchemaModal(true);
    } catch (e: any) {
      alert('Schema inference failed: ' + (e.response?.data?.detail || e.message));
    } finally {
      setInferringSchema(false);
    }
  };

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

    const parameters: Record<string, any> = {
      extraction_mode: extractionMode,
      provider: selectedProvider,
      model: selectedModel,
      use_vision: useVision,
      secondary_model: extractionMode === 'maximum_accuracy' ? secondaryModel : undefined,
    };

    if (inferredSchema && inferredSchema.fields.length > 0) {
      parameters.schema_override = inferredSchema.fields.map((f) => ({
        name: f.field_name,
        original_name: f.source_label,
        type: f.data_type,
        required: !f.nullable,
        identifier: f.identifier,
        description: f.description || f.source_label,
      }));
    }

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
      extraction_mode: extractionMode,
      provider: selectedProvider,
      model: selectedModel,
      secondary_model: extractionMode === 'maximum_accuracy' ? secondaryModel : undefined,
      parameters,
      target_dataset_name: datasetName.trim() || undefined,
    });
  };

  const toggleSelectDoc = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const modelsForSelected = availableModels.filter((m) => m.provider === selectedProvider);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight flex items-center space-x-2">
          <Workflow className="w-5 h-5 text-darkroom-gold" />
          <span>Intelligent Document Extraction Pipeline</span>
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Orchestrate layout reconstruction, table detection, LLM structured extraction, dual validation, and reconciliation
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pipeline Configuration Form */}
        <div className="lg:col-span-1 bg-darkroom-surface border border-darkroom-border rounded-xl p-5 space-y-4 font-mono text-xs">
          <div className="flex items-center space-x-2 text-darkroom-gold pb-2 border-b border-darkroom-border font-bold uppercase tracking-wider">
            <Sliders className="w-4 h-4" />
            <span>Extraction Configuration</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3.5">
            {/* Target Project */}
            <div>
              <label className="block text-gray-300 mb-1">Target Project *</label>
              <select
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
              >
                <option value="">Select Project...</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Extraction Mode Selector */}
            <div>
              <label className="block text-gray-300 mb-1 font-semibold flex items-center justify-between">
                <span>Extraction Mode *</span>
                <span className="text-[10px] text-darkroom-gold">
                  {extractionMode === 'high_accuracy' ? 'Recommended' : ''}
                </span>
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'fast', name: 'FAST', desc: 'Native tables first' },
                  { id: 'balanced', name: 'BALANCED', desc: 'LLM schema + extract' },
                  { id: 'high_accuracy', name: 'HIGH ACCURACY', desc: 'Deep verify pass' },
                  { id: 'maximum_accuracy', name: 'MAX ACCURACY', desc: 'Dual-model check' },
                ].map((m) => (
                  <button
                    type="button"
                    key={m.id}
                    onClick={() => setExtractionMode(m.id)}
                    className={`p-2 rounded-lg border text-left transition-all ${
                      extractionMode === m.id
                        ? 'bg-darkroom-card border-darkroom-gold text-darkroom-gold font-bold shadow-sm'
                        : 'bg-darkroom-bg border-darkroom-border text-gray-400 hover:text-gray-200'
                    }`}
                  >
                    <div className="text-[11px] font-bold">{m.name}</div>
                    <div className="text-[9px] text-gray-500">{m.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* AI Provider & Primary Model */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-gray-300 mb-1">AI Provider</label>
                <select
                  value={selectedProvider}
                  onChange={(e) => {
                    setSelectedProvider(e.target.value);
                    const p = providers.find((item) => item.id === e.target.value);
                    if (p) setSelectedModel(p.default_model);
                  }}
                  className="w-full px-2.5 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold text-[11px]"
                >
                  {providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} {p.is_local ? '(Local)' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-gray-300 mb-1">Primary Model</label>
                <input
                  type="text"
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold text-[11px]"
                />
              </div>
            </div>

            {/* Secondary Model for MAXIMUM_ACCURACY */}
            {extractionMode === 'maximum_accuracy' && (
              <div className="p-2.5 bg-amber-950/30 border border-amber-800/50 rounded-lg space-y-1 text-[11px]">
                <label className="block text-amber-300 font-bold">Secondary Verification Model</label>
                <input
                  type="text"
                  value={secondaryModel}
                  onChange={(e) => setSecondaryModel(e.target.value)}
                  placeholder="e.g. qwen2.5 or claude-3-5-haiku"
                  className="w-full px-2.5 py-1.5 bg-darkroom-bg border border-darkroom-border rounded text-gray-200 text-xs"
                />
                <p className="text-[10px] text-gray-400">
                  Model A and Model B will independently extract records. Disagreements enter the Review Queue with source page anchoring.
                </p>
              </div>
            )}

            {/* Vision & Multimodal Toggle */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-gray-300 mb-1">Vision Escalation</label>
                <select
                  value={useVision}
                  onChange={(e) => setUseVision(e.target.value as any)}
                  className="w-full px-2.5 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold text-[11px]"
                >
                  <option value="auto">Auto (If Scanned)</option>
                  <option value="never">Never (Text Only)</option>
                  <option value="always">Always (Render Pages)</option>
                </select>
              </div>

              <div>
                <label className="block text-gray-300 mb-1">Profile Archetype</label>
                <select
                  value={pipelineType}
                  onChange={(e) => setPipelineType(e.target.value)}
                  className="w-full px-2.5 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold text-[11px]"
                >
                  <option value="auto">Auto-Detect Profile</option>
                  <option value="qualifications">DHET TVET Qualifications</option>
                  <option value="occupations">OIHD Occupations & OFO</option>
                  <option value="codebook">Survey Codebook (QLFS)</option>
                  <option value="pdf_tables">Native PDF Tables</option>
                </select>
              </div>
            </div>

            {/* Custom Dataset Name & Page Range */}
            <div>
              <label className="block text-gray-300 mb-1">Target Dataset Name</label>
              <input
                type="text"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                placeholder="Defaults to document name"
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
              />
            </div>

            <div>
              <label className="block text-gray-300 mb-1">Page Selection (Optional)</label>
              <input
                type="text"
                value={pageRange}
                onChange={(e) => setPageRange(e.target.value)}
                placeholder="e.g. 1, 2, 3 or leave blank for all"
                className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
              />
            </div>

            {/* Select Documents */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-gray-300 font-semibold">
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
                    className="text-[11px] text-darkroom-gold hover:underline"
                  >
                    {selectedDocIds.length === documents.length ? 'Clear' : 'Select All'}
                  </button>
                )}
              </div>

              <div className="max-h-40 overflow-y-auto bg-darkroom-bg border border-darkroom-border rounded-lg p-2 space-y-1">
                {documents.map((doc) => {
                  const isChecked = selectedDocIds.includes(doc.id);
                  return (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between p-1.5 hover:bg-darkroom-card rounded"
                    >
                      <label className="flex items-center space-x-2 cursor-pointer flex-1 truncate">
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleSelectDoc(doc.id)}
                          className="rounded bg-darkroom-surface border-gray-700 text-darkroom-gold focus:ring-0"
                        />
                        <span className="truncate text-gray-300" title={doc.original_name}>
                          {doc.original_name}
                        </span>
                      </label>
                      <button
                        type="button"
                        onClick={() => handleInspectDocument(doc.id)}
                        className="p-1 text-gray-500 hover:text-darkroom-gold rounded ml-2"
                        title="Inspect Layout Map"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Pre-Inspection Preview Info */}
            {selectedDocIds.length === 1 && (
              <div className="flex items-center space-x-2 pt-1">
                <button
                  type="button"
                  onClick={() => handleInspectDocument(selectedDocIds[0])}
                  disabled={inspectingDoc}
                  className="flex-1 py-1.5 bg-darkroom-card hover:bg-darkroom-border border border-darkroom-border rounded text-[11px] text-gray-300 flex items-center justify-center space-x-1.5"
                >
                  <Eye className="w-3.5 h-3.5 text-sky-400" />
                  <span>{inspectingDoc ? 'Inspecting Layout...' : 'Inspect Intelligence Map'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleInferSchema(selectedDocIds[0])}
                  disabled={inferringSchema}
                  className="flex-1 py-1.5 bg-darkroom-card hover:bg-darkroom-border border border-darkroom-border rounded text-[11px] text-gray-300 flex items-center justify-center space-x-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5 text-darkroom-gold" />
                  <span>{inferringSchema ? 'Inferring...' : 'Preview Schema'}</span>
                </button>
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting || selectedDocIds.length === 0}
              className="w-full py-2.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover disabled:opacity-50 font-bold rounded-lg transition-colors flex items-center justify-center space-x-2 mt-2 shadow-sm"
            >
              <Play className="w-4 h-4" />
              <span>{isSubmitting ? 'Dispatching Pipeline...' : 'Start Intelligent Extraction'}</span>
            </button>
          </form>
        </div>

        {/* Pipeline Execution Queue & Intelligence Live Telemetry */}
        <div className="lg:col-span-2 space-y-4">
          {/* Document Intelligence Map Drawer (if inspected) */}
          {inspectionMap && (
            <div className="bg-darkroom-card border border-darkroom-border rounded-xl p-4 space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between pb-2 border-b border-darkroom-border">
                <div className="flex items-center space-x-2 text-sky-400 font-bold">
                  <Eye className="w-4 h-4" />
                  <span>Document Intelligence Map: {inspectionMap.filename}</span>
                </div>
                <button
                  onClick={() => setInspectionMap(null)}
                  className="text-gray-500 hover:text-white text-[10px]"
                >
                  Dismiss
                </button>
              </div>

              <div className="grid grid-cols-4 gap-2 text-[11px] text-gray-400">
                <div>Pages: <span className="text-gray-200 font-bold">{inspectionMap.page_count}</span></div>
                <div>Density: <span className="text-gray-200 font-bold">{inspectionMap.text_density_avg}</span></div>
                <div>Tables: <span className="text-darkroom-gold font-bold">{inspectionMap.tables.length}</span></div>
                <div>
                  Scanned:{' '}
                  <span className={inspectionMap.is_scanned ? 'text-rose-400 font-bold' : 'text-emerald-400'}>
                    {inspectionMap.is_scanned ? 'YES (OCR/Vision)' : 'NO (Native Text)'}
                  </span>
                </div>
              </div>

              {inspectionMap.continuation_groups.length > 0 && (
                <div className="text-[11px] text-amber-300 bg-amber-950/30 border border-amber-800/40 p-2 rounded">
                  <strong>Continuation Tables Found:</strong> Spanning pages{' '}
                  {inspectionMap.continuation_groups.map((g) => `[${g.join('-')}]`).join(', ')}. Context overlap chunking active.
                </div>
              )}
            </div>
          )}

          {/* Execution Queue */}
          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl p-5 space-y-4 flex flex-col font-mono text-xs">
            <div className="flex items-center justify-between pb-2 border-b border-darkroom-border">
              <div className="flex items-center space-x-2 text-gray-200 font-bold uppercase tracking-wider">
                <Workflow className="w-4 h-4 text-emerald-400" />
                <span>Asynchronous Pipeline Queue</span>
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
                    className="p-4 bg-darkroom-card border border-darkroom-border rounded-xl space-y-3"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-bold text-gray-200">Job #{job.id.slice(0, 8)}</span>
                          <Badge
                            variant={
                              isCompleted ? 'success' : isFailed ? 'danger' : isRunning ? 'gold' : 'default'
                            }
                          >
                            {job.status.toUpperCase()}
                          </Badge>
                          <span className="text-[10px] text-darkroom-gold uppercase">
                            {job.extraction_mode || 'HIGH ACCURACY'}
                          </span>
                        </div>
                        <div className="text-[11px] text-gray-400 mt-1">
                          Model: <span className="text-gray-200">{job.primary_model || job.pipeline_type}</span>
                          {job.secondary_model && (
                            <span className="text-amber-400 ml-1.5">vs {job.secondary_model}</span>
                          )}
                          {' • '}
                          Stage: <span className="text-emerald-400 capitalize">{job.step_status || 'Executing'}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-2">
                        {isCompleted && job.conflicts && job.conflicts.length > 0 && (
                          <Link
                            to="/review"
                            className="flex items-center space-x-1 px-2 py-1 bg-amber-950/60 border border-amber-800/80 text-amber-300 hover:bg-amber-900 rounded text-xs"
                          >
                            <AlertTriangle className="w-3 h-3 text-amber-400" />
                            <span>{job.conflicts.length} Conflicts</span>
                          </Link>
                        )}

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
                    </div>

                    {/* Progress Bar */}
                    <ProgressBar progress={job.progress} showPercentage />

                    {/* Telemetry Metrics */}
                    {job.metrics && Object.keys(job.metrics).length > 0 && (
                      <div className="grid grid-cols-4 gap-2 pt-2 border-t border-darkroom-border/60 text-[11px] text-gray-400">
                        <div>
                          Rows: <span className="text-gray-200 font-bold">{job.metrics.records_extracted}</span>
                        </div>
                        <div>
                          Score: <span className="text-darkroom-gold font-bold">{job.metrics.quality_score}%</span>
                        </div>
                        <div>
                          Tokens:{' '}
                          <span className="text-gray-200">
                            {job.metrics.tokens_used ? `${(job.metrics.tokens_used / 1000).toFixed(1)}k` : 'N/A'}
                          </span>
                        </div>
                        <div>
                          Cost:{' '}
                          <span className="text-emerald-400">
                            {job.metrics.estimated_cost_usd !== undefined
                              ? `$${job.metrics.estimated_cost_usd.toFixed(4)}`
                              : 'Local'}
                          </span>
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
                <div className="py-16 text-center text-gray-500">
                  No extraction jobs running or queued. Configure a document on the left and click Start.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Inferred Schema Review Modal */}
      {showSchemaModal && inferredSchema && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl max-w-2xl w-full p-6 space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-darkroom-border pb-3">
              <div>
                <h2 className="text-sm font-bold text-gray-100 flex items-center space-x-2">
                  <Sparkles className="w-4 h-4 text-darkroom-gold" />
                  <span>Inferred Schema: {inferredSchema.dataset_name}</span>
                </h2>
                <p className="text-[11px] text-gray-400 mt-0.5">{inferredSchema.description}</p>
              </div>
              <Badge variant="gold">PASS 2 COMPLETE</Badge>
            </div>

            <div className="max-h-72 overflow-y-auto border border-darkroom-border rounded-lg">
              <table className="w-full text-left border-collapse">
                <thead className="bg-darkroom-card border-b border-darkroom-border sticky top-0 text-[10px] text-gray-400">
                  <tr>
                    <th className="p-2">Field Name</th>
                    <th className="p-2">Source Label</th>
                    <th className="p-2">Type</th>
                    <th className="p-2">Identifier</th>
                    <th className="p-2">Nullable</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-darkroom-border text-[11px]">
                  {inferredSchema.fields.map((f, idx) => (
                    <tr key={idx} className="hover:bg-darkroom-card/50">
                      <td className="p-2 font-bold text-darkroom-gold">{f.field_name}</td>
                      <td className="p-2 text-gray-300">{f.source_label}</td>
                      <td className="p-2 text-sky-400">{f.data_type}</td>
                      <td className="p-2 text-gray-300">{f.identifier ? 'YES' : 'NO'}</td>
                      <td className="p-2 text-gray-400">{f.nullable ? 'YES' : 'NO'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-darkroom-border">
              <span className="text-[11px] text-gray-400">
                Recommended Chunk Size: {inferredSchema.recommended_chunk_size} pages
              </span>
              <div className="flex items-center space-x-2">
                <button
                  type="button"
                  onClick={() => setShowSchemaModal(false)}
                  className="px-4 py-2 bg-darkroom-gold text-black hover:bg-darkroom-goldHover font-bold rounded-lg"
                >
                  Accept Schema & Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
