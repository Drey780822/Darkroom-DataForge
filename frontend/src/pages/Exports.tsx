import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Download,
  FileSpreadsheet,
  FileCode,
  FileText,
  Database,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { ExportResponse } from '../types';

export const Exports: React.FC = () => {
  const location = useLocation();
  const { selectedProjectId } = useAppStore();

  const defaultDsId = location.state?.defaultDatasetId;

  const [activeDatasetId, setActiveDatasetId] = useState<string>(defaultDsId || '');
  const [format, setFormat] = useState<string>('csv');
  const [includeProvenance, setIncludeProvenance] = useState<boolean>(true);
  const [onlyValidRecords, setOnlyValidRecords] = useState<boolean>(false);
  const [lastExport, setLastExport] = useState<ExportResponse | null>(null);

  const { data: datasets = [] } = useQuery({
    queryKey: ['datasets', selectedProjectId],
    queryFn: () => apiClient.getDatasets(selectedProjectId || undefined),
  });

  useEffect(() => {
    if (!activeDatasetId && datasets.length > 0) {
      setActiveDatasetId(datasets[0].id);
    }
  }, [datasets, activeDatasetId]);

  const exportMutation = useMutation({
    mutationFn: () =>
      apiClient.exportDataset(activeDatasetId, {
        format,
        include_provenance: includeProvenance,
        only_valid_records: onlyValidRecords,
      }),
    onSuccess: (data) => {
      setLastExport(data);
    },
    onError: (err: any) => {
      alert('Export failed: ' + (err.response?.data?.detail || err.message));
    },
  });

  const activeDataset = datasets.find((d) => d.id === activeDatasetId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight">
          Dataset Exporter
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Generate production-ready machine-readable datasets in CSV, JSON, and Excel formats
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Export Configuration Form */}
        <div className="bg-darkroom-surface border border-darkroom-border rounded-xl p-5 space-y-4 font-mono text-xs">
          <div className="flex items-center space-x-2 text-darkroom-gold pb-2 border-b border-darkroom-border font-bold uppercase tracking-wider">
            <Download className="w-4 h-4" />
            <span>Export Configuration</span>
          </div>

          <div>
            <label className="block text-gray-300 mb-1">Select Dataset *</label>
            <select
              value={activeDatasetId}
              onChange={(e) => setActiveDatasetId(e.target.value)}
              className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-200 focus:outline-none focus:border-darkroom-gold"
            >
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} ({d.record_count} records)
                </option>
              ))}
            </select>
          </div>

          {/* Format Selection Cards */}
          <div>
            <label className="block text-gray-300 mb-2">Target File Format *</label>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setFormat('csv')}
                className={`p-3 rounded-xl border flex flex-col items-center justify-center space-y-2 transition-all ${
                  format === 'csv'
                    ? 'border-darkroom-gold bg-darkroom-goldLight text-darkroom-gold'
                    : 'border-darkroom-border bg-darkroom-bg text-gray-400 hover:text-gray-200'
                }`}
              >
                <FileText className="w-6 h-6" />
                <span className="font-bold">CSV</span>
              </button>

              <button
                type="button"
                onClick={() => setFormat('xlsx')}
                className={`p-3 rounded-xl border flex flex-col items-center justify-center space-y-2 transition-all ${
                  format === 'xlsx'
                    ? 'border-darkroom-gold bg-darkroom-goldLight text-darkroom-gold'
                    : 'border-darkroom-border bg-darkroom-bg text-gray-400 hover:text-gray-200'
                }`}
              >
                <FileSpreadsheet className="w-6 h-6" />
                <span className="font-bold">Excel (.xlsx)</span>
              </button>

              <button
                type="button"
                onClick={() => setFormat('json')}
                className={`p-3 rounded-xl border flex flex-col items-center justify-center space-y-2 transition-all ${
                  format === 'json'
                    ? 'border-darkroom-gold bg-darkroom-goldLight text-darkroom-gold'
                    : 'border-darkroom-border bg-darkroom-bg text-gray-400 hover:text-gray-200'
                }`}
              >
                <FileCode className="w-6 h-6" />
                <span className="font-bold">JSON</span>
              </button>
            </div>
          </div>

          {/* Options Checkboxes */}
          <div className="space-y-2 pt-2 border-t border-darkroom-border">
            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={includeProvenance}
                onChange={(e) => setIncludeProvenance(e.target.checked)}
                className="rounded bg-darkroom-bg border-gray-700 text-darkroom-gold focus:ring-0"
              />
              <span className="text-gray-300">
                Include Provenance Columns (_prov_doc, _prov_page, _prov_confidence)
              </span>
            </label>

            <label className="flex items-center space-x-2 cursor-pointer">
              <input
                type="checkbox"
                checked={onlyValidRecords}
                onChange={(e) => setOnlyValidRecords(e.target.checked)}
                className="rounded bg-darkroom-bg border-gray-700 text-darkroom-gold focus:ring-0"
              />
              <span className="text-gray-300">
                Filter: Only export validated / reviewed records
              </span>
            </label>
          </div>

          <button
            onClick={() => exportMutation.mutate()}
            disabled={!activeDatasetId || exportMutation.isPending}
            className="w-full flex items-center justify-center space-x-2 py-2.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover disabled:opacity-50 font-bold rounded-lg shadow-sm transition-colors"
          >
            <Download className="w-4 h-4" />
            <span>{exportMutation.isPending ? 'Generating File...' : 'Generate & Download Export'}</span>
          </button>
        </div>

        {/* Export Result Preview */}
        <div className="bg-darkroom-surface border border-darkroom-border rounded-xl p-5 space-y-4 font-mono text-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-2 text-gray-200 pb-2 border-b border-darkroom-border font-bold uppercase tracking-wider">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Export Summary & Download</span>
            </div>

            {lastExport ? (
              <div className="mt-4 p-4 bg-darkroom-card border border-emerald-800/50 rounded-xl space-y-3">
                <div className="flex items-center space-x-2 text-emerald-400 font-bold">
                  <CheckCircle2 className="w-5 h-5" />
                  <span>Export Ready for Download</span>
                </div>

                <div className="space-y-1 text-gray-300 text-[11px]">
                  <div>File: <span className="font-bold text-gray-100">{lastExport.filename}</span></div>
                  <div>Format: <span className="uppercase text-darkroom-gold">{lastExport.format}</span></div>
                  <div>Records: <span>{lastExport.record_count.toLocaleString()}</span></div>
                  <div>Size: <span>{(lastExport.file_size_bytes / 1024).toFixed(1)} KB</span></div>
                </div>

                <a
                  href={lastExport.download_url}
                  download={lastExport.filename}
                  className="mt-3 inline-flex items-center justify-center space-x-2 w-full py-2 bg-emerald-500 hover:bg-emerald-400 text-black font-bold rounded-lg shadow-sm"
                >
                  <Download className="w-4 h-4" />
                  <span>Download {lastExport.filename}</span>
                </a>
              </div>
            ) : (
              <div className="py-16 text-center text-gray-500">
                Configure your export settings and click "Generate & Download Export" to build your dataset file.
              </div>
            )}
          </div>

          {activeDataset && (
            <div className="p-3 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-400 text-[11px]">
              <div>Target Schema: <span className="text-gray-200">{activeDataset.schema_name}</span></div>
              <div>Columns: <span className="text-gray-200">{activeDataset.schema_columns.length}</span></div>
              <div>Available Rows: <span className="text-gray-200">{activeDataset.record_count}</span></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
