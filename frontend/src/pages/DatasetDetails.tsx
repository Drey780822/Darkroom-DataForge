import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Database,
  Search,
  Filter,
  Eye,
  Edit2,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Download,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  FileText,
  X,
  History,
  BookOpen,
  MapPin,
  CheckCircle2,
  Layers,
  Award,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';
import { DatasetRecord } from '../types';

export const DatasetDetails: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const queryClient = useQueryClient();
  const { openSourceModal } = useAppStore();

  const [activeTab, setActiveTab] = useState<'records' | 'dictionary' | 'map'>('records');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [editingRecord, setEditingRecord] = useState<DatasetRecord | null>(null);
  const [editFormData, setEditFormData] = useState<Record<string, any>>({});
  const [editNotes, setEditNotes] = useState('');

  // Verification modal state
  const [showVerifyModal, setShowVerifyModal] = useState(false);
  const [verifierName, setVerifierName] = useState('Senior Research Data Specialist');
  const [verificationNotes, setVerificationNotes] = useState('');

  const { data: dataset, isLoading: isDatasetLoading } = useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: () => apiClient.getDataset(datasetId!),
    enabled: !!datasetId,
  });

  const { data: recordsData, isLoading: isRecordsLoading } = useQuery({
    queryKey: ['records', datasetId, page, pageSize, statusFilter, search],
    queryFn: () =>
      apiClient.getRecords(datasetId!, {
        page,
        page_size: pageSize,
        status_filter: statusFilter || undefined,
        search: search || undefined,
      }),
    enabled: !!datasetId,
  });

  const updateRecordMutation = useMutation({
    mutationFn: ({ id, data, notes }: { id: string; data: any; notes?: string }) =>
      apiClient.updateRecord(id, { data, review_notes: notes, status: 'human_reviewed' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      setEditingRecord(null);
    },
  });

  const reviewActionMutation = useMutation({
    mutationFn: ({ recordId, action }: { recordId: string; action: string }) =>
      apiClient.createReviewAudit({
        record_id: recordId,
        action,
        reviewed_by: 'Researcher',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['records', datasetId] });
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
    },
  });

  const verifyDatasetMutation = useMutation({
    mutationFn: (payload: { verified_by: string; verification_notes?: string }) =>
      apiClient.verifyDataset(datasetId!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dataset', datasetId] });
      setShowVerifyModal(false);
    },
  });

  if (isDatasetLoading) {
    return (
      <div className="p-12 text-center text-gray-400 font-mono text-xs">
        Loading dataset schema and records...
      </div>
    );
  }

  if (!dataset) {
    return (
      <div className="p-12 text-center text-rose-400 font-mono text-xs">
        Dataset not found.
      </div>
    );
  }

  const columns = dataset.schema_columns || [];
  const records = recordsData?.records || [];
  const total = recordsData?.total || 0;
  const totalPages = Math.ceil(total / pageSize) || 1;

  const handleEditClick = (record: DatasetRecord) => {
    setEditingRecord(record);
    setEditFormData({ ...record.data });
    setEditNotes(record.review_notes || '');
  };

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRecord) return;
    updateRecordMutation.mutate({
      id: editingRecord.id,
      data: editFormData,
      notes: editNotes,
    });
  };

  const handleVerifySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    verifyDatasetMutation.mutate({
      verified_by: verifierName,
      verification_notes: verificationNotes,
    });
  };

  const statusBadge = (st: string) => {
    switch (st) {
      case 'valid':
        return <Badge variant="success">VALID</Badge>;
      case 'warning':
        return <Badge variant="warning">WARNING</Badge>;
      case 'error':
        return <Badge variant="danger">ERROR</Badge>;
      case 'human_reviewed':
        return <Badge variant="gold">HUMAN REVIEWED</Badge>;
      default:
        return <Badge variant="default">{st}</Badge>;
    }
  };

  // Extract data dictionary entries
  const dictionaryEntries = dataset.data_dictionary && Array.isArray(dataset.data_dictionary) && dataset.data_dictionary.length > 0
    ? dataset.data_dictionary
    : columns.map((col) => ({
        column_name: col.name,
        source_label: col.description || col.name,
        data_type: col.type,
        nullable: col.required ? 'False' : 'True',
        identifier: col.identifier ? 'True' : 'False',
        description: col.description || 'Extracted tabular feature',
        example_value: '-',
        source_pages: '-',
      }));

  const docMap = dataset.document_map;

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <Link
              to="/datasets"
              className="text-xs font-mono text-gray-400 hover:text-darkroom-gold flex items-center space-x-1"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
              <span>All Datasets</span>
            </Link>
          </div>
          <div className="flex items-center space-x-3 mt-1">
            <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight">
              {dataset.name}
            </h1>
            {dataset.is_verified ? (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>Verified Dataset</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-mono font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/30">
                <AlertTriangle className="w-3.5 h-3.5" />
                <span>Unverified / Draft</span>
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 font-mono mt-0.5">
            Model: {dataset.schema_name} • {dataset.record_count.toLocaleString()} Total Records • Quality Score: {dataset.quality_score}%
            {dataset.is_verified && dataset.verified_by && (
              <span className="text-emerald-400 ml-2">
                • Verified by {dataset.verified_by} {dataset.verified_at ? `on ${new Date(dataset.verified_at).toLocaleDateString()}` : ''}
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center space-x-2 font-mono text-xs">
          {!dataset.is_verified ? (
            <button
              onClick={() => setShowVerifyModal(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 rounded-lg transition-colors"
            >
              <Award className="w-3.5 h-3.5 text-emerald-400" />
              <span>Sign-off & Verify</span>
            </button>
          ) : (
            <button
              onClick={() => setShowVerifyModal(true)}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-gray-300 border border-darkroom-border rounded-lg transition-colors"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              <span>Update Sign-off</span>
            </button>
          )}

          <Link
            to="/exports"
            state={{ defaultDatasetId: dataset.id }}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-gray-200 border border-darkroom-border rounded-lg transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-darkroom-gold" />
            <span>Export Bundle</span>
          </Link>
          <Link
            to="/validation"
            state={{ defaultDatasetId: dataset.id }}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover font-semibold rounded-lg shadow-sm transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Audit Validation</span>
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-darkroom-border space-x-2 font-mono text-xs">
        <button
          onClick={() => setActiveTab('records')}
          className={`flex items-center space-x-2 px-4 py-2.5 font-medium border-b-2 transition-all ${
            activeTab === 'records'
              ? 'border-darkroom-gold text-darkroom-gold bg-darkroom-surface/50'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Structured Records ({dataset.record_count.toLocaleString()})</span>
        </button>

        <button
          onClick={() => setActiveTab('dictionary')}
          className={`flex items-center space-x-2 px-4 py-2.5 font-medium border-b-2 transition-all ${
            activeTab === 'dictionary'
              ? 'border-darkroom-gold text-darkroom-gold bg-darkroom-surface/50'
              : 'border-transparent text-gray-400 hover:text-gray-200'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>Data Dictionary ({dictionaryEntries.length} fields)</span>
        </button>

        {docMap && (
          <button
            onClick={() => setActiveTab('map')}
            className={`flex items-center space-x-2 px-4 py-2.5 font-medium border-b-2 transition-all ${
              activeTab === 'map'
                ? 'border-darkroom-gold text-darkroom-gold bg-darkroom-surface/50'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <MapPin className="w-4 h-4" />
            <span>Intelligence Map</span>
          </button>
        )}
      </div>

      {/* TAB 1: STRUCTURED RECORDS */}
      {activeTab === 'records' && (
        <div className="space-y-4">
          {/* Filter and Search Bar */}
          <div className="flex flex-wrap items-center justify-between gap-4 bg-darkroom-surface p-3.5 rounded-xl border border-darkroom-border font-mono text-xs">
            <div className="flex items-center space-x-3 flex-1 min-w-[280px]">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-gray-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  placeholder="Search across all record fields..."
                  className="w-full pl-9 pr-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 focus:outline-none focus:border-darkroom-gold"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 focus:outline-none focus:border-darkroom-gold"
              >
                <option value="">All Statuses</option>
                <option value="valid">Valid Only</option>
                <option value="warning">Warnings</option>
                <option value="error">Errors</option>
                <option value="human_reviewed">Human Reviewed</option>
              </select>
            </div>

            <div className="flex items-center space-x-2 text-gray-400">
              <span>Rows per page:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(Number(e.target.value));
                  setPage(1);
                }}
                className="px-2 py-1 bg-darkroom-bg border border-darkroom-border rounded text-xs text-gray-200 focus:outline-none"
              >
                <option value="25">25</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </div>
          </div>

          {/* Dataset Data Table */}
          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto max-h-[60vh]">
              <table className="w-full text-left text-xs font-mono whitespace-nowrap">
                <thead className="bg-darkroom-card/90 sticky top-0 z-10 border-b border-darkroom-border text-gray-300">
                  <tr>
                    <th className="p-3 w-14 text-center">#</th>
                    <th className="p-3">Status</th>
                    <th className="p-3">Provenance (Source)</th>
                    {columns.map((col) => (
                      <th key={col.name} className="p-3">
                        <div className="flex flex-col">
                          <span className="font-bold text-gray-100">{col.name}</span>
                          <span className="text-[10px] text-gray-500 font-normal">{col.type}</span>
                        </div>
                      </th>
                    ))}
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-darkroom-border/60 text-gray-300">
                  {records.map((record) => {
                    const prov = record.provenance || {};
                    return (
                      <tr
                        key={record.id}
                        className="hover:bg-darkroom-card/50 transition-colors"
                      >
                        <td className="p-3 text-center text-gray-500 font-bold">
                          {record.row_index}
                        </td>
                        <td className="p-3">{statusBadge(record.status)}</td>
                        <td className="p-3">
                          {prov.document_id ? (
                            <button
                              onClick={() =>
                                openSourceModal({
                                  documentId: prov.document_id!,
                                  documentName: prov.document_name || 'Source PDF',
                                  pageNumber: prov.page_number || 1,
                                  recordIndex: record.row_index,
                                })
                              }
                              className="flex items-center space-x-1.5 px-2 py-1 bg-darkroom-navy/60 hover:bg-darkroom-navy text-darkroom-gold border border-darkroom-gold/30 rounded text-[11px] transition-colors"
                              title="Open exact PDF page in source viewer"
                            >
                              <FileText className="w-3 h-3 text-darkroom-gold" />
                              <span>p.{prov.page_number || 1}</span>
                              <Eye className="w-3 h-3 ml-0.5 opacity-70" />
                            </button>
                          ) : (
                            <span className="text-gray-500 text-[11px]">N/A</span>
                          )}
                        </td>

                        {/* Column values */}
                        {columns.map((col) => {
                          const val = record.data?.[col.name];
                          const valStr = val !== null && val !== undefined ? String(val) : '';
                          return (
                            <td
                              key={col.name}
                              className="p-3 max-w-xs truncate"
                              title={valStr}
                            >
                              {valStr || <span className="text-gray-600 italic">null</span>}
                            </td>
                          );
                        })}

                        {/* Actions */}
                        <td className="p-3 text-right">
                          <div className="flex items-center justify-end space-x-1.5">
                            <button
                              onClick={() => handleEditClick(record)}
                              className="p-1 text-gray-400 hover:text-darkroom-gold hover:bg-darkroom-card rounded"
                              title="Edit Row Values"
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() =>
                                reviewActionMutation.mutate({
                                  recordId: record.id,
                                  action: 'approve_record',
                                })
                              }
                              className="p-1 text-gray-400 hover:text-emerald-400 hover:bg-darkroom-card rounded"
                              title="Approve Record"
                            >
                              <CheckCircle className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() =>
                                reviewActionMutation.mutate({
                                  recordId: record.id,
                                  action: 'flag_record',
                                })
                              }
                              className="p-1 text-gray-400 hover:text-amber-400 hover:bg-darkroom-card rounded"
                              title="Flag for Investigation"
                            >
                              <AlertTriangle className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {records.length === 0 && !isRecordsLoading && (
              <div className="p-12 text-center text-gray-400 font-mono text-xs">
                No records matched current search / filter criteria.
              </div>
            )}

            {/* Pagination Footer */}
            <div className="p-3.5 bg-darkroom-card/70 border-t border-darkroom-border flex items-center justify-between text-xs font-mono text-gray-400">
              <div>
                Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total.toLocaleString()} records
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="p-1.5 bg-darkroom-bg border border-darkroom-border rounded hover:text-white disabled:opacity-30"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-gray-200">
                  Page {page} of {totalPages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="p-1.5 bg-darkroom-bg border border-darkroom-border rounded hover:text-white disabled:opacity-30"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: DATA DICTIONARY */}
      {activeTab === 'dictionary' && (
        <div className="space-y-4 font-mono text-xs">
          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl p-4 flex items-center justify-between">
            <div>
              <h3 className="font-bold text-gray-100 text-sm">Dataset Data Dictionary & Codebook</h3>
              <p className="text-gray-400 text-xs mt-0.5">
                Standardized definitions, source headers, data types, and primary keys for research reproducibility.
              </p>
            </div>
            <Link
              to="/exports"
              state={{ defaultDatasetId: dataset.id }}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-darkroom-gold border border-darkroom-gold/30 rounded-lg text-xs"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export Dictionary CSV</span>
            </Link>
          </div>

          <div className="bg-darkroom-surface border border-darkroom-border rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead className="bg-darkroom-card/90 border-b border-darkroom-border text-gray-300">
                  <tr>
                    <th className="p-3">Column Name</th>
                    <th className="p-3">Source Header</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Nullable</th>
                    <th className="p-3">Identifier</th>
                    <th className="p-3">Example Value</th>
                    <th className="p-3">Description & Semantic Scope</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-darkroom-border/60 text-gray-300">
                  {dictionaryEntries.map((col: any, idx: number) => (
                    <tr key={idx} className="hover:bg-darkroom-card/50 transition-colors">
                      <td className="p-3 font-bold text-darkroom-gold">
                        {col.column_name || col.name}
                      </td>
                      <td className="p-3 text-gray-300">
                        {col.source_label || col.name}
                      </td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded text-[10px] bg-darkroom-navy text-sky-300 border border-sky-500/20 uppercase font-semibold">
                          {col.data_type || col.type || 'string'}
                        </span>
                      </td>
                      <td className="p-3 text-gray-400">
                        {col.nullable === 'False' || col.required ? 'No (Required)' : 'Yes'}
                      </td>
                      <td className="p-3">
                        {col.identifier === 'True' || col.unique ? (
                          <span className="text-emerald-400 font-bold">Primary / Key</span>
                        ) : (
                          <span className="text-gray-500">-</span>
                        )}
                      </td>
                      <td className="p-3 font-mono text-gray-400">
                        {col.example_value || col.example || '-'}
                      </td>
                      <td className="p-3 text-gray-300 max-w-sm">
                        {col.description || 'Extracted tabular feature'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: DOCUMENT INTELLIGENCE MAP */}
      {activeTab === 'map' && docMap && (
        <div className="space-y-4 font-mono text-xs">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl">
              <span className="text-gray-400 text-[10px] block uppercase">Total Document Pages</span>
              <span className="text-2xl font-bold text-gray-100 mt-1 block">{docMap.page_count || '-'}</span>
            </div>
            <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl">
              <span className="text-gray-400 text-[10px] block uppercase">Scanned vs Digital</span>
              <span className="text-2xl font-bold text-sky-400 mt-1 block">
                {docMap.is_scanned ? 'Scanned (OCR)' : 'Digital Text'}
              </span>
            </div>
            <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl">
              <span className="text-gray-400 text-[10px] block uppercase">Average Text Density</span>
              <span className="text-2xl font-bold text-darkroom-gold mt-1 block">
                {docMap.text_density_avg ? docMap.text_density_avg.toFixed(1) : '-'} chars/area
              </span>
            </div>
            <div className="p-4 bg-darkroom-surface border border-darkroom-border rounded-xl">
              <span className="text-gray-400 text-[10px] block uppercase">Multi-Page Continuations</span>
              <span className="text-2xl font-bold text-emerald-400 mt-1 block">
                {docMap.continuation_groups?.length || 0} groups
              </span>
            </div>
          </div>

          {/* Detected Tables */}
          {docMap.tables && docMap.tables.length > 0 && (
            <div className="bg-darkroom-surface border border-darkroom-border rounded-xl p-4 space-y-3">
              <h4 className="font-bold text-gray-200">Detected Document Tables</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {docMap.tables.map((tbl: any, idx: number) => (
                  <div key={idx} className="p-3 bg-darkroom-card rounded-lg border border-darkroom-border space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-darkroom-gold">{tbl.table_id || `Table ${idx + 1}`}</span>
                      <span className="text-gray-400">Pages {tbl.start_page} – {tbl.end_page}</span>
                    </div>
                    <div className="text-gray-400 text-[11px]">
                      Est. Rows: <span className="text-gray-200">{tbl.row_count_estimate || '-'}</span> •
                      Continuation: <span className={tbl.is_continuation ? 'text-amber-400 font-bold' : 'text-gray-300'}>
                        {tbl.is_continuation ? 'Yes' : 'No'}
                      </span>
                    </div>
                    {tbl.headers && tbl.headers.length > 0 && (
                      <div className="text-[10px] text-gray-500 truncate">
                        Headers: {tbl.headers.join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Edit Record Modal */}
      {editingRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-xl bg-darkroom-surface border border-darkroom-border rounded-xl shadow-2xl p-6 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-darkroom-border">
              <h3 className="text-sm font-bold text-gray-100 font-mono">
                Edit Record #{editingRecord.row_index}
              </h3>
              <button
                onClick={() => setEditingRecord(null)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="flex-1 overflow-y-auto mt-4 space-y-4 pr-1">
              {columns.map((col) => (
                <div key={col.name}>
                  <label className="block text-xs font-mono text-gray-300 mb-1">
                    {col.name} {col.required && <span className="text-rose-400">*</span>}
                  </label>
                  <input
                    type="text"
                    value={editFormData[col.name] ?? ''}
                    onChange={(e) =>
                      setEditFormData({ ...editFormData, [col.name]: e.target.value })
                    }
                    className="w-full px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 font-mono focus:outline-none focus:border-darkroom-gold"
                  />
                </div>
              ))}

              <div>
                <label className="block text-xs font-mono text-gray-300 mb-1">
                  Researcher Review Notes (Audit Trail)
                </label>
                <textarea
                  rows={2}
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Reason for manual edit, verified document source..."
                  className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 focus:outline-none focus:border-darkroom-gold"
                />
              </div>

              <div className="pt-4 border-t border-darkroom-border flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setEditingRecord(null)}
                  className="px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-xs font-mono text-gray-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updateRecordMutation.isPending}
                  className="px-4 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-mono font-semibold rounded-lg shadow-sm"
                >
                  Save & Apply Audit
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Dataset Verification Sign-off Modal */}
      {showVerifyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 font-mono text-xs">
          <div className="w-full max-w-md bg-darkroom-surface border border-darkroom-border rounded-xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-darkroom-border">
              <h3 className="text-sm font-bold text-gray-100 flex items-center space-x-2">
                <Award className="w-4 h-4 text-emerald-400" />
                <span>Dataset Verification Sign-Off</span>
              </h3>
              <button
                onClick={() => setShowVerifyModal(false)}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-gray-400 text-xs">
              Marking this dataset as <strong className="text-emerald-300">Verified</strong> confirms that human-in-the-loop review has resolved all critical discrepancies, quality thresholds are met, and the dataset is signed off for downstream research publication.
            </p>

            <form onSubmit={handleVerifySubmit} className="space-y-3">
              <div>
                <label className="block text-gray-300 mb-1">
                  Verifier Name & Title <span className="text-darkroom-gold">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={verifierName}
                  onChange={(e) => setVerifierName(e.target.value)}
                  placeholder="e.g. Dr. Jane Doe (Lead Quantitative Researcher)"
                  className="w-full px-3 py-1.5 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-100 focus:outline-none focus:border-darkroom-gold"
                />
              </div>

              <div>
                <label className="block text-gray-300 mb-1">
                  Verification Rationale & Notes
                </label>
                <textarea
                  rows={3}
                  value={verificationNotes}
                  onChange={(e) => setVerificationNotes(e.target.value)}
                  placeholder="e.g. Checked all OFO codes against 2024 Gazette, cross-verified 50 sampled rows against source document..."
                  className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-gray-100 focus:outline-none focus:border-darkroom-gold"
                />
              </div>

              <div className="pt-3 border-t border-darkroom-border flex justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowVerifyModal(false)}
                  className="px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-gray-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={verifyDatasetMutation.isPending || !verifierName.trim()}
                  className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-lg shadow-sm disabled:opacity-50 flex items-center space-x-1.5"
                >
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  <span>Confirm Sign-Off</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
