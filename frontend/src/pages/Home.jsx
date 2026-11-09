import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  FileSearch, 
  Bot, 
  FolderKanban, 
  ShieldCheck, 
  BookOpen, 
  FlaskConical, 
  Scale, 
  CheckCircle2, 
  ArrowRight, 
  Sparkles,
  Layers,
  FileText,
  AlertCircle
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Home() {
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Hero Section */}
      <div 
        className="card" 
        style={{ 
          background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)',
          border: '1px solid rgba(99, 102, 241, 0.25)',
          padding: '36px 32px',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        <div style={{ maxWidth: '820px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <span 
              style={{ 
                fontSize: '0.78rem', 
                fontWeight: 600, 
                padding: '4px 10px', 
                borderRadius: '16px', 
                backgroundColor: 'rgba(56, 189, 248, 0.12)', 
                color: '#38bdf8',
                border: '1px solid rgba(56, 189, 248, 0.28)',
                letterSpacing: '0.04em'
              }}
            >
              Analyze your Novality
            </span>
          </div>

          <h1 style={{ fontSize: '2.1rem', fontWeight: 800, color: '#f8fafc', lineHeight: 1.25, marginBottom: '12px' }}>
          AYUSH PRIOR-ART RESEARCH SYSTEM
          </h1>

          <p style={{ fontSize: '1.02rem', color: '#94a3b8', lineHeight: 1.6, marginBottom: '24px' }}>
            IP-SAKTI Sahayak bridges the gap between traditional Indian medicinal knowledge, modern scientific research, and patent examination processes to evaluate the novelty of AYUSH innovations and support patent eligibility assessment</p>

          <div style={{ display: 'flex', gap: '14px', flexWrap: 'wrap' }}>
            <Link to="/innovation" className="btn btn-primary" style={{ padding: '10px 20px', fontSize: '0.95rem' }}>
              <FileSearch size={18} />
              <span>Prior-Art Innovation Analysis</span>
            </Link>

            <Link to="/assistant" className="btn btn-secondary" style={{ padding: '10px 20px', fontSize: '0.95rem' }}>
              <Bot size={18} color="var(--accent-secondary)" />
              <span>Conversational Patent Assistant</span>
            </Link>

            {isAuthenticated && (
              <Link to="/my-innovations" className="btn btn-secondary" style={{ padding: '10px 20px', fontSize: '0.95rem' }}>
                <FolderKanban size={18} color="var(--accent-primary)" />
                <span>My Projects & Runs</span>
              </Link>
            )}
          </div>
        </div>
      </div>

      {/* Primary Workspaces Grid */}
      <div>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '16px' }}>
          Research Workspaces & Capabilities
        </h2>

        <div className="grid-3">
          {/* Card 1: Prior-Art Innovation Evaluation */}
          <div 
            className="card" 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'space-between',
              cursor: 'pointer',
              transition: 'border-color 0.2s, transform 0.2s'
            }}
            onClick={() => navigate('/innovation')}
          >
            <div>
              <div 
                style={{ 
                  width: '44px', 
                  height: '44px', 
                  borderRadius: '10px', 
                  backgroundColor: 'rgba(99, 102, 241, 0.15)', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  marginBottom: '16px',
                  color: 'var(--accent-primary)'
                }}
              >
                <FileSearch size={22} />
              </div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                Prior-Art Novelty Evaluation
              </h3>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '16px' }}>
                Submit single herbs or polyherbal compositions. The engine decomposes technical features, executes multi-query retrieval, and audits claimed synergy against prior knowledge.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.86rem', color: 'var(--accent-primary)', fontWeight: 600 }}>
              <span>Launch Submission Workspace</span>
              <ArrowRight size={15} />
            </div>
          </div>

          {/* Card 2: Conversational Patent Assistant */}
          <div 
            className="card" 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'space-between',
              cursor: 'pointer',
              transition: 'border-color 0.2s, transform 0.2s'
            }}
            onClick={() => navigate('/assistant')}
          >
            <div>
              <div 
                style={{ 
                  width: '44px', 
                  height: '44px', 
                  borderRadius: '10px', 
                  backgroundColor: 'rgba(56, 189, 248, 0.15)', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  marginBottom: '16px',
                  color: '#38bdf8'
                }}
              >
                <Bot size={22} />
              </div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                Conversational Patent Assistant
              </h3>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '16px' }}>
                Interact in English, Hindi, or Telugu. Ask about botanical synonyms, therapeutic indications, classical recipes, or examination guidelines with verified passage citations.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.86rem', color: '#38bdf8', fontWeight: 600 }}>
              <span>Open Research Assistant</span>
              <ArrowRight size={15} />
            </div>
          </div>

          {/* Card 3: Project Workspaces & Versioning */}
          <div 
            className="card" 
            style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              justifyContent: 'space-between',
              cursor: 'pointer',
              transition: 'border-color 0.2s, transform 0.2s'
            }}
            onClick={() => navigate(isAuthenticated ? '/my-innovations' : '/login')}
          >
            <div>
              <div 
                style={{ 
                  width: '44px', 
                  height: '44px', 
                  borderRadius: '10px', 
                  backgroundColor: 'rgba(16, 185, 129, 0.15)', 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  marginBottom: '16px',
                  color: '#10b981'
                }}
              >
                <FolderKanban size={22} />
              </div>
              <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
                Immutable Project Workspaces
              </h3>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '16px' }}>
                Save draft claims, track evolutionary versions, attach confidential specifications (PDF/DOCX/TXT), and preserve immutable historical audit records.
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.86rem', color: '#10b981', fontWeight: 600 }}>
              <span>{isAuthenticated ? 'View My Projects' : 'Sign In to Access'}</span>
              <ArrowRight size={15} />
            </div>
          </div>
        </div>
      </div>

      {/* Authoritative Knowledge Repositories */}
      <div>
        <div style={{ marginBottom: '16px' }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Curated Traditional Knowledge & Prior-Art Sources
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Indexed against verified Indian medicinal treatises, standardized phytochemical bioactivity profiles, and patent examination manuals.
          </p>
        </div>

        <div className="grid-3">
          <div className="card" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
              <BookOpen size={20} color="var(--accent-secondary)" />
              <h3 style={{ fontSize: '1.02rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Classical Formularies (AFI / API)
              </h3>
            </div>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Comprehensive Ayurvedic, Siddha, and Unani classical formulation texts, preparation guidelines, classical indications, and traditional therapeutic uses recognized under the First Schedule of the Drugs and Cosmetics Act.
            </p>
          </div>

          <div className="card" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
              <FlaskConical size={20} color="var(--accent-primary)" />
              <h3 style={{ fontSize: '1.02rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Phytochemical Profiles (IMPPAT)
              </h3>
            </div>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Standardized plant part extracts, bioactive secondary metabolites, Curcuma bioactivity data, and botanical nomenclature mappings preventing cosmetic renaming from bypassing prior-art detection.
            </p>
          </div>

          <div className="card" style={{ backgroundColor: 'var(--bg-secondary)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px' }}>
              <Scale size={20} color="#10b981" />
              <h3 style={{ fontSize: '1.02rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                Patent Office Guidelines
              </h3>
            </div>
            <p style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Indian Patent Office (IPO) Guidelines for Examination of Patent Applications relating to Traditional Knowledge and Biological Materials under Section 3(p) and synergy requirements under Section 3(e).
            </p>
          </div>
        </div>
      </div>

      {/* 3-Step Methodology Workflow */}
      <div className="card" style={{ border: '1px solid var(--border-subtle)' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '18px' }}>
          Statutory Prior-Art Examination Methodology
        </h2>

        <div className="grid-3" style={{ gap: '20px' }}>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <div 
              style={{ 
                width: '32px', 
                height: '32px', 
                borderRadius: '50%', 
                backgroundColor: 'rgba(99, 102, 241, 0.2)', 
                color: 'var(--accent-primary)',
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.9rem',
                flexShrink: 0
              }}
            >
              1
            </div>
            <div>
              <h4 style={{ fontSize: '0.98rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Specification Intake
              </h4>
              <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Enter ingredients, extract ratios, and distinguishing technical features, or attach draft specifications (PDF/DOCX/TXT).
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <div 
              style={{ 
                width: '32px', 
                height: '32px', 
                borderRadius: '50%', 
                backgroundColor: 'rgba(56, 189, 248, 0.2)', 
                color: '#38bdf8',
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.9rem',
                flexShrink: 0
              }}
            >
              2
            </div>
            <div>
              <h4 style={{ fontSize: '0.98rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Multi-Corpus Grounding
              </h4>
              <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Hybrid dense semantic and lexical BM25 retrieval across traditional formularies and granted prior art identifies relevant disclosures.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <div 
              style={{ 
                width: '32px', 
                height: '32px', 
                borderRadius: '50%', 
                backgroundColor: 'rgba(16, 185, 129, 0.2)', 
                color: '#10b981',
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '0.9rem',
                flexShrink: 0
              }}
            >
              3
            </div>
            <div>
              <h4 style={{ fontSize: '0.98rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                Statutory Novelty Audit
              </h4>
              <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                Generates feature-by-feature prior-art comparison table with passage citations, auditing novelty against classical knowledge.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Advisory Notice */}
      <div className="alert alert-warning" style={{ margin: 0 }}>
        <AlertCircle size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '0.86rem', lineHeight: 1.5 }}>
          <strong>Statutory Research Advisory:</strong> Semantic similarity scoring and automated prior-art analysis assist researchers and patent attorneys in identifying potential conflicts with traditional Indian medicine. Final determinations regarding patentability under Section 3(p) (Traditional Knowledge) and Section 3(e) (Mere Admixture) rest solely with the Controller General of Patents, Designs and Trade Marks (CGPDTM).
        </div>
      </div>
    </div>
  );
}
