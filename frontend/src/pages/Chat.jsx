import { useState, useRef, useEffect } from "react";
import Layout from "../components/Layout";
import api from "../api";

const EMPLOYEE_TYPES = [
  "", "Full-time", "Part-time", "Contract", "Intern", "Manager",
];
const CATEGORIES = [
  "", "Leave & Absence", "Harassment & Conduct", "Compensation & Benefits",
  "Performance", "Termination", "Remote Work", "Safety", "Other",
];

const DECISION_META = {
  ANSWER:        { label: "Answered",       color: "#22c55e", bg: "rgba(34,197,94,0.08)",  icon: "✅" },
  CLARIFY:       { label: "Needs Clarity",  color: "#3b82f6", bg: "rgba(59,130,246,0.08)", icon: "💡" },
  FLAG_CONFLICT: { label: "Policy Conflict",color: "#f59e0b", bg: "rgba(245,158,11,0.08)", icon: "⚠️" },
  REFUSED:       { label: "Declined",       color: "#ef4444", bg: "rgba(239,68,68,0.08)",  icon: "🚫" },
};

function ResponseCard({ msg }) {
  const meta = DECISION_META[msg.decision] || DECISION_META.CLARIFY;
  const [showReason, setShowReason] = useState(false);

  return (
    <div className="fade-in" style={{
      background: meta.bg,
      border: `1px solid ${meta.color}40`,
      borderRadius: 12,
      padding: "1rem 1.25rem",
      marginBottom: "0.75rem",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "0.75rem" }}>
        <span style={{ fontSize: "1.1rem" }}>{meta.icon}</span>
        <span className="tag" style={{
          background: `${meta.color}20`, color: meta.color,
          borderRadius: 20, padding: "0.2rem 0.6rem",
          fontSize: "0.7rem", fontWeight: 700,
        }}>
          {meta.label}
        </span>
        {msg.confidence && (
          <span style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginLeft: "auto" }}>
            Confidence: {msg.confidence}
          </span>
        )}
        {msg.latency > 0 && (
          <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
            {msg.latency?.toFixed(1)}s
          </span>
        )}
      </div>

      {/* Answer */}
      <p style={{ fontSize: "0.9rem", lineHeight: 1.7, whiteSpace: "pre-wrap" }}>
        {msg.answer}
      </p>

      {/* Clarification question */}
      {msg.clarification_question && (
        <div style={{
          marginTop: "0.75rem", padding: "0.6rem 0.9rem",
          background: "rgba(59,130,246,0.12)", borderRadius: 8,
          fontSize: "0.85rem", color: "#93c5fd",
        }}>
          ❓ {msg.clarification_question}
        </div>
      )}

      {/* Conflict clauses */}
      {msg.decision === "FLAG_CONFLICT" && msg.conflict_clause_a && (
        <div style={{ marginTop: "0.75rem", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {[["Clause A", msg.conflict_clause_a], ["Clause B", msg.conflict_clause_b]].map(([label, text]) => (
            <div key={label} style={{
              background: "rgba(245,158,11,0.08)", border: "1px solid rgba(245,158,11,0.25)",
              borderRadius: 8, padding: "0.6rem 0.8rem",
            }}>
              <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "var(--amber)", marginBottom: 3 }}>{label}</div>
              <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>{text}</div>
            </div>
          ))}
        </div>
      )}

      {/* Citation + Reasoning toggle */}
      {(msg.citation || msg.reasoning) && (
        <div style={{ marginTop: "0.75rem" }}>
          {msg.citation && msg.citation !== "N/A" && (
            <div style={{
              fontSize: "0.75rem", color: "var(--text-muted)",
              borderTop: "1px solid var(--border)", paddingTop: "0.5rem", marginBottom: "0.4rem",
            }}>
              📎 <em>{msg.citation}</em>
            </div>
          )}
          {msg.reasoning && (
            <button
              className="btn-ghost"
              style={{ padding: "0.3rem 0.75rem", fontSize: "0.75rem" }}
              onClick={() => setShowReason(v => !v)}
            >
              {showReason ? "Hide" : "Show"} Reasoning 🧠
            </button>
          )}
          {showReason && msg.reasoning && (
            <div style={{
              marginTop: "0.5rem", padding: "0.75rem",
              background: "var(--surface2)", borderRadius: 8,
              fontSize: "0.8rem", lineHeight: 1.6, color: "var(--text-muted)",
            }}>
              {msg.reasoning}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Chat() {
  const user = JSON.parse(localStorage.getItem("pg_user") || "{}");
  const [question, setQuestion]         = useState("");
  const [employeeType, setEmployeeType] = useState("");
  const [category, setCategory]         = useState("");
  const [anonymous, setAnonymous]       = useState(false);
  const [messages, setMessages]         = useState([]);
  const [loading, setLoading]           = useState(false);
  const [error, setError]               = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (e) => {
    e.preventDefault();
    if (!question.trim() || loading) return;

    const q = question.trim();
    setQuestion("");
    setError("");
    setMessages(prev => [...prev, { role: "user", text: q, anonymous }]);
    setLoading(true);

    try {
      const { data } = await api.post("/api/ask", {
        question: q,
        employee_type: employeeType,
        issue_category: category,
        anonymous,
      });
      setMessages(prev => [...prev, { role: "assistant", ...data }]);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      if (detail?.includes("No documents loaded")) {
        setError("No policy documents are loaded. Ask a Policy Admin to upload PDF files first.");
      } else {
        setError(detail || "Request failed. Is the backend running?");
      }
    } finally {
      setLoading(false);
    }
  };

  const clear = () => setMessages([]);

  return (
    <Layout>
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
          <div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>Policy Chat</h1>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 2 }}>
              Ask anything about your company HR policies
            </p>
          </div>
          {messages.length > 0 && (
            <button className="btn-ghost" onClick={clear} style={{ fontSize: "0.8rem" }}>
              Clear Chat
            </button>
          )}
        </div>

        {/* Filters */}
        <div className="card" style={{ marginBottom: "1.25rem" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "0.75rem", alignItems: "center" }}>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                Employee Type
              </label>
              <select value={employeeType} onChange={e => setEmployeeType(e.target.value)} style={{ width: "100%" }}>
                {EMPLOYEE_TYPES.map(t => <option key={t} value={t}>{t || "Any"}</option>)}
              </select>
            </div>
            <div>
              <label style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginBottom: 4 }}>
                Issue Category
              </label>
              <select value={category} onChange={e => setCategory(e.target.value)} style={{ width: "100%" }}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c || "All Categories"}</option>)}
              </select>
            </div>
            <div style={{ paddingTop: "1.25rem" }}>
              <label style={{
                display: "flex", alignItems: "center", gap: 8, cursor: "pointer",
                fontSize: "0.85rem", userSelect: "none",
              }}>
                <div
                  onClick={() => setAnonymous(v => !v)}
                  style={{
                    width: 40, height: 22, borderRadius: 11,
                    background: anonymous ? "var(--accent)" : "var(--border)",
                    position: "relative", transition: "background 0.2s", cursor: "pointer",
                  }}
                >
                  <div style={{
                    position: "absolute", top: 3, left: anonymous ? 21 : 3,
                    width: 16, height: 16, borderRadius: "50%",
                    background: "#fff", transition: "left 0.2s",
                  }} />
                </div>
                {anonymous ? <><span className="tag tag-purple">Anonymous</span></> : <span style={{ color: "var(--text-muted)" }}>Anonymous</span>}
              </label>
            </div>
          </div>
        </div>

        {/* Message list */}
        <div style={{ minHeight: 200, marginBottom: "1rem" }}>
          {messages.length === 0 && (
            <div style={{
              textAlign: "center", padding: "3rem 1rem",
              color: "var(--text-muted)", fontSize: "0.9rem",
            }}>
              <div style={{ fontSize: "2.5rem", marginBottom: "0.75rem" }}>💬</div>
              <div>Ask a question about HR policies, leave, benefits, or conduct.</div>
              <div style={{ fontSize: "0.8rem", marginTop: "0.5rem" }}>
                e.g. "Am I eligible for FMLA leave?" or "How do I report harassment?"
              </div>
            </div>
          )}

          {messages.map((msg, i) => {
            if (msg.role === "user") {
              return (
                <div key={i} style={{
                  display: "flex", justifyContent: "flex-end", marginBottom: "0.75rem",
                }}>
                  <div style={{
                    maxWidth: "75%",
                    background: "var(--surface2)",
                    borderLeft: "3px solid var(--accent)",
                    borderRadius: "0 12px 12px 12px",
                    padding: "0.75rem 1rem",
                    fontSize: "0.9rem",
                  }}>
                    {msg.anonymous && (
                      <span className="tag tag-purple" style={{ marginBottom: 6, display: "inline-block" }}>
                        👤 Anonymous
                      </span>
                    )}
                    <div>{msg.text}</div>
                  </div>
                </div>
              );
            }
            return <ResponseCard key={i} msg={msg} />;
          })}

          {loading && (
            <div className="fade-in" style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "1rem 1.25rem",
              background: "var(--surface2)", borderRadius: 12,
              fontSize: "0.85rem", color: "var(--text-muted)",
              marginBottom: "0.75rem",
            }}>
              <span className="spinner" />
              Analyzing policy documents… this may take up to 60s on CPU
            </div>
          )}

          {error && (
            <div className="fade-in" style={{
              background: "rgba(239,68,68,0.08)", border: "1px solid rgba(239,68,68,0.3)",
              borderRadius: 12, padding: "0.9rem 1.1rem",
              fontSize: "0.85rem", color: "var(--red)", marginBottom: "0.75rem",
            }}>
              ⚠️ {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <form onSubmit={send} style={{ display: "flex", gap: "0.75rem" }}>
          <input
            type="text"
            placeholder="Type your policy question…"
            value={question}
            onChange={e => setQuestion(e.target.value)}
            disabled={loading}
            style={{ flex: 1, padding: "0.75rem 1rem", fontSize: "0.9rem" }}
          />
          <button
            type="submit"
            className="btn-primary"
            disabled={loading || !question.trim()}
            style={{ padding: "0.75rem 1.5rem", flexShrink: 0 }}
          >
            {loading ? <span className="spinner" /> : "Send"}
          </button>
        </form>

        <div style={{ textAlign: "center", fontSize: "0.7rem", color: "var(--text-muted)", marginTop: "0.75rem" }}>
          🔒 All queries processed locally · Powered by {user.role === "Employee" ? "qwen3.5:4b" : "Ollama + qwen3.5:4b"}
        </div>
      </div>
    </Layout>
  );
}
