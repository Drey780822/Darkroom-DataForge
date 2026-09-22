import React from 'react';
import { Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { apiClient } from '../../services/api';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { SourceDocumentModal } from '../common/SourceDocumentModal';
import { ResetDatabaseModal } from '../common/ResetDatabaseModal';

export const Layout: React.FC = () => {
  const { data: health, isError } = useQuery({
    queryKey: ['health'],
    queryFn: apiClient.getHealth,
    refetchInterval: 6000,
    retry: 1,
  });

  const isOffline = isError || !health || health.status !== 'healthy';

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-darkroom-bg text-darkroom-text font-sans">
      <Header />
      {isOffline && (
        <div className="bg-rose-950/90 border-b border-rose-800/80 px-6 py-2 text-xs font-mono text-rose-200 flex items-center justify-between z-30">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0 animate-bounce" />
            <span>
              <strong>Backend Server Offline:</strong> Cannot connect to FastAPI on{' '}
              <code className="bg-black/40 px-1 py-0.5 rounded text-rose-300">
                http://127.0.0.1:8000
              </code>
              .
            </span>
          </div>
          <span className="text-[11px] text-rose-300 hidden md:inline">
            Run{' '}
            <code className="bg-black/50 px-1.5 py-0.5 rounded font-bold text-darkroom-gold">
              python run_dev.py
            </code>{' '}
            in your terminal to start the backend.
          </span>
        </div>
      )}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto bg-darkroom-bg p-6">
          <Outlet />
        </main>
      </div>
      <SourceDocumentModal />
      <ResetDatabaseModal />
    </div>
  );
};
