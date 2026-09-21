import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  FolderPlus,
  FolderGit2,
  FileText,
  Database,
  Trash2,
  Edit2,
  Tag,
  Check,
  X,
  AlertCircle,
} from 'lucide-react';
import { apiClient } from '../services/api';
import { useAppStore } from '../store/useAppStore';
import { Project } from '../types';

export const Projects: React.FC = () => {
  const queryClient = useQueryClient();
  const { selectedProjectId, setSelectedProjectId } = useAppStore();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: apiClient.getProjects,
  });

  const createMutation = useMutation({
    mutationFn: apiClient.createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setIsCreateOpen(false);
      setName('');
      setDescription('');
      setTagsInput('');
      setErrorMessage(null);
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Could not connect to backend server. Make sure port 8000 is running.';
      setErrorMessage(msg);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) => apiClient.updateProject(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setEditingProject(null);
      setErrorMessage(null);
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.detail ||
        err.message ||
        'Could not connect to backend server. Make sure port 8000 is running.';
      setErrorMessage(msg);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: apiClient.deleteProject,
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      if (selectedProjectId === deletedId) {
        setSelectedProjectId(null);
      }
    },
    onError: (err: any) => {
      alert('Delete failed: ' + (err.response?.data?.detail || err.message));
    },
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setErrorMessage('Project name is required.');
      return;
    }
    setErrorMessage(null);
    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    createMutation.mutate({ name: name.trim(), description: description.trim() || undefined, tags });
  };

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingProject || !name.trim()) {
      setErrorMessage('Project name is required.');
      return;
    }
    setErrorMessage(null);
    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    updateMutation.mutate({
      id: editingProject.id,
      data: { name: name.trim(), description: description.trim() || undefined, tags },
    });
  };

  const startEdit = (p: Project) => {
    setEditingProject(p);
    setName(p.name);
    setDescription(p.description || '');
    setTagsInput((p.tags || []).join(', '));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100 font-mono tracking-tight">
            Research Projects
          </h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Organize documents, extraction schemas, and datasets by research initiatives
          </p>
        </div>
        <button
          onClick={() => {
            setIsCreateOpen(true);
            setEditingProject(null);
            setName('');
            setDescription('');
            setTagsInput('');
          }}
          className="flex items-center space-x-1.5 px-3 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-semibold rounded-lg shadow-sm transition-colors"
        >
          <FolderPlus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {projects.map((project) => {
          const isSelected = selectedProjectId === project.id;
          return (
            <div
              key={project.id}
              className={`flex flex-col justify-between p-5 bg-darkroom-surface border rounded-xl transition-all ${
                isSelected
                  ? 'border-darkroom-gold shadow-lg shadow-darkroom-gold/5'
                  : 'border-darkroom-border hover:border-darkroom-borderLight'
              }`}
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center space-x-2">
                    <FolderGit2 className="w-5 h-5 text-darkroom-gold flex-shrink-0" />
                    <h2 className="text-sm font-bold text-gray-100 font-mono line-clamp-1">
                      {project.name}
                    </h2>
                  </div>
                  <div className="flex items-center space-x-1">
                    <button
                      onClick={() => startEdit(project)}
                      className="p-1 text-gray-400 hover:text-white rounded"
                      title="Edit project"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => {
                        if (confirm(`Delete project "${project.name}" and all associated data?`)) {
                          deleteMutation.mutate(project.id);
                        }
                      }}
                      className="p-1 text-gray-400 hover:text-rose-400 rounded"
                      title="Delete project"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>

                <p className="text-xs text-gray-400 mt-2 line-clamp-2 min-h-[2.5rem]">
                  {project.description || 'No description provided.'}
                </p>

                {/* Tags */}
                <div className="flex flex-wrap gap-1.5 mt-3">
                  {project.tags && project.tags.length > 0 ? (
                    project.tags.map((tag, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center space-x-1 px-2 py-0.5 bg-darkroom-card text-darkroom-gold/90 border border-darkroom-border rounded text-[10px] font-mono"
                      >
                        <Tag className="w-2.5 h-2.5" />
                        <span>{tag}</span>
                      </span>
                    ))
                  ) : (
                    <span className="text-[11px] text-gray-400 italic">No tags</span>
                  )}
                </div>
              </div>

              {/* Stats & Select Button */}
              <div className="mt-5 pt-3 border-t border-darkroom-border/80 flex items-center justify-between text-xs font-mono">
                <div className="flex items-center space-x-3 text-gray-400">
                  <span className="flex items-center space-x-1">
                    <FileText className="w-3.5 h-3.5 text-sky-400" />
                    <span>{project.document_count}</span>
                  </span>
                  <span className="flex items-center space-x-1">
                    <Database className="w-3.5 h-3.5 text-emerald-400" />
                    <span>{project.dataset_count}</span>
                  </span>
                </div>

                <button
                  onClick={() => setSelectedProjectId(isSelected ? null : project.id)}
                  className={`px-2.5 py-1 rounded text-[11px] transition-colors ${
                    isSelected
                      ? 'bg-darkroom-gold text-black font-semibold'
                      : 'bg-darkroom-card hover:bg-darkroom-border text-gray-300'
                  }`}
                >
                  {isSelected ? 'Active Scope' : 'Select Scope'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {projects.length === 0 && !isLoading && (
        <div className="p-12 text-center bg-darkroom-surface border border-dashed border-darkroom-border rounded-xl">
          <FolderGit2 className="w-10 h-10 text-gray-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-gray-300 font-mono">No Projects Found</h3>
          <p className="text-xs text-gray-400 mt-1 max-w-sm mx-auto">
            Create your first research project to start uploading and extracting structured datasets.
          </p>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="mt-4 px-3 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-semibold rounded-lg shadow-sm transition-colors"
          >
            Create Project
          </button>
        </div>
      )}

      {/* Create / Edit Modal */}
      {(isCreateOpen || editingProject) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md bg-darkroom-surface border border-darkroom-border rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-darkroom-border">
              <h2 className="text-sm font-bold text-gray-100 font-mono">
                {editingProject ? 'Edit Project' : 'Create New Project'}
              </h2>
              <button
                onClick={() => {
                  setIsCreateOpen(false);
                  setEditingProject(null);
                }}
                className="text-gray-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {errorMessage && (
              <div className="mt-3 p-3 bg-rose-950/80 border border-rose-800 rounded-lg text-xs font-mono text-rose-300 flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-bold">Action Failed</div>
                  <div>{errorMessage}</div>
                </div>
              </div>
            )}

            <form onSubmit={editingProject ? handleUpdate : handleCreate} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-mono text-gray-300 mb-1">
                  Project Name *
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. merSETA Skills Demand Audit 2026"
                  className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 focus:outline-none focus:border-darkroom-gold font-mono"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-gray-300 mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Brief description of research initiative, stakeholders, and goals..."
                  className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 focus:outline-none focus:border-darkroom-gold"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-gray-300 mb-1">
                  Tags (comma-separated)
                </label>
                <input
                  type="text"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  placeholder="e.g. DHET, TVET, Labour, 2026"
                  className="w-full px-3 py-2 bg-darkroom-bg border border-darkroom-border rounded-lg text-xs text-gray-200 focus:outline-none focus:border-darkroom-gold font-mono"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-3 border-t border-darkroom-border">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreateOpen(false);
                    setEditingProject(null);
                  }}
                  className="px-3 py-1.5 bg-darkroom-card hover:bg-darkroom-border text-xs text-gray-300 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="px-4 py-1.5 bg-darkroom-gold text-black hover:bg-darkroom-goldHover text-xs font-semibold rounded-lg shadow-sm"
                >
                  {editingProject ? 'Save Changes' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
