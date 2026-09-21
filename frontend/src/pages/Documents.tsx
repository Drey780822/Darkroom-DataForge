import React, { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  UploadCloud,
  FileText,
  Search,
  Eye,
  Play,
  Trash2,
  CheckCircle2,
  FileSearch,
  X,
  Layers,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';
import { Document, DocumentInspection } from '../types';

export const Documents: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { selectedProjectId, openSourceModal } = useAppStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [search, setSearch] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProjectId, setUploadProjectId] = useState(selectedProjectId || '');
  const [uploadDocType, setUploadDocType] = useState('auto');
  const [inspectingDoc, setInspectingDoc] = useState<Document | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const { data: documents = [], isLoading } = useQuery({
    queryKey: ['documents', selectedProjectId],
    queryFn: () => apiClient.getDocuments(selectedProjectId || undefined),
  });

  const { data: inspectionData, isLoading: isInspecting } = useQuery({
    queryKey: ['document-inspect', inspectingDoc?.id],
    queryFn: () => apiClient.inspectDocument(inspectingDoc!.id),
    enabled: !!inspectingDoc,
  });

  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteDocument,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      setSelectedDocIds([]);
    },
  });

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const targetProjId = uploadProjectId || (projects.length > 0 ? projects[0].id : null);
    if (!targetProjId) {
      alert('Please select or create a project first before uploading documents.');
      return;
    }

    setIsUploading(true);
    try {
      await apiClient.uploadDocuments(
        targetProjId,
        Array.from(files),
        uploadDocType === 'auto' ? undefined : uploadDocType
      );
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    } catch (err: any) {
      alert('Upload failed: ' + (err.response?.data?.detail || err.message));
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const filteredDocs = documents.filter((doc) =>
    doc.original_name.toLowerCase().includes(search.toLowerCase()) ||
    doc.doc_type.toLowerCase().includes(search.toLowerCase())
  );

  const docTypeBadgeVariant = (type: string) => {
    switch (type) {
      case 'qualifications':
        return 'gold';
      case 'occupations':
        return 'navy';
      case 'codebook':
        return 'success';
      default:
        return 'default';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight">
            Document Repository
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Ingest, inspect, classify, and stage PDF documents for structured table extraction
          </p>
        </div>

        {selectedDocIds.length > 0 && (
          <div className="flex items-center space-x-2">
            <button
              onClick={() => {
                navigate('/pipeline', { state: { documentIds: selectedDocIds } });
              }}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-semibold rounded-lg shadow-sm"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Run Pipeline on ({selectedDocIds.length}) Selected</span>
            </button>
          </div>
        )}
      </div>

      {/* Ingestion Dropzone */}
      <div className="p-5 bg-darkroom-surface border border-dashed border-darkroom-border hover:border-darkroom-gold/60 rounded-xl transition-all">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center space-x-4">
            <div className="p-3 bg-darkroom-card rounded-xl border border-darkroom-border text-darkroom-gold">
              <UploadCloud className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-xs font-bold text-gray-200 font-mono uppercase tracking-wider">
                Ingest Research Documents (PDF)
              </h3>
              <p className="text-xs text-gray-400">
                Upload single or multiple reports, codebooks, TVET gazettes, or OFO lists.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Project Selection for Upload */}
            <select
              value={uploadProjectId}
              onChange={(e) => setUploadProjectId(e.target.value)}
              className="px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 font-mono focus:outline-none"
            >
              <option value="">Choose Target Project...</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>

            {/* Doc Type Hint */}
            <select
              value={uploadDocType}
              onChange={(e) => setUploadDocType(e.target.value)}
              className="px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 font-mono focus:outline-none"
            >
              <option value="auto">Auto-Classify Document</option>
              <option value="qualifications">TVET Qualifications</option>
              <option value="occupations">OIHD Occupations</option>
              <option value="codebook">Survey Codebook (QLFS)</option>
              <option value="general_table">General Table Extraction</option>
            </select>

            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf"
              className="hidden"
              onChange={(e) => handleFileUpload(e.target.files)}
            />

            <button
              disabled={isUploading}
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover disabled:opacity-50 text-xs font-semibold rounded-lg shadow-sm font-mono transition-colors"
            >
              {isUploading ? 'Ingesting...' : 'Select Files'}
            </button>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-gray-500 absolute left-3 top-2.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search document by filename or classification..."
            className="w-full pl-9 pr-4 py-1.5 bg-darkroom-surface border border-darkroom-border rounded-lg text-xs text-gray-200 focus:outline-none focus:border-darkroom-gold font-mono"
          />
        </div>
        <div className="text-xs font-mono text-gray-400">
          Showing {filteredDocs.length} of {documents.length} document(s)
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-darkroom-surface border border-darkroom-border rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-darkroom-card/80 border-b border-darkroom-border text-gray-400">
              <tr>
                <th className="p-3 w-10 text-center">
                  <input
                    type="checkbox"
                    checked={
                      filteredDocs.length > 0 &&
                      filteredDocs.every((d) => selectedDocIds.includes(d.id))
                    }
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedDocIds(filteredDocs.map((d) => d.id));
                      } else {
                        setSelectedDocIds([]);
                      }
                    }}
                    className="rounded bg-darkroom-bg border-gray-700 text-darkroom-gold focus:ring-0"
                  />
                </th>
                <th className="p-3">Document Name</th>
                <th className="p-3">Classification</th>
                <th className="p-3">Pages</th>
                <th className="p-3">File Size</th>
                <th className="p-3">Status</th>
                <th className="p-3">Ingested At</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-darkroom-border/60 text-gray-300">
              {filteredDocs.map((doc) => {
                const isSelected = selectedDocIds.includes(doc.id);
                return (
                  <tr
                    key={doc.id}
                    className={`hover:bg-darkroom-card/40 transition-colors ${
                      isSelected ? 'bg-darkroom-card/60' : ''
                    }`}
                  >
                    <td className="p-3 text-center">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelect(doc.id)}
                        className="rounded bg-darkroom-bg border-gray-700 text-darkroom-gold focus:ring-0"
                      />
                    </td>
                    <td className="p-3 font-medium text-gray-200 max-w-xs truncate">
                      <div className="flex items-center space-x-2 truncate">
                        <FileText className="w-4 h-4 text-darkroom-gold flex-shrink-0" />
                        <span className="truncate" title={doc.original_name}>
                          {doc.original_name}
                        </span>
                      </div>
                    </td>
                    <td className="p-3">
                      <Badge variant={docTypeBadgeVariant(doc.doc_type)}>
                        {doc.doc_type}
                      </Badge>
                    </td>
                    <td className="p-3">{doc.page_count} pp</td>
                    <td className="p-3">{(doc.file_size / 1024 / 1024).toFixed(2)} MB</td>
                    <td className="p-3">
                      <span className="capitalize">{doc.status}</span>
                    </td>
                    <td className="p-3 text-gray-400">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-3 text-right">
                      <div className="flex items-center justify-end space-x-1.5">
                        <button
                          onClick={() => setInspectingDoc(doc)}
                          className="p-1.5 text-gray-400 hover:text-darkroom-gold hover:bg-darkroom-card rounded"
                          title="Inspect Document"
                        >
                          <FileSearch className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() =>
                            openSourceModal({
                              documentId: doc.id,
                              documentName: doc.original_name,
                              pageNumber: 1,
                            })
                          }
                          className="p-1.5 text-gray-400 hover:text-sky-400 hover:bg-darkroom-card rounded"
                          title="View PDF"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            navigate('/pipeline', { state: { documentIds: [doc.id] } });
                          }}
                          className="p-1.5 text-gray-400 hover:text-emerald-400 hover:bg-darkroom-card rounded"
                          title="Run Pipeline"
                        >
                          <Play className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => {
                            if (confirm(`Delete document "${doc.original_name}"?`)) {
                              deleteMutation.mutate(doc.id);
                            }
                          }}
                          className="p-1.5 text-gray-400 hover:text-rose-400 hover:bg-darkroom-card rounded"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filteredDocs.length === 0 && !isLoading && (
          <div className="p-10 text-center text-gray-400 font-mono text-xs">
            No documents found. Use the ingestion box above to upload PDF documents.
          </div>
        )}
      </div>

      {/* Document Inspection Drawer / Modal */}
      {inspectingDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl bg-darkroom-surface border border-darkroom-border rounded-xl shadow-2xl p-6 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-darkroom-border">
              <div className="flex items-center space-x-2">
                <FileSearch className="w-5 h-5 text-darkroom-gold" />
                <h3 className="text-sm font-bold text-gray-100 font-mono truncate max-w-md">
                  Inspection: {inspectingDoc.original_name}
                </h3>
              </div>
              <button
                onClick={() => setInspectingDoc(null)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto mt-4 space-y-4">
              {/* Quick Specs */}
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs font-mono">
                  <div className="text-gray-400">Total Pages</div>
                  <div className="text-sm font-bold text-gray-100 mt-0.5">
                    {inspectionData?.page_count ?? inspectingDoc.page_count}
                  </div>
                </div>
                <div className="p-3 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs font-mono">
                  <div className="text-gray-400">Detected Tables</div>
                  <div className="text-sm font-bold text-emerald-400 mt-0.5">
                    {inspectionData?.detected_tables_count ?? 0}
                  </div>
                </div>
                <div className="p-3 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs font-mono">
                  <div className="text-gray-400">Text Layer</div>
                  <div className="text-sm font-bold text-gray-100 mt-0.5">
                    {inspectionData?.has_text_layer ? 'Searchable' : 'Scanned / OCR Needed'}
                  </div>
                </div>
              </div>

              {/* Sample Pages Breakdown */}
              <div className="space-y-2">
                <h4 className="text-xs font-bold text-gray-300 font-mono uppercase tracking-wider">
                  Sample Page Inspection
                </h4>
                {inspectionData?.pages_sample.map((sample) => (
                  <div
                    key={sample.page_number}
                    className="p-3 bg-darkroom-card/50 border border-darkroom-border rounded-lg text-xs font-mono space-y-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-darkroom-gold font-semibold">
                        Page {sample.page_number}
                      </span>
                      <span className="text-gray-400 text-[11px]">
                        Tables: {sample.table_count} | Dims: {sample.width.toFixed(0)}x{sample.height.toFixed(0)}
                      </span>
                    </div>
                    <p className="text-gray-300 text-[11px] line-clamp-2 bg-darkroom-bg p-2 rounded border border-darkroom-border/60">
                      {sample.text_preview || 'No selectable text layer.'}
                    </p>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-darkroom-border flex justify-end space-x-2">
              <button
                onClick={() => {
                  setInspectingDoc(null);
                  openSourceModal({
                    documentId: inspectingDoc.id,
                    documentName: inspectingDoc.original_name,
                    pageNumber: 1,
                  });
                }}
                className="px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-xs font-mono text-gray-300 rounded-lg"
              >
                Open Full PDF
              </button>
              <button
                onClick={() => {
                  const docId = inspectingDoc.id;
                  setInspectingDoc(null);
                  navigate('/pipeline', { state: { documentIds: [docId] } });
                }}
                className="px-3 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-mono font-semibold rounded-lg"
              >
                Launch Pipeline
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
