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
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Badge } from '../components/common/Badge';
import { DatasetRecord } from '../types';

export const DatasetDetails: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const queryClient = useQueryClient();
  const { openSourceModal } = useAppStore();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [editingRecord, setEditingRecord] = useState<DatasetRecord | null>(null);
  const [editFormData, setEditFormData] = useState<Record<string, any>>({});
  const [editNotes, setEditNotes] = useState('');

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
          <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight mt-1 flex items-center space-x-2">
            <span>{dataset.name}</span>
          </h1>
          <p className="text-xs text-gray-400 font-mono mt-0.5">
            Model: {dataset.schema_name} • {dataset.record_count.toLocaleString()} Total Records • Quality Score: {dataset.quality_score}%
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Link
            to="/exports"
            state={{ defaultDatasetId: dataset.id }}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-xs font-mono text-gray-200 border border-darkroom-border rounded-lg transition-colors"
          >
            <Download className="w-3.5 h-3.5 text-darkroom-gold" />
            <span>Export Dataset</span>
          </Link>
          <Link
            to="/validation"
            state={{ defaultDatasetId: dataset.id }}
            className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-mono font-semibold rounded-lg shadow-sm transition-colors"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Audit Validation</span>
          </Link>
        </div>
      </div>

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
                              documentId: prov.document_id,
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
    </div>
  );
};
