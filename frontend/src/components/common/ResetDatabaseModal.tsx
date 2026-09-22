import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  X,
  Loader2,
  Database,
  Trash2,
  Terminal,
} from 'lucide-react';
import { apiClient } from '../../services/api';
import { useAppStore } from '../../store/useAppStore';
import { ResetDatabaseResponse } from '../../types';

export const ResetDatabaseModal: React.FC = () => {
  const { isResetModalOpen, closeResetModal, setSelectedProjectId } = useAppStore();
  const queryClient = useQueryClient();

  const [clearFiles, setClearFiles] = useState<boolean>(false);
  const [resetResult, setResetResult] = useState<ResetDatabaseResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const resetMutation = useMutation({
    mutationFn: (clearFilesArg: boolean) => apiClient.resetDatabase(clearFilesArg),
    onSuccess: (data: ResetDatabaseResponse) => {
      setResetResult(data);
      setErrorMessage(null);
      setSelectedProjectId(null);
      // Invalidate all queries across the entire workspace
      queryClient.invalidateQueries();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || err.message || 'Failed to reset database';
      setErrorMessage(String(msg));
      setResetResult(null);
    },
  });

  if (!isResetModalOpen) return null;

  const handleClose = () => {
    if (resetMutation.isPending) return;
    setResetResult(null);
    setErrorMessage(null);
    setClearFiles(false);
    closeResetModal();
  };

  const handleExecuteReset = () => {
    setErrorMessage(null);
    resetMutation.mutate(clearFiles);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="flex flex-col w-full max-w-lg bg-darkroom-surface border border-darkroom-border rounded-xl shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-4 bg-darkroom-card border-b border-darkroom-border">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-rose-950/60 text-rose-400 rounded-lg border border-rose-800/40">
              <RotateCcw className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-100 flex items-center space-x-2">
                <span>Reset Database</span>
                <span className="text-[10px] font-mono bg-darkroom-bg px-1.5 py-0.5 rounded border border-darkroom-border text-gray-400">
                  python reset_db.py
                </span>
              </h3>
              <p className="text-xs text-gray-400 font-mono">
                Darkroom DataForge SQLite Clean Slate
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            disabled={resetMutation.isPending}
            className="p-1 text-gray-400 hover:text-gray-200 hover:bg-darkroom-border rounded-lg transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-4">
          {resetResult ? (
            /* Success State */
            <div className="space-y-4">
              <div className="p-4 bg-emerald-950/50 border border-emerald-800/60 rounded-xl space-y-2">
                <div className="flex items-center space-x-2 text-emerald-400 font-medium text-sm">
                  <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
                  <span>Database Reset Completed Successfully</span>
                </div>
                <p className="text-xs text-emerald-200/90 leading-relaxed font-mono">
                  {resetResult.message}
                </p>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-emerald-800/40 text-xs font-mono text-emerald-300">
                  <div>
                    <span className="text-gray-400">Tables Recreated:</span>{' '}
                    <strong className="text-emerald-400">{resetResult.tables_recreated}</strong>
                  </div>
                  <div>
                    <span className="text-gray-400">Files Removed:</span>{' '}
                    <strong className="text-emerald-400">{resetResult.files_removed}</strong>
                  </div>
                </div>
              </div>
              <p className="text-xs text-gray-300">
                All SQLite tables, foreign key constraints, and auto-increment sequences have been reinitialized fresh.
              </p>
            </div>
          ) : (
            /* Confirmation Form */
            <div className="space-y-4">
              {/* Caution Callout */}
              <div className="p-3.5 bg-rose-950/40 border border-rose-800/50 rounded-lg flex items-start space-x-3">
                <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0 mt-0.5" />
                <div className="text-xs space-y-1">
                  <div className="font-semibold text-rose-300">Caution: Destructive Operation</div>
                  <p className="text-rose-200/80 leading-relaxed">
                    This will drop all SQLite tables and clear all projects, extracted qualifications, colleges, metadata records, validation logs, and human review items.
                  </p>
                </div>
              </div>

              {/* What this does */}
              <div className="p-3 bg-darkroom-bg border border-darkroom-border rounded-lg space-y-2 text-xs font-mono text-gray-300">
                <div className="flex items-center space-x-1.5 text-darkroom-gold text-[11px] font-semibold uppercase tracking-wider">
                  <Terminal className="w-3.5 h-3.5" />
                  <span>Operation Details</span>
                </div>
                <ul className="space-y-1 text-gray-400 list-disc list-inside">
                  <li>Disables foreign key pragma during purge</li>
                  <li>Drops all 17 schema tables & resets counters</li>
                  <li>Recreates all relational tables, checks & indexes fresh</li>
                  <li>Equivalent to running <code className="text-gray-200">python reset_db.py</code> in terminal</li>
                </ul>
              </div>

              {/* Checkbox for clearing uploaded files & exports */}
              <label className="flex items-start space-x-3 p-3 bg-darkroom-card/50 hover:bg-darkroom-card border border-darkroom-border rounded-lg cursor-pointer transition-colors">
                <input
                  type="checkbox"
                  checked={clearFiles}
                  onChange={(e) => setClearFiles(e.target.checked)}
                  disabled={resetMutation.isPending}
                  className="mt-0.5 h-4 w-4 rounded border-darkroom-border bg-darkroom-bg text-rose-600 focus:ring-rose-500 focus:ring-offset-0"
                />
                <div className="text-xs">
                  <span className="font-medium text-gray-200 flex items-center space-x-1.5">
                    <Trash2 className="w-3.5 h-3.5 text-gray-400" />
                    <span>Also wipe uploaded PDF files & export artifacts</span>
                  </span>
                  <p className="text-[11px] text-gray-400 mt-0.5 font-mono">
                    Equivalent to <code className="text-gray-300">--clear-files</code>. Clears uploads/ and exports/ directories.
                  </p>
                </div>
              </label>

              {/* Error Callout */}
              {errorMessage && (
                <div className="p-3 bg-rose-950/70 border border-rose-800 rounded-lg text-xs text-rose-200 font-mono">
                  {errorMessage}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-5 py-3.5 bg-darkroom-card border-t border-darkroom-border">
          {resetResult ? (
            <button
              onClick={handleClose}
              className="w-full py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold rounded-lg transition-colors font-mono"
            >
              Done (Workspace Ready)
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={handleClose}
                disabled={resetMutation.isPending}
                className="px-4 py-2 bg-darkroom-surface hover:bg-darkroom-border text-xs font-medium text-gray-300 border border-darkroom-border rounded-lg transition-colors disabled:opacity-50 font-mono"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecuteReset}
                disabled={resetMutation.isPending}
                className="flex items-center space-x-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold rounded-lg transition-colors shadow-sm disabled:opacity-50 font-mono"
              >
                {resetMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Resetting SQLite Database...</span>
                  </>
                ) : (
                  <>
                    <RotateCcw className="w-4 h-4" />
                    <span>Reset Database (Start Fresh)</span>
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
