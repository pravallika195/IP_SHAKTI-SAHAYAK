import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Bot,
  User,
  Send,
  Plus,
  Trash2,
  RotateCcw,
  Sparkles,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  Languages,
  BookOpen,
  Layers,
  FileText,
  AlertCircle
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  chatAssistant,
  resetAssistant,
  getAssistantThreads,
  getAssistantThread,
  createAssistantThread,
  deleteAssistantThread
} from '../api/client';

// Prompt suggestion templates
const PROMPT_SUGGESTIONS = [
  {
    tag: 'Phytochemistry',
    text: 'What phytochemicals and bioactive compounds are reported in Curcuma longa (turmeric)?',
  },
  {
    tag: 'Formulations',
    text: 'Which Ayurvedic polyherbal formulations contain Haridra for skin disorders and wound healing?',
  },
  {
    tag: 'Patent Claims',
    text: 'Compare traditional therapeutic uses of turmeric with modern patent claims on curcuminoids.',
  },
  {
    tag: 'Patentability',
    text: 'What are the patentability requirements under Section 3(p) and 3(e) for herbal formulations?',
  },
];

// Helper to generate a unique session ID
function generateSessionId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 9);
}

// Helper to format ISO timestamp
function formatTime(isoString) {
  if (!isoString) return '';
  const date = new Date(isoString);
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Helper to generate a fresh default session
function createDefaultSession() {
  const initialId = generateSessionId();
  return [
    {
      id: initialId,
      title: 'New Research Thread',
      language: 'English',
      createdAt: new Date().toISOString(),
      messages: [],
      loaded: true,
    },
  ];
}

export default function PatentAssistant() {
  const { isAuthenticated, user } = useAuth();

  // Initialize clean conversation sessions (strictly per user)
  const [sessions, setSessions] = useState(() => createDefaultSession());
  const [activeSessionId, setActiveSessionId] = useState(() => sessions[0].id);
  const [inputQuery, setInputQuery] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState(null);
  const [expandedSources, setExpandedSources] = useState({});

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Sync strictly with MySQL threads per authenticated user
  useEffect(() => {
    let isMounted = true;

    if (isAuthenticated && user?.id) {
      async function loadRemoteThreads() {
        try {
          const data = await getAssistantThreads();
          if (!isMounted) return;

          if (data.threads && data.threads.length > 0) {
            const remoteSessions = data.threads.map((t) => ({
              id: t.id,
              title: t.title,
              language: t.language || 'English',
              createdAt: t.created_at,
              messages: [],
              loaded: false,
            }));
            setSessions(remoteSessions);
            setActiveSessionId(remoteSessions[0].id);

            // Fetch full messages & sources for first thread
            const threadDetail = await getAssistantThread(remoteSessions[0].id);
            if (isMounted && threadDetail.thread?.messages) {
              setSessions((prev) =>
                prev.map((s) =>
                  s.id === remoteSessions[0].id
                    ? {
                        ...s,
                        messages: threadDetail.thread.messages.map((m) => ({
                          id: m.id,
                          role: m.role,
                          content: m.content,
                          category: m.category,
                          standaloneQuery: m.standalone_query,
                          resolvedQuery: m.resolved_query,
                          citationAudit: m.citation_audit,
                          sources: m.sources || [],
                          timestamp: m.created_at,
                        })),
                        loaded: true,
                      }
                    : s
                )
              );
            }
          } else {
            // Authenticated user has 0 saved threads in MySQL -> Clean fresh state
            const fresh = createDefaultSession();
            setSessions(fresh);
            setActiveSessionId(fresh[0].id);
          }
        } catch (err) {
          console.warn('Could not load remote threads from MySQL:', err);
        }
      }

      loadRemoteThreads();
    } else {
      // Unauthenticated / Logged out -> Reset to clean independent guest session
      const fresh = createDefaultSession();
      setSessions(fresh);
      setActiveSessionId(fresh[0].id);
    }

    return () => {
      isMounted = false;
    };
  }, [isAuthenticated, user?.id]);

  // Current active session
  const activeSession = sessions.find((s) => s.id === activeSessionId) || sessions[0] || {
    id: activeSessionId,
    title: 'New Research Thread',
    language: 'English',
    createdAt: new Date().toISOString(),
    messages: [],
    loaded: true,
  };

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeSession?.messages, isSending]);

  // Handle creating a new research thread
  const handleNewThread = async () => {
    const newId = generateSessionId();
    const newSession = {
      id: newId,
      title: 'New Research Thread',
      language: activeSession.language || 'English',
      createdAt: new Date().toISOString(),
      messages: [],
      loaded: true,
    };

    if (isAuthenticated) {
      try {
        await createAssistantThread({
          session_id: newId,
          title: 'New Research Thread',
          language: newSession.language,
        });
      } catch (err) {
        console.warn('Could not persist new thread to MySQL:', err);
      }
    }

    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);
    setInputQuery('');
    setSendError(null);
  };

  // Handle switching active thread and loading history from MySQL
  const handleSelectThread = async (id) => {
    setActiveSessionId(id);
    setSendError(null);

    if (isAuthenticated) {
      const target = sessions.find((s) => s.id === id);
      if (target && !target.loaded) {
        try {
          const detail = await getAssistantThread(id);
          if (detail.thread?.messages) {
            setSessions((prev) =>
              prev.map((s) =>
                s.id === id
                  ? {
                      ...s,
                      messages: detail.thread.messages.map((m) => ({
                        id: m.id,
                        role: m.role,
                        content: m.content,
                        category: m.category,
                        standaloneQuery: m.standalone_query,
                        resolvedQuery: m.resolved_query,
                        citationAudit: m.citation_audit,
                        sources: m.sources || [],
                        timestamp: m.created_at,
                      })),
                      loaded: true,
                    }
                  : s
              )
            );
          }
        } catch (err) {
          console.warn('Failed to load thread messages:', err);
        }
      }
    }
  };

  // Handle deleting a thread
  const handleDeleteThread = async (id, e) => {
    e.stopPropagation();
    try {
      if (isAuthenticated) {
        await deleteAssistantThread(id);
      } else {
        await resetAssistant(id);
      }
    } catch (err) {
      console.warn(`Could not delete thread ${id}:`, err);
    }

    setSessions((prev) => {
      const filtered = prev.filter((s) => s.id !== id);
      if (filtered.length === 0) {
        const freshId = generateSessionId();
        const freshSession = {
          id: freshId,
          title: 'New Research Thread',
          language: 'English',
          createdAt: new Date().toISOString(),
          messages: [],
          loaded: true,
        };
        setActiveSessionId(freshId);
        return [freshSession];
      }
      if (activeSessionId === id) {
        setActiveSessionId(filtered[0].id);
      }
      return filtered;
    });
  };

  // Handle resetting the current active session
  const handleResetActiveThread = async () => {
    if (!window.confirm('Reset this conversation? This clears memory on both backend and client.')) {
      return;
    }
    try {
      await resetAssistant(activeSession.id);
    } catch (err) {
      console.warn(`Error resetting session ${activeSession.id}:`, err);
    }

    setSessions((prev) =>
      prev.map((s) => (s.id === activeSession.id ? { ...s, title: 'New Research Thread', messages: [] } : s))
    );
    setSendError(null);
  };

  // Handle changing language for current session
  const handleLanguageChange = (newLang) => {
    setSessions((prev) =>
      prev.map((s) => (s.id === activeSession.id ? { ...s, language: newLang } : s))
    );
  };

  // Toggle evidence sources accordion for a specific message
  const toggleSources = (msgId) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  // Core send message handler
  const handleSendMessage = async (queryToSend) => {
    const query = (queryToSend || inputQuery).trim();
    if (!query || isSending) return;

    setSendError(null);
    setInputQuery('');

    const userMessageId = 'msg_user_' + Date.now();
    const userMessage = {
      id: userMessageId,
      role: 'user',
      content: query,
      timestamp: new Date().toISOString(),
    };

    // Update active session title if it's the first message
    const isFirstMessage = activeSession.messages.length === 0;
    const newTitle = isFirstMessage
      ? query.length > 32
        ? query.substring(0, 32) + '...'
        : query
      : activeSession.title;

    // Optimistically append user message
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSession.id) {
          return {
            ...s,
            title: newTitle,
            messages: [...s.messages, userMessage],
          };
        }
        return s;
      })
    );

    setIsSending(true);

    try {
      // Auto-detect Indic script in query or fall back to active session language
      const isTelugu = /[\u0C00-\u0C7F]/.test(query);
      const isHindi = /[\u0900-\u097F]/.test(query);
      const queryLanguage = isTelugu ? 'Telugu' : isHindi ? 'Hindi' : (activeSession.language || 'English');

      const response = await chatAssistant({
        sessionId: activeSession.id,
        query: query,
        language: queryLanguage,
      });

      const effectiveLanguage = response.language || queryLanguage;
      const assistantMessageId = 'msg_ast_' + Date.now();
      const assistantMessage = {
        id: assistantMessageId,
        role: 'assistant',
        content: response.answer || 'No response generated.',
        category: response.category || 'AYUSH_RESEARCH',
        standaloneQuery: response.standalone_query || '',
        resolvedQuery: response.resolved_query || '',
        sources: response.sources || [],
        citationAudit: response.citation_audit || null,
        timestamp: new Date().toISOString(),
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSession.id) {
            return {
              ...s,
              language: effectiveLanguage,
              messages: [...s.messages, assistantMessage],
            };
          }
          return s;
        })
      );
    } catch (err) {
      console.error('Chat request failed:', err);
      const errorMsg = err.message || 'Failed to communicate with Patent Assistant service.';
      setSendError(errorMsg);

      const errorAssistantMessage = {
        id: 'msg_err_' + Date.now(),
        role: 'assistant',
        content: `**Error:** ${errorMsg}\n\nPlease verify that the backend API gateway is running on port 5000 and try again.`,
        category: 'ERROR',
        isError: true,
        sources: [],
        citationAudit: null,
        timestamp: new Date().toISOString(),
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSession.id) {
            return {
              ...s,
              messages: [...s.messages, errorAssistantMessage],
            };
          }
          return s;
        })
      );
    } finally {
      setIsSending(false);
      // Refocus input
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  };

  // Handle textarea enter key
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Render intent badge with semantic styling
  const renderIntentBadge = (category) => {
    switch (category) {
      case 'AYUSH_RESEARCH':
        return <span className="intent-badge intent-badge-ayush">AYUSH Prior-Art</span>;
      case 'FOLLOW_UP':
        return <span className="intent-badge intent-badge-followup">Contextual Follow-up</span>;
      case 'GREETING':
        return <span className="intent-badge intent-badge-greeting">Greeting</span>;
      case 'TIME_GREETING':
        return <span className="intent-badge intent-badge-greeting">Time Greeting</span>;
      case 'GRATITUDE':
        return <span className="intent-badge intent-badge-greeting">Gratitude</span>;
      case 'ACKNOWLEDGEMENT':
        return <span className="intent-badge intent-badge-greeting">Acknowledgement</span>;
      case 'IDENTITY':
        return <span className="intent-badge intent-badge-greeting">System Identity</span>;
      case 'FAREWELL':
        return <span className="intent-badge intent-badge-greeting">Farewell</span>;
      case 'CLARIFICATION':
        return <span className="intent-badge intent-badge-warning">Clarification</span>;
      case 'OUT_OF_DOMAIN':
        return <span className="intent-badge intent-badge-outofdomain">Out-of-Domain Notice</span>;
      default:
        return category ? <span className="intent-badge intent-badge-ayush">{category}</span> : null;
    }
  };

  // Render citation audit badge
  const renderCitationAuditBadge = (audit) => {
    if (!audit || !audit.status) return null;

    switch (audit.status) {
      case 'ID_MATCH_CONFIRMED':
        return (
          <span className="citation-audit-badge audit-confirmed" title="Every citation ID strictly corresponds to a retrieved chunk.">
            <CheckCircle2 size={13} />
            <span>Citations Verified ({audit.valid_citations?.length || 0})</span>
          </span>
        );
      case 'MISSING_CITATIONS':
        return (
          <span className="citation-audit-badge audit-missing" title="Synthesized answer omitted bracketed chunk citations.">
            <AlertTriangle size={13} />
            <span>Citations Missing</span>
          </span>
        );
      case 'FABRICATED_OR_UNMATCHED_IDS':
        return (
          <span className="citation-audit-badge audit-unmatched" title="Some bracketed IDs did not match retrieved chunks.">
            <AlertTriangle size={13} />
            <span>Unmatched Citations ({audit.invalid_citations?.length || 0})</span>
          </span>
        );
      case 'NO_EVIDENCE_AVAILABLE':
        return (
          <span className="citation-audit-badge audit-noevidence">
            <span>No Evidence Required</span>
          </span>
        );
      default:
        return null;
    }
  };

  return (
    <div className="assistant-workspace">
      {/* ------------------------------------------------------------- */}
      {/* Left Pane: Conversation Threads Sidebar                       */}
      {/* ------------------------------------------------------------- */}
      <aside className="assistant-threads-pane">
        <div className="threads-header">
          <button className="btn-new-thread" onClick={handleNewThread}>
            <Plus size={16} />
            <span>New Research Thread</span>
          </button>
        </div>

        <div className="threads-list">
          {sessions.length === 0 ? (
            <div className="threads-empty">No conversations yet.</div>
          ) : (
            sessions.map((thread) => {
              const isActive = thread.id === activeSession.id;
              const msgCount = thread.messages?.length || 0;
              return (
                <div
                  key={thread.id}
                  className={`thread-item ${isActive ? 'active' : ''}`}
                  onClick={() => handleSelectThread(thread.id)}
                >
                  <div className="thread-info">
                    <div className="thread-title">{thread.title || 'Untitled Thread'}</div>
                    <div className="thread-meta">
                      <span>{msgCount} {msgCount === 1 ? 'turn' : 'turns'}</span>
                      <span>•</span>
                      <span>{thread.language || 'English'}</span>
                    </div>
                  </div>
                  <button
                    className="thread-delete-btn"
                    title="Delete Thread"
                    onClick={(e) => handleDeleteThread(thread.id, e)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </aside>

      {/* ------------------------------------------------------------- */}
      {/* Right Pane: Main Conversational Assistant                     */}
      {/* ------------------------------------------------------------- */}
      <section className="assistant-chat-main">
        {/* Chat Header */}
        <header className="chat-header">
          <div className="chat-header-title">
            <Bot size={20} color="var(--accent-secondary)" />
            <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '300px' }}>
              {activeSession.title}
            </span>
            <span className="chat-session-badge" title={activeSession.id}>
              {activeSession.id.substring(0, 10)}...
            </span>
          </div>

          <div className="chat-header-actions">
            {/* Language Selector */}
            <div className="lang-selector-group" title="Target response language for synthesis">
              <Languages size={15} color="var(--text-muted)" />
              <select
                className="chat-lang-select"
                value={activeSession.language || 'English'}
                onChange={(e) => handleLanguageChange(e.target.value)}
              >
                <option value="English">English</option>
                <option value="Hindi">हिंदी (Hindi)</option>
                <option value="Telugu">తెలుగు (Telugu)</option>
              </select>
            </div>

            {/* Reset History Button */}
            <button
              className="chat-btn-reset"
              onClick={handleResetActiveThread}
              title="Reset conversation context on backend & clear chat"
            >
              <RotateCcw size={14} />
              <span>Reset Context</span>
            </button>
          </div>
        </header>

        {/* Chat Messages Scroll Container */}
        <div className="chat-messages-scroll">
          {activeSession.messages.length === 0 ? (
            /* Welcome Hero & Suggestions */
            <div className="assistant-welcome-hero">
              <div className="welcome-icon-box">
                <Bot size={30} color="var(--accent-secondary)" />
              </div>
              <h2 className="welcome-hero-title">Patent & Prior-Art Assistant</h2>
              <p className="welcome-hero-desc">
                Multi-collection conversational intelligence grounded in AYUSH Ayurvedic formulations,
                Curcuma longa phytochemicals, and verified patent prior art. Strict citations and honest abstention enforced.
              </p>

              <div className="prompt-suggestions-grid">
                {PROMPT_SUGGESTIONS.map((sugg, idx) => (
                  <div
                    key={idx}
                    className="prompt-suggestion-pill"
                    onClick={() => handleSendMessage(sugg.text)}
                  >
                    <span className="suggestion-tag">{sugg.tag}</span>
                    <span className="suggestion-text">{sugg.text}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Render Messages */
            activeSession.messages.map((msg) => {
              const isUser = msg.role === 'user';
              const isExpanded = !!expandedSources[msg.id];

              if (isUser) {
                return (
                  <div key={msg.id} className="chat-row chat-row-user">
                    <div className="chat-bubble-user">
                      <div>{msg.content}</div>
                      <div className="chat-timestamp">{formatTime(msg.timestamp)}</div>
                    </div>
                    <div className="chat-avatar chat-avatar-user">
                      <User size={18} />
                    </div>
                  </div>
                );
              }

              // Assistant message
              return (
                <div key={msg.id} className="chat-row chat-row-assistant">
                  <div className="chat-avatar chat-avatar-assistant">
                    <Bot size={18} />
                  </div>

                  <div className="chat-bubble-assistant">
                    {/* Metadata Strip */}
                    <div className="chat-meta-bar">
                      {renderIntentBadge(msg.category)}

                      {/* Display resolved query tag if follow-up changed the prompt */}
                      {msg.resolvedQuery &&
                        msg.resolvedQuery.trim() !== '' &&
                        msg.category === 'FOLLOW_UP' && (
                          <span
                            className="resolved-query-tag"
                            title="Underlying standalone query rewritten by PatentAssistantEngine"
                          >
                            Resolved: "{msg.resolvedQuery}"
                          </span>
                        )}

                      {renderCitationAuditBadge(msg.citationAudit)}

                      <span style={{ marginLeft: 'auto', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                        {formatTime(msg.timestamp)}
                      </span>
                    </div>

                    {/* Markdown Answer */}
                    <div className="chat-markdown">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                    </div>

                    {/* Expandable Evidence Drawer (when sources are present) */}
                    {msg.sources && msg.sources.length > 0 && (
                      <div>
                        <div
                          className="chat-evidence-toggle"
                          onClick={() => toggleSources(msg.id)}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <BookOpen size={14} color="var(--accent-secondary)" />
                            <span style={{ fontWeight: 600 }}>
                              Retrieved Prior-Art Evidence ({msg.sources.length} {msg.sources.length === 1 ? 'passage' : 'passages'})
                            </span>
                          </div>
                          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                        </div>

                        {isExpanded && (
                          <div className="chat-evidence-list">
                            {msg.sources.map((src, sIdx) => {
                              const docType = src.document_type || 'other';
                              const collection = src.collection || 'corpus';
                              const passage = src.evidence || src.text || 'No passage text provided.';

                              return (
                                <div key={src.id || sIdx} className="chat-evidence-card">
                                  <div className="chat-evidence-header">
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                                      <span
                                        className={`badge ${
                                          docType === 'patent' ? 'badge-primary' : 'badge-success'
                                        }`}
                                      >
                                        {docType.toUpperCase()}
                                      </span>
                                      <span
                                        style={{
                                          fontSize: '0.74rem',
                                          fontFamily: 'var(--font-mono)',
                                          color: 'var(--text-muted)',
                                        }}
                                      >
                                        {collection}
                                      </span>
                                      {src.page && src.page !== 'N/A' && (
                                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                          p. {src.page}
                                        </span>
                                      )}
                                      {src.section && (
                                        <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                          sec: {src.section}
                                        </span>
                                      )}
                                    </div>

                                    <code style={{ fontSize: '0.7rem', color: 'var(--accent-secondary)' }}>
                                      {src.id || `chunk_${sIdx}`}
                                    </code>
                                  </div>

                                  <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                                    {src.source || 'Unnamed Document'}
                                  </div>

                                  <div className="chat-evidence-passage">
                                    "{passage}"
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {/* Thinking / In-Flight Indicator */}
          {isSending && (
            <div className="chat-row chat-row-assistant">
              <div className="chat-avatar chat-avatar-assistant">
                <Bot size={18} />
              </div>
              <div className="typing-bubble">
                <div className="typing-dots">
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                  <div className="typing-dot" />
                </div>
                <span>Retrieving AYUSH & patent evidence, reasoning across context...</span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Chat Composer */}
        <footer className="chat-composer">
          {sendError && (
            <div className="alert alert-danger" style={{ marginBottom: '10px', padding: '8px 12px' }}>
              <AlertCircle size={16} />
              <div style={{ fontSize: '0.82rem' }}>{sendError}</div>
            </div>
          )}

          <div className="composer-input-row">
            <textarea
              ref={textareaRef}
              className="composer-textarea"
              placeholder={`Ask in ${activeSession.language || 'English'} (e.g., 'What are the phytochemicals in turmeric?' or follow up with 'What formulations contain it?'). Press Enter to send...`}
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isSending}
              rows={2}
            />

            <button
              className="composer-send-btn"
              onClick={() => handleSendMessage()}
              disabled={!inputQuery.trim() || isSending}
              title="Send message (Enter)"
            >
              {isSending ? <div className="spinner" style={{ width: '16px', height: '16px' }} /> : <Send size={18} />}
            </button>
          </div>

          <div className="composer-footer-hint">
            <span>
              Grounding enforced against <code>ip_sakti_ayush_v1</code> & <code>ip_sakti_curcuma_test_v1</code> (3,447 chunks).
            </span>
            <span>Shift + Enter for new line</span>
          </div>
        </footer>
      </section>
    </div>
  );
}
