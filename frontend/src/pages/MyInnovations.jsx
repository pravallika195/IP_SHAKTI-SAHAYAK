import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  FolderKanban,
  Plus,
  Play,
  Trash2,
  FileText,
  Clock,
  Layers,
  Sparkles,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  FlaskConical
} from 'lucide-react';
import { getInnovations, deleteInnovation } from '../api/client';
import { useInnovation } from '../context/InnovationContext';

function formatDate(isoString) {
  if (!isoString) return 'N/A';
  const d = new Date(isoString);
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function MyInnovations() {
  const navigate = useNavigate();
  const { runAnalysis, isAnalyzing } = useInnovation();

  const [innovations, setInnovations] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');

  const loadData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getInnovations();
      setInnovations(data.innovations || []);
    } catch (err) {
      setError(err.message || 'Failed to load innovation projects.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDelete = async (id, title, e) => {
    e.stopPropagation();
    if (!window.confirm(`Delete innovation project "${title}"? This cannot be undone.`)) {
      return;
    }
    try {
      await deleteInnovation(id);
      setInnovations((prev) => prev.filter((item) => item.id !== id));
    } catch (err) {
      alert(`Could not delete innovation: ${err.message}`);
    }
  };

  const filteredInnovations = innovations.filter((inn) => {
    const q = searchQuery.toLowerCase();
    return (
      inn.title.toLowerCase().includes(q) ||
      (inn.ayush_system && inn.ayush_system.toLowerCase().includes(q))
    );
  });

  return (
    <div>
      {/* Header Banner */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <FolderKanban size={24} color="var(--accent-primary)" />
              <span>My Innovation Workspaces</span>
            </h1>
            <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
              Manage your persistent AYUSH formulation projects, immutable claim versions, and prior-art evaluation runs.
            </p>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <Link to="/innovation" className="btn btn-primary" style={{ fontSize: '0.88rem' }}>
              <Plus size={16} />
              <span>New Innovation Project</span>
            </Link>
          </div>
        </div>
      </div>

      {error && (
        <div className="alert alert-danger" style={{ marginBottom: '20px' }}>
          <AlertCircle size={20} style={{ flexShrink: 0 }} />
          <div>{error}</div>
        </div>
      )}

      {/* Filter / Search Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', gap: '16px' }}>
        <div style={{ maxWidth: '360px', width: '100%' }}>
          <input
            type="text"
            className="form-control"
            placeholder="Search projects by title or AYUSH system..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
          Showing {filteredInnovations.length} {filteredInnovations.length === 1 ? 'project' : 'projects'}
        </div>
      </div>

      {/* Main Listing */}
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <div className="spinner" style={{ width: '32px', height: '32px', marginBottom: '12px' }} />
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Loading saved innovation workspaces from MySQL...</div>
        </div>
      ) : filteredInnovations.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '50px 24px' }}>
          <div
            style={{
              width: '60px',
              height: '60px',
              borderRadius: '14px',
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--accent-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px auto',
            }}
          >
            <FolderKanban size={30} />
          </div>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
            No Innovation Projects Found
          </h3>
          <p style={{ color: 'var(--text-secondary)', maxWidth: '480px', margin: '0 auto 24px', fontSize: '0.9rem' }}>
            {searchQuery
              ? 'No projects match your search filter.'
              : 'You have not saved any innovation workspaces yet. Create your first project to track versioned claims and evaluate prior art.'}
          </p>
          <Link to="/innovation" className="btn btn-primary" style={{ display: 'inline-flex' }}>
            <Plus size={16} />
            <span>Create First Project</span>
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filteredInnovations.map((inn) => {
            const isAnalyzed = inn.status === 'analyzed';
            return (
              <div
                key={inn.id}
                className="card"
                style={{
                  padding: '20px 24px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '16px',
                  transition: 'border-color 0.15s ease',
                  cursor: 'pointer',
                }}
                onClick={() => navigate(`/innovation?id=${inn.id}`)}
              >
                <div style={{ flex: 1, minWidth: '280px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', flexWrap: 'wrap' }}>
                    <span
                      style={{
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        backgroundColor: 'var(--accent-glow)',
                        color: 'var(--accent-secondary)',
                        border: '1px solid rgba(99, 102, 241, 0.3)',
                      }}
                    >
                      {inn.ayush_system || 'Ayurveda'}
                    </span>

                    <span
                      className={`badge ${isAnalyzed ? 'badge-success' : 'badge-primary'}`}
                      style={{ fontSize: '0.72rem' }}
                    >
                      {isAnalyzed ? 'ANALYZED' : 'DRAFT'}
                    </span>

                    <span
                      style={{
                        fontSize: '0.72rem',
                        fontFamily: 'var(--font-mono)',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        backgroundColor: 'var(--bg-tertiary)',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      Version {inn.latest_version_number || 1}
                    </span>

                    {inn.runs_count > 0 && (
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          backgroundColor: 'rgba(56, 189, 248, 0.12)',
                          color: '#38bdf8',
                          border: '1px solid rgba(56, 189, 248, 0.3)',
                        }}
                      >
                        {inn.runs_count} {inn.runs_count === 1 ? 'analysis run' : 'analysis runs'}
                      </span>
                    )}
                  </div>

                  <h3 style={{ fontSize: '1.12rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                    {inn.title}
                  </h3>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={13} />
                      <span>Updated {formatDate(inn.updated_at)}</span>
                    </span>
                    <span>•</span>
                    <span>{inn.versions_count || 1} version(s) in history</span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexShrink: 0 }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    style={{ fontSize: '0.82rem', padding: '8px 14px' }}
                    onClick={(e) => {
                      e.stopPropagation();
                      navigate(`/innovation?id=${inn.id}`);
                    }}
                  >
                    <FlaskConical size={14} color="var(--accent-secondary)" />
                    <span>Open Workspace</span>
                  </button>

                  <button
                    type="button"
                    className="btn-icon-danger"
                    title="Delete project"
                    onClick={(e) => handleDelete(inn.id, inn.title, e)}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

