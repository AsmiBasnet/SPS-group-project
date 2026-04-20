import { useState, useRef, useEffect } from "react";
import Layout from "../components/Layout";
import api from "../api";

const EMPLOYEE_TYPES = ["", "Full-time", "Part-time", "Contract", "Intern", "Manager"];
const CATEGORIES = [
  "", "Leave & Absence", "Harassment & Conduct", "Compensation & Benefits",
  "Performance", "Termination", "Remote Work", "Safety & Health", "Other",
];

const QUICK_QUESTIONS = [
  "Am I eligible for FMLA leave?",
  "How do I report workplace harassment?",
  "What is the remote work policy?",
  "What are the performance review criteria?",
];

const DECISION_META = {
  ANSWER:        { label: "Policy Answer",   color: "#10b981", bg: "rgba(16,185,129,0.07)",  border: "rgba(16,185,129,0.2)",  icon: "✅", tag: "tag-green" },
  CLARIFY:       { label: "Needs Clarity",   color: "#3b82f6", bg: "rgba(59,130,246,0.07)",  border: "rgba(59,130,246,0.2)",  icon: "💡", tag: "tag-blue"  },
  FLAG_CONFLICT: { label: "Policy Conflict", color: "#f59e0b", bg: "rgba(245,158,11,0.07)",  border: "rgba(245,158,11,0.2)",  icon: "⚠️", tag: "tag-amber" },
  REFUSED:       { label: "Out of Scope",    color: "#ef4444", bg: "rgba(239,68,68,0.07)",   border: "rgba(239,68,68,0.2)",   icon: "🚫", tag: "tag-red"   },
};

function TypingIndicator() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0.75rem 0" }}>
      <div style={{
        width: 32, height: 32, borderRadius: "50%",
        background: "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(139,92,246,0.2))",
        border: "1px solid rgba(99,102,241,0.25)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "0.9rem", flexShrink: 0,
      }}>🛡️</div>
      <div style={{
        display: "flex", alignItems: "center", gap: 4,
        padding: "0.6rem 1rem",
        background: "var(--surface-up)",
        border: "1px solid var(--border)",
        borderRadius: "0 14px 14px 14px",
      }}>
        {[0,1,2].map(i => (
          <div key={i} style={{
            width: 7, height: 7, borderRadius: "50%",
            background: "var(--indigo)",
            animation: `bounce-dot 1.2s ease-in-out ${i*0.2}s infinite`,
          }} />
        ))}
      </div>
      <span style={{ fontSize: "0.75rem", color: "var(--text-3)" }}>
        Analyzing policies…
      </span>
      <style>{`
        @keyframes bounce-dot {
          0%,60%,100% { transform: translateY(0); opacity:0.4; }
          30%          { transform: translateY(-5px); opacity:1; }
        }
      `}</style>
    </div>
  );
}

function ResponseCard({ msg }) {
  const meta = DECISION_META[msg.decision] || DECISION_META.CLARIFY;
  const [showReason, setShowReason] = useState(false);

  return (
    <div className="fade-in" style={{ display: "flex", gap: 10, alignItems: "flex-start", marginBottom: "1.25rem" }}>
      {/* Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
        background: "linear-gradient(135deg, rgba(99,102,241,0.3), rgba(139,92,246,0.2))",
        border: "1px solid rgba(99,102,241,0.25)",
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "0.9rem", marginTop: 2,
      }}>🛡️</div>

      <div style={{ flex: 1 }}>
        {/* Sender label */}
        <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-3)", marginBottom: 5, display: "flex", alignItems: "center", gap: 8 }}>
          PolicyGuard AI
          <span className={`tag ${meta.tag}`}>{meta.icon} {meta.label}</span>
          {msg.confidence && <span style={{ color: "var(--text-3)", fontWeight: 400 }}>· {msg.confidence}</span>}
          {msg.latency > 0 && <span style={{ color: "var(--text-3)", fontWeight: 400 }}>· {msg.latency?.toFixed(1)}s</span>}
        </div>

        {/* Answer bubble */}
        <div style={{
          background: meta.bg,
          border: `1px solid ${meta.border}`,
          borderRadius: "0 14px 14px 14px",
          padding: "1rem 1.25rem",
          fontSize: "0.9rem", lineHeight: 1.75,
          whiteSpace: "pre-wrap",
        }}>
          {msg.answer}
        </div>

        {/* Clarification box */}
        {msg.clarification_question && (
          <div style={{
            marginTop: 8,
            padding: "0.7rem 1rem",
            background: "rgba(59,130,246,0.08)",
            border: "1px solid rgba(59,130,246,0.2)",
            borderRadius: 10,
            fontSize: "0.85rem",
            color: "#93c5fd",
            display: "flex", alignItems: "flex-start", gap: 8,
          }}>
            <span>❓</span>
            <span>{msg.clarification_question}</span>
          </div>
        )}

        {/* Conflict comparison */}
        {msg.decision === "FLAG_CONFLICT" && msg.conflict_clause_a && (
          <div style={{ marginTop: 8, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {[
              ["Clause A — This Document", msg.conflict_clause_a],
              ["Clause B — Existing Policy", msg.conflict_clause_b],
            ].map(([label, text]) => (
              <div key={label} style={{
                background: "rgba(245,158,11,0.06)",
                border: "1px solid rgba(245,158,11,0.2)",
                borderRadius: 10, padding: "0.75rem",
              }}>
                <div style={{ fontSize: "0.67rem", fontWeight: 700, color: "#f59e0b", marginBottom: 5, letterSpacing: "0.04em" }}>
                  {label}
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-2)", lineHeight: 1.6 }}>{text}</div>
              </div>
            ))}
          </div>
        )}

        {/* Footer: citation + reasoning */}
        {(msg.citation || msg.reasoning) && (
          <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            {msg.citation && msg.citation !== "N/A" && (
              <div style={{
                display: "flex", alignItems: "center", gap: 5,
                padding: "0.3rem 0.7rem",
                background: "var(--surface-up)",
                border: "1px solid var(--border)",
                borderRadius: 20, fontSize: "0.72rem", color: "var(--text-3)",
              }}>
                📎 <em>{msg.citation}</em>
              </div>
            )}
            {msg.reasoning && (
              <button
                className="btn-ghost"
                style={{ padding: "0.3rem 0.75rem", fontSize: "0.72rem", borderRadius: 20 }}
                onClick={() => setShowReason(v => !v)}
              >
                {showReason ? "▲ Hide" : "▼ Show"} reasoning
              </button>
            )}
          </div>
        )}

        {/* Reasoning box */}
        {showReason && msg.reasoning && (
          <div className="slide-up" style={{
            marginTop: 8,
            padding: "0.9rem 1.1rem",
            background: "rgba(99,102,241,0.06)",
            border: "1px solid rgba(99,102,241,0.15)",
            borderRadius: 10,
            fontSize: "0.82rem", lineHeight: 1.7, color: "var(--text-2)",
          }}>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, color: "#818cf8", marginBottom: 6, letterSpacing: "0.06em" }}>
              🧠 CHAIN-OF-THOUGHT REASONING
            </div>
            {msg.reasoning}
          </div>
        )}
      </div>
    </div>
  );
}

function UserBubble({ msg }) {
  return (
    <div className="fade-in" style={{
      display: "flex", flexDirection: "column", alignItems: "flex-end",
      marginBottom: "1.25rem",
    }}>
      <div style={{ fontSize: "0.75rem", color: "var(--text-3)", marginBottom: 5, display: "flex", alignItems: "center", gap: 8 }}>
        {msg.anonymous && <span className="tag tag-indigo">👤 Anonymous</span>}
        You
      </div>
      <div style={{
        maxWidth: "72%",
        padding: "0.8rem 1.1rem",
        background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))",
        border: "1px solid rgba(99,102,241,0.25)",
        borderRadius: "14px 0 14px 14px",
        fontSize: "0.9rem", lineHeight: 1.65,
        color: "var(--text)",
      }}>
        {msg.text}
      </div>
    </div>
  );
}

export default function Chat() {
  const [question, setQuestion]           = useState("");
  const [employeeType, setEmployeeType]   = useState("");
  const [category, setCategory]           = useState("");
  const [anonymous, setAnonymous]         = useState(false);
  const [messages, setMessages]           = useState([]);
  const [loading, setLoading]             = useState(false);
  const [error, setError]                 = useState("");
  const bottomRef = useRef(null);
  const inputRef  = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (q) => {
    const query = (q || question).trim();
    if (!query || loading) return;
    setQuestion("");
    setError("");
    setMessages(prev => [...prev, { role: "user", text: query, anonymous }]);
    setLoading(true);
    inputRef.current?.focus();

    try {
      const { data } = await api.post("/api/ask", {
        question: query,
        employee_type: employeeType,
        issue_category: category,
        anonymous,
      });
      setMessages(prev => [...prev, { role: "assistant", ...data }]);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      setError(detail?.includes("No documents")
        ? "No policy documents loaded. A Policy Admin must upload PDF files first."
        : detail || "Request failed. Is the backend running on port 8000?"
      );
    } finally {
      setLoading(false);
    }
  };

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <Layout>
      <div style={{ maxWidth: 860, margin: "0 auto", display: "flex", flexDirection: "column", height: "calc(100vh - 4rem)" }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem", flexShrink: 0 }}>
          <div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: 2 }}>
              Policy Chat
            </h1>
            <p style={{ color: "var(--text-2)", fontSize: "0.82rem" }}>
              Ask any question about your company HR policies · Powered by local LLM
            </p>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {messages.length > 0 && (
              <button className="btn-ghost" onClick={() => setMessages([])} style={{ fontSize: "0.8rem" }}>
                🗑 Clear
              </button>
            )}
          </div>
        </div>

        {/* Context bar */}
        <div style={{
          display: "flex", gap: "0.75rem", alignItems: "center",
          padding: "0.75rem 1rem",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 12,
          marginBottom: "1rem",
          flexShrink: 0,
        }}>
          <select value={employeeType} onChange={e => setEmployeeType(e.target.value)} style={{ flex: 1, fontSize: "0.8rem" }}>
            {EMPLOYEE_TYPES.map(t => <option key={t} value={t}>{t || "👤 Any employee type"}</option>)}
          </select>
          <select value={category} onChange={e => setCategory(e.target.value)} style={{ flex: 1, fontSize: "0.8rem" }}>
            {CATEGORIES.map(c => <option key={c} value={c}>{c || "🏷 All categories"}</option>)}
          </select>

          {/* Anonymous toggle */}
          <div
            onClick={() => setAnonymous(v => !v)}
            style={{
              display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
              padding: "0.4rem 0.75rem",
              background: anonymous ? "rgba(99,102,241,0.12)" : "transparent",
              border: `1px solid ${anonymous ? "rgba(99,102,241,0.3)" : "var(--border)"}`,
              borderRadius: 8, transition: "all 0.15s", userSelect: "none",
              flexShrink: 0,
            }}
          >
            <div style={{
              width: 34, height: 18, borderRadius: 9,
              background: anonymous ? "var(--indigo)" : "var(--surface-high)",
              position: "relative", transition: "background 0.2s",
              boxShadow: anonymous ? "0 0 8px rgba(99,102,241,0.5)" : "none",
              flexShrink: 0,
            }}>
              <div style={{
                position: "absolute", top: 3, left: anonymous ? 17 : 3,
                width: 12, height: 12, borderRadius: "50%",
                background: "#fff", transition: "left 0.2s",
                boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
              }} />
            </div>
            <span style={{ fontSize: "0.78rem", fontWeight: anonymous ? 600 : 400, color: anonymous ? "#a5b4fc" : "var(--text-3)" }}>
              {anonymous ? "👤 Anonymous" : "Anonymous"}
            </span>
          </div>
        </div>

        {/* Message area */}
        <div style={{ flex: 1, overflowY: "auto", paddingRight: "0.25rem" }}>
          {messages.length === 0 && (
            <div style={{ paddingTop: "2rem" }}>
              {/* Empty state */}
              <div style={{ textAlign: "center", marginBottom: "2.5rem" }}>
                <div style={{
                  width: 72, height: 72, borderRadius: "50%", margin: "0 auto 1rem",
                  background: "linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.15))",
                  border: "1px solid rgba(99,102,241,0.2)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "2rem",
                }}>💬</div>
                <h3 style={{ fontWeight: 700, marginBottom: 6 }}>Start a policy conversation</h3>
                <p style={{ color: "var(--text-2)", fontSize: "0.875rem" }}>
                  Ask about leave, conduct, benefits, remote work, or any HR policy.
                </p>
              </div>

              {/* Quick questions */}
              <div>
                <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-3)", letterSpacing: "0.06em", marginBottom: "0.75rem", textAlign: "center" }}>
                  SUGGESTED QUESTIONS
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.6rem" }}>
                  {QUICK_QUESTIONS.map(q => (
                    <button
                      key={q}
                      className="btn-ghost"
                      onClick={() => send(q)}
                      style={{
                        textAlign: "left", padding: "0.75rem 1rem",
                        fontSize: "0.83rem", lineHeight: 1.4,
                        borderRadius: 12, height: "auto",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <span style={{ color: "var(--indigo)", marginRight: 6 }}>→</span>
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            msg.role === "user"
              ? <UserBubble key={i} msg={msg} />
              : <ResponseCard key={i} msg={msg} />
          ))}

          {loading && <TypingIndicator />}

          {error && (
            <div className="fade-in" style={{
              display: "flex", alignItems: "center", gap: 10,
              background: "rgba(239,68,68,0.07)",
              border: "1px solid rgba(239,68,68,0.2)",
              borderRadius: 12, padding: "0.85rem 1.1rem",
              fontSize: "0.85rem", color: "#f87171", marginBottom: "1rem",
            }}>
              <span style={{ fontSize: "1.1rem" }}>⚠️</span>
              <span>{error}</span>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        <div style={{
          flexShrink: 0,
          marginTop: "1rem",
          padding: "0.75rem",
          background: "var(--surface)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          display: "flex", gap: "0.6rem", alignItems: "flex-end",
        }}>
          <textarea
            ref={inputRef}
            rows={1}
            placeholder="Ask a policy question… (Enter to send, Shift+Enter for newline)"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={onKey}
            disabled={loading}
            style={{
              flex: 1, resize: "none", border: "none",
              background: "transparent", outline: "none",
              fontSize: "0.9rem", lineHeight: 1.6,
              maxHeight: 120, overflowY: "auto",
              padding: "0.35rem 0.5rem",
              boxShadow: "none",
            }}
          />
          <button
            className="btn-primary"
            onClick={() => send()}
            disabled={loading || !question.trim()}
            style={{ padding: "0.65rem 1.25rem", flexShrink: 0, borderRadius: 10, fontSize: "0.875rem" }}
          >
            {loading ? <span className="spinner" /> : <>Send ↑</>}
          </button>
        </div>

        <div style={{ textAlign: "center", fontSize: "0.68rem", color: "var(--text-3)", marginTop: "0.5rem" }}>
          🔒 Processed locally · No external API calls · qwen3.5:4b + nomic-embed-text
        </div>
      </div>
    </Layout>
  );
}
