import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  FileText, 
  Download, 
  Search, 
  Database, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Info, 
  ChevronDown, 
  ChevronUp, 
  ArrowLeft,
  Sparkles,
  ShieldCheck,
  BookOpen
} from 'lucide-react';
import { useInnovation } from '../context/InnovationContext';
import { getInnovationRuns, getSpecificRun } from '../api/client';

export default function AnalysisReport() {
  const navigate = useNavigate();
  const location = useLocation();
  const { analysisResult, setAnalysisResult, runAnalysis, isAnalyzing } = useInnovation();

  const searchParams = new URLSearchParams(location.search);
  const paramInnovationId = searchParams.get('innovationId');
  const paramRunId = searchParams.get('runId');
  const [isLoadingRun, setIsLoadingRun] = useState(false);
  const [loadError, setLoadError] = useState(null);

  useEffect(() => {
    if (!paramInnovationId) return;
    let isMounted = true;
    setIsLoadingRun(true);
    setLoadError(null);

    const loadRunData = async () => {
      try {
        let runToFetch = paramRunId;
        if (!runToFetch) {
          const runsData = await getInnovationRuns(paramInnovationId);
          if (runsData.runs && runsData.runs.length > 0) {
            runToFetch = runsData.runs[0].id;
          }
        }
        if (runToFetch) {
          const detail = await getSpecificRun(paramInnovationId, runToFetch);
          if (isMounted && detail.run) {
            const r = detail.run;
            const fullResult = r.report_json || {
              retrieval_status: r.retrieval_status,
              sources_count: r.sources_count,
              queries_executed: r.queries_executed || [],
              citation_audit: r.citation_audit,
              report_markdown: r.report_markdown,
              run_id: r.id,
              run_number: r.run_number
            };
            setAnalysisResult(fullResult);
          }
        }
      } catch (err) {
        if (isMounted) setLoadError(err.message || 'Failed to load persistent analysis run.');
      } finally {
        if (isMounted) setIsLoadingRun(false);
      }
    };

    loadRunData();
    return () => { isMounted = false; };
  }, [paramInnovationId, paramRunId, setAnalysisResult]);

  // State for collapsible panels
  const [showQueries, setShowQueries] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});

  const toggleSource = (idx) => {
    setExpandedSources((prev) => ({
      ...prev,
      [idx]: !prev[idx]
    }));
  };

  const expandAllSources = () => {
    if (!analysisResult?.sources) return;
    const all = {};
    analysisResult.sources.forEach((_, i) => { all[i] = true; });
    setExpandedSources(all);
  };

  const collapseAllSources = () => {
    setExpandedSources({});
  };

  const handleDownloadMarkdown = () => {
    if (!analysisResult?.report_markdown) return;
    const blob = new Blob([analysisResult.report_markdown], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const safeTitle = (analysisResult.innovation?.title || 'Innovation')
      .replace(/[^a-zA-Z0-9_-]/g, '_')
      .slice(0, 30);
    link.href = url;
    link.setAttribute('download', `IP_SAKTI_Report_${safeTitle}.md`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // Run quick demo directly from empty state
  const handleRunDemo = async () => {
    const demoPayload = {
      title: 'Synergistic Topical Emulgel of Curcuma longa and Piper nigrum for Accelerated Wound Healing',
      ayush_system: 'Ayurveda',
      problem: 'Poor dermal bioavailability, chemical instability, and rapid degradation of topical curcumin in open wound healing.',
      solution: 'A stable topical emulgel incorporating standardized Curcuma longa rhizome extract with piperine in a carbopol polymer matrix.',
      ingredients: [
        'Curcuma longa rhizome extract (95% curcuminoids)',
        'Piper nigrum extract / Piperine',
        'Carbopol 940',
        'Triethanolamine',
        'Purified Water'
      ],
      technical_features: [
        'Standardized Curcuma longa extract containing 95% total curcuminoids',
        'Piperine bio-enhancer at 1:10 w/w ratio to curcumin for increased dermal permeation',
        'Topical carbopol emulgel formulation maintaining stable pH 6.0 - 6.5',
        'Demonstrated 2.5-fold acceleration in epithelial wound closure over single herbs'
      ],
      claimed_advantages: 'Enhanced dermal penetration, prolonged active retention, and synergistic wound healing without systemic toxicity.'
    };

    await runAnalysis(demoPayload);
  };

  // ============================================================================
  // LOADING / ERROR / EMPTY STATE
  // ============================================================================
  if (isLoadingRun) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '80px 24px' }}>
        <div className="spinner" style={{ width: '36px', height: '36px', margin: '0 auto 16px' }} />
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
          Loading Analysis Run from MySQL...
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
          Restoring immutable evaluation report and citation audit.
        </p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
        <div style={{ color: 'var(--danger)', marginBottom: '16px' }}>
          <AlertTriangle size={40} style={{ margin: '0 auto' }} />
        </div>
        <h3 style={{ fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
          Failed to Load Historical Run
        </h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '20px' }}>
          {loadError}
        </p>
        <button type="button" className="btn btn-secondary" onClick={() => navigate('/my-innovations')}>
          <ArrowLeft size={16} />
          <span>Back to Innovations</span>
        </button>
      </div>
    );
  }

  if (!analysisResult) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '60px 24px' }}>
        <div style={{ 
          width: '64px', 
          height: '64px', 
          borderRadius: '50%', 
          backgroundColor: 'var(--bg-tertiary)', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center', 
          margin: '0 auto 20px',
          color: 'var(--accent-secondary)'
        }}>
          <FileText size={32} />
        </div>
        
        <h2 style={{ fontSize: '1.4rem', fontWeight: 700, color: '#f8fafc', marginBottom: '8px' }}>
          No Prior-Art Analysis Performed Yet
        </h2>
        
        <p style={{ color: 'var(--text-secondary)', maxWidth: '520px', margin: '0 auto 24px', fontSize: '0.92rem' }}>
          Submit your AYUSH formulation or technical composition in the Innovation Submission workspace to generate a grounded prior-art comparison report.
        </p>

        <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <Link to="/innovation" className="btn btn-primary">
            <span>Go to Innovation Submission</span>
          </Link>
          <button 
            onClick={handleRunDemo} 
            disabled={isAnalyzing}
            className="btn btn-secondary"
          >
            <Sparkles size={16} color="var(--accent-secondary)" />
            <span>{isAnalyzing ? 'Running Demo Analysis...' : 'Run Quick Demonstration Analysis'}</span>
          </button>
        </div>
      </div>
    );
  }

  const { innovation, queries_executed, sources_count, sources, citation_audit, report_markdown, retrieval_status } = analysisResult;

  return (
    <div>
      {/* Top Action & Navigation Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
        <Link to="/innovation" className="btn btn-secondary" style={{ fontSize: '0.85rem' }}>
          <ArrowLeft size={16} />
          <span>Edit Innovation Submission</span>
        </Link>

        <button 
          onClick={handleDownloadMarkdown}
          className="btn btn-primary"
          style={{ fontSize: '0.85rem' }}
        >
          <Download size={16} />
          <span>Download Markdown Report</span>
        </button>
      </div>

      {/* Innovation Profile Overview */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span style={{ 
                fontSize: '0.75rem', 
                fontWeight: 600, 
                padding: '2px 8px', 
                borderRadius: '4px', 
                backgroundColor: 'var(--accent-glow)', 
                color: 'var(--accent-secondary)',
                border: '1px solid rgba(99, 102, 241, 0.3)'
              }}>
                {innovation?.ayush_system || 'AYUSH'}
              </span>
              <span style={{ 
                fontSize: '0.75rem', 
                fontWeight: 600, 
                padding: '2px 8px', 
                borderRadius: '4px', 
                backgroundColor: retrieval_status === 'ZERO_RETRIEVAL' ? 'var(--warning-bg)' : 'var(--success-bg)', 
                color: retrieval_status === 'ZERO_RETRIEVAL' ? 'var(--warning)' : 'var(--success)',
                border: `1px solid ${retrieval_status === 'ZERO_RETRIEVAL' ? 'var(--warning-border)' : 'var(--success-border)'}`
              }}>
                {retrieval_status === 'ZERO_RETRIEVAL' ? 'ZERO RETRIEVAL' : 'EVIDENCE RETRIEVED'}
              </span>
            </div>
            
            <h1 style={{ fontSize: '1.45rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
              {innovation?.title}
            </h1>
            
            <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)' }}>
              <strong>Ingredients:</strong> {innovation?.ingredients?.join(' • ')}
            </p>

            {(analysisResult?.uploaded_documents?.length > 0 || innovation?.uploaded_documents?.length > 0) && (
              <div style={{ marginTop: '8px', fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span className="badge badge-primary" style={{ fontSize: '0.72rem' }}>APPLICANT DOCUMENTS</span>
                <span>
                  {(analysisResult?.uploaded_documents || innovation?.uploaded_documents || [])
                    .map((d) => `${d.filename} (${d.page_count} ${d.page_count === 1 ? 'page' : 'pages'})`)
                    .join(', ')}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Evaluation Disclaimer */}
        <div className="alert alert-warning" style={{ marginTop: '16px', marginBottom: '0' }}>
          <Info size={18} style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '0.85rem' }}>
            <strong>Evaluation Framework:</strong> User-submitted specifications (problem, solution, claimed efficacy)
            represent <strong>unverified applicant claims</strong>. The analysis below evaluates these claims strictly against 
            externally retrieved prior-art evidence. Semantic similarity does not certify legal patentability.
          </div>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="grid-3" style={{ marginBottom: '20px' }}>
        <div className="stat-box">
          <div className="stat-label">Sub-Queries Executed</div>
          <div className="stat-value" style={{ color: '#818cf8' }}>
            {queries_executed?.length || 0}
          </div>
          <div className="stat-caption">Botanical, patent & feature queries</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Evidence Passages</div>
          <div className="stat-value" style={{ color: '#34d399' }}>
            {sources_count || 0}
          </div>
          <div className="stat-caption">ChromaDB multi-collection chunks</div>
        </div>

        <div className="stat-box">
          <div className="stat-label">Citation Audit Status</div>
          <div className="stat-value" style={{ fontSize: '1.25rem', color: '#38bdf8', marginTop: '10px' }}>
            {citation_audit?.status === 'ID_MATCH_CONFIRMED' ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#34d399' }}>
                <CheckCircle size={20} />
                <span>ID Confirmed</span>
              </span>
            ) : citation_audit?.status === 'MISSING_CITATIONS' ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#fbbf24' }}>
                <AlertTriangle size={20} />
                <span>Missing IDs</span>
              </span>
            ) : (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#f87171' }}>
                <XCircle size={20} />
                <span>Unverified IDs</span>
              </span>
            )}
          </div>
          <div className="stat-caption">Validates document chunk IDs only</div>
        </div>
      </div>

      {/* Citation Audit Details Box */}
      <div className="card" style={{ marginBottom: '20px', padding: '16px 20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <ShieldCheck size={20} color="var(--accent-secondary)" />
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#f8fafc' }}>
            Citation ID Verification Notice
          </h3>
        </div>
        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
          {citation_audit?.status === 'ID_MATCH_CONFIRMED' && (
            <span>
              ✓ All <strong>{citation_audit.valid_citations?.length || 0}</strong> cited chunk ID(s) strictly match records retrieved from the knowledge base.
            </span>
          )}
          {citation_audit?.status === 'MISSING_CITATIONS' && (
            <span>
              ⚠️ The report contains statements without explicit chunk citation tags.
            </span>
          )}
          {citation_audit?.status === 'FABRICATED_OR_UNMATCHED_IDS' && (
            <span style={{ color: '#f87171' }}>
              ❌ The report generated citation IDs not present in retrieved evidence: <code>{citation_audit.invalid_citations?.join(', ')}</code>.
            </span>
          )}
          {citation_audit?.status === 'NO_EVIDENCE_AVAILABLE' && (
            <span>
              ℹ️ Zero external chunks retrieved; all features evaluated as <code>NOT_FOUND_IN_CORPUS</code>.
            </span>
          )}
        </p>
        <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '6px', fontStyle: 'italic' }}>
          *Disclaimer: Verifies document reference IDs only; does not prove semantic factual truth or statutory patentability under the Indian Patents Act.
        </p>
      </div>

      {/* Executed Queries Accordion */}
      <div className="card" style={{ marginBottom: '20px', padding: '16px 20px' }}>
        <div 
          onClick={() => setShowQueries(!showQueries)}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: 'pointer' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            <Search size={18} color="var(--accent-primary)" />
            <span>Targeted Sub-Queries Executed ({queries_executed?.length || 0})</span>
          </div>
          {showQueries ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
        </div>

        {showQueries && (
          <div style={{ marginTop: '14px', borderTop: '1px solid var(--border-subtle)', paddingTop: '12px' }}>
            {queries_executed?.map((q, idx) => (
              <div 
                key={idx} 
                style={{ 
                  display: 'flex', 
                  gap: '8px', 
                  fontSize: '0.84rem', 
                  marginBottom: '6px',
                  backgroundColor: 'var(--bg-secondary)',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  fontFamily: 'var(--font-mono)',
                  color: '#a5b4fc'
                }}
              >
                <span style={{ color: 'var(--text-muted)' }}>{idx + 1}.</span>
                <span>{q}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Main Markdown Report Body */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <div className="card-title">
            <BookOpen size={20} color="var(--accent-primary)" />
            <span>Prior-Art Assessment Report</span>
          </div>
        </div>

        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {report_markdown}
          </ReactMarkdown>
        </div>
      </div>

      {/* Expandable Evidence Passages Inspector */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Database size={20} color="var(--accent-secondary)" />
            <span>Retrieved Evidence Passages & Source Audits ({sources?.length || 0})</span>
          </div>

          {sources && sources.length > 0 && (
            <div style={{ display: 'flex', gap: '8px' }}>
              <button 
                onClick={expandAllSources}
                className="btn btn-secondary"
                style={{ padding: '4px 10px', fontSize: '0.78rem' }}
              >
                Expand All
              </button>
              <button 
                onClick={collapseAllSources}
                className="btn btn-secondary"
                style={{ padding: '4px 10px', fontSize: '0.78rem' }}
              >
                Collapse All
              </button>
            </div>
          )}
        </div>

        {!sources || sources.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', padding: '16px 0' }}>
            No external evidence chunks were retrieved from the pilot knowledge base.
          </div>
        ) : (
          sources.map((src, idx) => {
            const isExpanded = !!expandedSources[idx];
            return (
              <div key={idx} className="evidence-card">
                <div className="evidence-header" onClick={() => toggleSource(idx)}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ 
                      fontSize: '0.78rem', 
                      fontWeight: 700, 
                      color: 'var(--accent-secondary)',
                      backgroundColor: 'var(--accent-glow)',
                      padding: '2px 8px',
                      borderRadius: '4px'
                    }}>
                      #{idx + 1}
                    </span>
                    <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {src.source}
                    </span>
                    <span style={{ 
                      fontSize: '0.75rem', 
                      color: 'var(--text-muted)', 
                      backgroundColor: 'var(--bg-tertiary)', 
                      padding: '2px 6px', 
                      borderRadius: '4px' 
                    }}>
                      {src.document_type || 'reference'}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {src.collection} • Page {src.page ?? 'N/A'}
                    </span>
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </div>
                </div>

                {isExpanded && (
                  <div className="evidence-body">
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '10px', fontSize: '0.82rem', marginBottom: '12px' }}>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Collection: </span>
                        <code style={{ color: '#818cf8' }}>{src.collection}</code>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Chunk ID: </span>
                        <code style={{ color: '#38bdf8' }}>{src.id}</code>
                      </div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Section: </span>
                        <span>{src.section || 'body'}</span>
                      </div>
                    </div>

                    <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                      Supporting Passage Text:
                    </div>
                    <div className="passage-quote">
                      {src.text || src.evidence || 'Passage text not available.'}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
