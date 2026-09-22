import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Cpu,
  ShieldCheck,
  Zap,
  Server,
  Key,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Plus,
  Trash2,
  Sliders,
  DollarSign,
  Lock,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { Badge } from '../components/common/Badge';
import { ProviderConfig, ModelMetadata, AIModelConfig } from '../types';

export const AiModels: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'providers' | 'presets'>('providers');

  // Selected Provider for Credential/Test
  const [selectedProvider, setSelectedProvider] = useState<string>('deepseek');
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [baseUrlInput, setBaseUrlInput] = useState<string>('');
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency?: number } | null>(null);

  // New Preset State
  const [showPresetModal, setShowPresetModal] = useState(false);
  const [presetName, setPresetName] = useState('');
  const [presetProvider, setPresetProvider] = useState('deepseek');
  const [presetModel, setPresetModel] = useState('deepseek-reasoner');
  const [presetTemp, setPresetTemp] = useState(0.0);
  const [presetMaxTokens, setPresetMaxTokens] = useState(16000);
  const [presetReasoning, setPresetReasoning] = useState(true);
  const [presetVision, setPresetVision] = useState<'auto' | 'never' | 'always'>('auto');
  const [presetFallback, setPresetFallback] = useState('deepseek-chat');

  const { data: providers = [], isLoading: loadingProviders } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: apiClient.getProviders,
  });

  const { data: availableModels = [] } = useQuery({
    queryKey: ['ai-models-available'],
    queryFn: apiClient.getAvailableModels,
  });

  const { data: presets = [], isLoading: loadingPresets } = useQuery({
    queryKey: ['ai-presets'],
    queryFn: apiClient.getAIConfigs,
  });

  const saveCredentialsMutation = useMutation({
    mutationFn: apiClient.updateAICredentials,
    onSuccess: (res) => {
      alert(res.message);
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] });
      setApiKeyInput('');
    },
    onError: (err: any) => {
      alert('Failed to save credentials: ' + (err.response?.data?.detail || err.message));
    },
  });

  const testConnectionMutation = useMutation({
    mutationFn: apiClient.testAIConnection,
    onSuccess: (res) => {
      setTestResult({
        success: res.success,
        message: res.message,
        latency: res.latency_ms,
      });
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] });
    },
    onError: (err: any) => {
      setTestResult({
        success: false,
        message: err.response?.data?.detail || err.message,
      });
    },
  });

  const savePresetMutation = useMutation({
    mutationFn: apiClient.saveAIConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-presets'] });
      setShowPresetModal(false);
      setPresetName('');
    },
  });

  const deletePresetMutation = useMutation({
    mutationFn: apiClient.deleteAIConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-presets'] });
    },
  });

  const handleTestConnection = (provId: string) => {
    setTestResult(null);
    testConnectionMutation.mutate({
      provider: provId,
      api_key: apiKeyInput.trim() || undefined,
      base_url: baseUrlInput.trim() || undefined,
    });
  };

  const handleSaveCredentials = (provId: string) => {
    if (!apiKeyInput.trim() && !baseUrlInput.trim()) {
      alert('Please enter an API Key or Base URL.');
      return;
    }
    saveCredentialsMutation.mutate({
      provider: provId,
      api_key: apiKeyInput.trim() || undefined,
      base_url: baseUrlInput.trim() || undefined,
    });
  };

  const handleSavePreset = (e: React.FormEvent) => {
    e.preventDefault();
    if (!presetName.trim()) {
      alert('Please enter a preset name');
      return;
    }
    savePresetMutation.mutate({
      name: presetName.trim(),
      provider: presetProvider,
      model: presetModel,
      temperature: presetTemp,
      max_tokens: presetMaxTokens,
      reasoning_mode: presetReasoning,
      structured_output: true,
      use_vision: presetVision,
      fallback_model: presetFallback || undefined,
      timeout_seconds: 90,
      retry_count: 3,
      is_default: false,
    });
  };

  const currentProviderConfig = providers.find((p) => p.id === selectedProvider);
  const modelsForSelected = availableModels.filter((m) => m.provider === selectedProvider);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight flex items-center space-x-2">
            <Cpu className="w-5 h-5 text-darkroom-gold" />
            <span>AI Models & Intelligence Settings</span>
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Configure LLM providers, local on-premise models (Ollama), and named extraction presets
          </p>
        </div>

        {/* Tabs */}
        <div className="flex bg-darkroom-surface border border-darkroom-border rounded-lg p-1 space-x-1 font-mono text-xs">
          <button
            onClick={() => setActiveTab('providers')}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              activeTab === 'providers' ? 'bg-darkroom-gold text-black font-bold' : 'text-gray-400 hover:text-white'
            }`}
          >
            Providers & Credentials
          </button>
          <button
            onClick={() => setActiveTab('presets')}
            className={`px-3 py-1.5 rounded-md transition-colors ${
              activeTab === 'presets' ? 'bg-darkroom-gold text-black font-bold' : 'text-gray-400 hover:text-white'
            }`}
          >
            Named Presets ({presets.length})
          </button>
        </div>
      </div>

      {/* Local Mode Notice */}
      <div className="bg-emerald-950/40 border border-emerald-800/60 rounded-xl p-4 flex items-center justify-between text-xs font-mono text-emerald-200">
        <div className="flex items-center space-x-3">
          <ShieldCheck className="w-5 h-5 text-emerald-400 flex-shrink-0" />
          <div>
            <span className="font-bold text-emerald-300">Local Privacy Mode Supported:</span>{' '}
            For sensitive labour-market and confidential survey datasets, select the <strong>Ollama (Local)</strong> provider. Documents remain 100% on-premise without external network requests.
          </div>
        </div>
        <Badge variant="success">CONFIDENTIAL READY</Badge>
      </div>

      {activeTab === 'providers' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Provider Selection List */}
          <div className="lg:col-span-1 space-y-3">
            <div className="text-xs font-mono uppercase text-gray-400 font-semibold px-1">
              Supported Providers
            </div>
            {providers.map((p) => {
              const isSelected = p.id === selectedProvider;
              return (
                <div
                  key={p.id}
                  onClick={() => {
                    setSelectedProvider(p.id);
                    setTestResult(null);
                    setApiKeyInput('');
                  }}
                  className={`p-4 rounded-xl border cursor-pointer transition-all font-mono text-xs ${
                    isSelected
                      ? 'bg-darkroom-card border-darkroom-gold shadow-md'
                      : 'bg-darkroom-surface border-darkroom-border hover:border-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-gray-200">{p.name}</span>
                    <Badge variant={p.is_configured ? 'success' : 'default'}>
                      {p.is_configured ? 'CONFIGURED' : 'NEEDS SETUP'}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-gray-400 mt-2 line-clamp-2 leading-relaxed">
                    {p.description}
                  </p>
                  <div className="flex items-center space-x-2 mt-3 text-[10px] text-gray-500">
                    {p.is_local && (
                      <span className="px-1.5 py-0.5 bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 rounded">
                        LOCAL / OFFLINE
                      </span>
                    )}
                    {p.supports_vision && (
                      <span className="px-1.5 py-0.5 bg-indigo-950/60 border border-indigo-800/60 text-indigo-300 rounded">
                        MULTIMODAL VISION
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Provider Detail & Credential Setup */}
          <div className="lg:col-span-2 bg-darkroom-surface border border-darkroom-border rounded-xl p-6 space-y-6">
            {currentProviderConfig && (
              <>
                <div className="border-b border-darkroom-border pb-4 flex items-start justify-between">
                  <div>
                    <h2 className="text-base font-bold text-gray-100 font-mono">
                      {currentProviderConfig.name} Configuration
                    </h2>
                    <p className="text-xs text-gray-400 mt-1">
                      {currentProviderConfig.description}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Lock className="w-4 h-4 text-darkroom-gold" />
                    <span className="text-[11px] font-mono text-gray-400">Server-side Vault</span>
                  </div>
                </div>

                {/* Secure Credential Input */}
                <div className="space-y-4 font-mono text-xs">
                  {!currentProviderConfig.is_local ? (
                    <div>
                      <label className="block text-gray-300 mb-1 font-semibold">
                        API Key (Never sent to browser)
                      </label>
                      <div className="relative">
                        <input
                          type="password"
                          value={apiKeyInput}
                          onChange={(e) => setApiKeyInput(e.target.value)}
                          placeholder={currentProviderConfig.is_configured ? '••••••••••••••••••••••••••••' : 'Enter secret API key'}
                          className="w-full pl-9 pr-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
                        />
                        <Key className="w-4 h-4 text-gray-500 absolute left-3 top-2.5" />
                      </div>
                      <p className="text-[10px] text-gray-500 mt-1">
                        Stored securely in server storage or environment variable. Replaces existing key.
                      </p>
                    </div>
                  ) : (
                    <div>
                      <label className="block text-gray-300 mb-1 font-semibold">
                        Ollama Base URL
                      </label>
                      <input
                        type="text"
                        value={baseUrlInput}
                        onChange={(e) => setBaseUrlInput(e.target.value)}
                        placeholder="http://localhost:11434"
                        className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
                      />
                    </div>
                  )}

                  <div className="flex items-center space-x-3 pt-2">
                    <button
                      onClick={() => handleSaveCredentials(currentProviderConfig.id)}
                      disabled={saveCredentialsMutation.isPending}
                      className="px-4 py-2 bg-darkroom-gold text-black hover:bg-darkroom-goldHover font-bold rounded-lg transition-colors flex items-center space-x-2"
                    >
                      <span>{saveCredentialsMutation.isPending ? 'Saving...' : 'Save Credentials'}</span>
                    </button>

                    <button
                      onClick={() => handleTestConnection(currentProviderConfig.id)}
                      disabled={testConnectionMutation.isPending}
                      className="px-4 py-2 bg-darkroom-card hover:bg-darkroom-border border border-darkroom-border text-gray-200 font-semibold rounded-lg transition-colors flex items-center space-x-2"
                    >
                      <Zap className="w-3.5 h-3.5 text-amber-400" />
                      <span>{testConnectionMutation.isPending ? 'Testing Ping...' : 'Test Connection'}</span>
                    </button>
                  </div>

                  {/* Test Connection Output */}
                  {testResult && (
                    <div
                      className={`p-3.5 rounded-lg border flex items-start space-x-2.5 ${
                        testResult.success
                          ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
                          : 'bg-rose-950/40 border-rose-800/60 text-rose-300'
                      }`}
                    >
                      {testResult.success ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                      )}
                      <div className="space-y-0.5">
                        <div className="font-bold">
                          {testResult.success ? 'Connection Successful' : 'Connection Failed'}
                        </div>
                        <div className="text-[11px]">{testResult.message}</div>
                        {testResult.latency !== undefined && (
                          <div className="text-[10px] text-gray-400">
                            Latency: {testResult.latency}ms
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                {/* Available Models for this provider */}
                <div className="pt-4 border-t border-darkroom-border space-y-3 font-mono text-xs">
                  <div className="font-bold text-gray-300">
                    Registered Models for {currentProviderConfig.name}
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {modelsForSelected.map((m) => (
                      <div
                        key={m.model}
                        className="p-3 bg-darkroom-card border border-darkroom-border rounded-lg space-y-1.5"
                      >
                        <div className="font-bold text-gray-200 truncate">{m.display_name}</div>
                        <div className="text-[10px] text-gray-400">Model ID: {m.model}</div>
                        <div className="text-[10px] text-gray-500">
                          Context: {(m.context_window / 1000).toFixed(0)}k tokens
                        </div>
                        <div className="flex items-center space-x-1.5 pt-1">
                          {m.supports_reasoning && (
                            <span className="px-1 py-0.5 bg-amber-950/50 border border-amber-800/40 text-amber-300 text-[9px] rounded">
                              REASONING
                            </span>
                          )}
                          {m.supports_vision && (
                            <span className="px-1 py-0.5 bg-indigo-950/50 border border-indigo-800/40 text-indigo-300 text-[9px] rounded">
                              VISION
                            </span>
                          )}
                          <span className="text-[10px] text-gray-400 ml-auto">
                            {m.cost_input_per_million === 0 ? 'Free / Local' : `$${m.cost_input_per_million}/1M in`}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {activeTab === 'presets' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-gray-400">
              Named extraction configurations ready to invoke in extraction jobs
            </span>
            <button
              onClick={() => setShowPresetModal(true)}
              className="px-3 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-bold rounded-lg font-mono flex items-center space-x-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create New Preset</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {presets.map((cfg) => (
              <div
                key={cfg.id}
                className="bg-darkroom-surface border border-darkroom-border rounded-xl p-5 space-y-3 font-mono text-xs"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-gray-200 text-sm">{cfg.name}</h3>
                    <div className="text-[11px] text-gray-400 mt-0.5">
                      {cfg.provider.toUpperCase()} • {cfg.model}
                    </div>
                  </div>
                  {cfg.is_default && <Badge variant="gold">DEFAULT</Badge>}
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-darkroom-border text-[11px] text-gray-400">
                  <div>
                    Temp: <span className="text-gray-200">{cfg.temperature}</span>
                  </div>
                  <div>
                    Max Tokens: <span className="text-gray-200">{cfg.max_tokens}</span>
                  </div>
                  <div>
                    Reasoning:{' '}
                    <span className={cfg.reasoning_mode ? 'text-emerald-400' : 'text-gray-500'}>
                      {cfg.reasoning_mode ? 'Enabled' : 'Disabled'}
                    </span>
                  </div>
                  <div>
                    Vision: <span className="text-gray-200 uppercase">{cfg.use_vision}</span>
                  </div>
                </div>

                {cfg.fallback_model && (
                  <div className="text-[10px] text-gray-500">
                    Fallback: <span className="text-gray-400">{cfg.fallback_model}</span>
                  </div>
                )}

                <div className="pt-2 border-t border-darkroom-border flex justify-end">
                  <button
                    onClick={() => cfg.id && deletePresetMutation.mutate(cfg.id)}
                    className="p-1 text-gray-500 hover:text-rose-400 rounded"
                    title="Delete preset"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Preset Modal */}
      {showPresetModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl max-w-md w-full p-6 space-y-4 font-mono text-xs">
            <h2 className="text-sm font-bold text-gray-100 flex items-center space-x-2">
              <Sliders className="w-4 h-4 text-darkroom-gold" />
              <span>Create AI Extraction Preset</span>
            </h2>

            <form onSubmit={handleSavePreset} className="space-y-3">
              <div>
                <label className="block text-gray-300 mb-1">Preset Name *</label>
                <input
                  type="text"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                  placeholder="e.g. DeepSeek Labour Market High Precision"
                  className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-300 mb-1">Provider *</label>
                  <select
                    value={presetProvider}
                    onChange={(e) => setPresetProvider(e.target.value)}
                    className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
                  >
                    {providers.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-gray-300 mb-1">Model *</label>
                  <input
                    type="text"
                    value={presetModel}
                    onChange={(e) => setPresetModel(e.target.value)}
                    className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-gray-300 mb-1">Temperature</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    value={presetTemp}
                    onChange={(e) => setPresetTemp(parseFloat(e.target.value))}
                    className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
                  />
                </div>
                <div>
                  <label className="block text-gray-300 mb-1">Max Tokens</label>
                  <input
                    type="number"
                    value={presetMaxTokens}
                    onChange={(e) => setPresetMaxTokens(parseInt(e.target.value, 10))}
                    className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
                  />
                </div>
              </div>

              <div className="flex items-center space-x-3 pt-2">
                <button
                  type="submit"
                  disabled={savePresetMutation.isPending}
                  className="flex-1 py-2 bg-darkroom-gold text-black hover:bg-darkroom-goldHover font-bold rounded-lg transition-colors"
                >
                  Save Preset
                </button>
                <button
                  type="button"
                  onClick={() => setShowPresetModal(false)}
                  className="px-4 py-2 bg-darkroom-card hover:bg-darkroom-border border border-darkroom-border text-gray-300 rounded-lg"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
