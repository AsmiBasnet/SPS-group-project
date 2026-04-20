import { useState, useEffect, useRef } from "react";
import Layout from "../components/Layout";
import api from "../api";

/* ── Stat card ─────────────────────────────────── */
function StatCard({ icon, label, value, sub, gradient, glow }) {
  return (
    <div style={{
      background: `linear-gradient(135deg, ${gradient[0]}, ${gradient[1]})`,
      border: `1px solid ${glow}30`,
      borderRadius: 16,
      padding: "1.4rem 1.5rem",
      position: "relative",
      overflow: "hidden",
      boxShadow: `0 4px 20px ${glow}20`,
      transition: "transform 0.2s, box-shadow 0.2s",
      cursor: "default",
    }}
    onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = `0 8px 28px ${glow}35`; }}
    onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = `0 4px 20px ${glow}20`; }}
    >
      {/* Glow orb */}
      <div style={{
        position: "absolute", top: "-30%", right: "-10%",
        width: "80%", height: "140%",
        background: `radial-gradient(circle, ${glow}15 0%, transparent 65%)`,
        pointerEvents: "none",
      }} />
      <div style={{ position: "relative", zIndex: 1 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10, marginBottom: "0.75rem",
          background: `${glow}20`, border: `1px solid ${glow}30`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: "1.1rem",
        }}>{icon}</div>
        <div style={{ fontSize: "2rem", fontWeight: 800, letterSpacing: "-0.04em", lineHeight: 1 }}>
          {value}
        </div>
        <div style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.6)", marginTop: 5 }}>{label}</div>
        {sub && <div style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.4)", marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  );
}

/* ── Health gauge ──────────────────────────────── */
function HealthGauge({ score, grade, color, pillars }) {
  const ref = useRef(null);
  const COLORS = { green: "#10b981", orange: "#f59e0b", red: "#ef4444" };
  const c = COLORS[color] || "#6366f1";
  const r = 52, circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;

  const gradeDesc = {
    "A": "Excellent — policies are fresh, comprehensive, and consistent.",
    "B": "Good — minor gaps or staleness detected.",
    "C": "Fair — review outdated or missing policies.",
    "D": "Poor — significant policy gaps or conflicts.",
    "F": "Critical — policies need immediate attention.",
  }[grade] || "";

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: 16,
      padding: "1.75rem",
      display: "flex",
      gap: "2rem",
      alignItems: "center",
    }}>
      {/* SVG gauge */}
      <div style={{ position: "relative", flexShrink: 0 }}>
        <svg ref={ref} width={130} height={130} viewBox="0 0 130 130">
          {/* Outer glow ring */}
          <circle cx="65" cy="65" r={r + 10} fill="none" stroke={`${c}08`} strokeWidth={20} />
          {/* Track */}
          <circle cx="65" cy="65" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={8} />
          {/* Fill */}
          <circle
            cx="65" cy="65" r={r}
            fill="none"
            stroke={c}
            strokeWidth={8}
            strokeDasharray={`${dash} ${circ}`}
            strokeLinecap="round"
            transform="rotate(-90 65 65)"
            style={{ transition: "stroke-dasharray 1.2s cubic-bezier(0.16,1,0.3,1)", filter: `drop-shadow(0 0 6px ${c})` }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
          gap: 2,
        }}>
          <span style={{ fontSize: "2rem", fontWeight: 900, color: c, letterSpacing: "-0.05em", lineHeight: 1 }}>
            {score}
          </span>
          <span style={{ fontSize: "0.68rem", color: "var(--text-3)", letterSpacing: "0.04em" }}>/100</span>
        </div>
      </div>

      {/* Info */}
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: "0.7rem", fontWeight: 600, color: "var(--text-3)", letterSpacing: "0.08em", marginBottom: 4 }}>
          POLICY HEALTH SCORE
        </div>
        <div style={{ fontSize: "2.5rem", fontWeight: 900, color: c, letterSpacing: "-0.04em", lineHeight: 1, marginBottom: 6 }}>
          Grade {grade}
        </div>
        <p style={{ fontSize: "0.8rem", color: "var(--text-2)", marginBottom: "1rem", lineHeight: 1.5 }}>
          {gradeDesc}
        </p>
        {/* Pillars */}
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {pillars.map(({ label, score: s, color: cl }) => (
            <div key={label}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", marginBottom: 3 }}>
                <span style={{ color: "var(--text-2)" }}>{label}</span>
                <span style={{ color: cl, fontWeight: 600 }}>{s}</span>
              </div>
              <div className="progress-track">
                <div className="progress-fill" style={{
                  width: `${(s / 40) * 100}%`,
                  background: `linear-gradient(90deg, ${cl}80, ${cl})`,
                }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Decision donut ────────────────────────────── */
function DecisionChart({ decisions }) {
  const total = decisions.reduce((s, d) => s + d.count, 0) || 1;
  const COLS  = { ANSWER: "#10b981", CLARIFY: "#3b82f6", FLAG_CONFLICT: "#f59e0b", REFUSED: "#ef4444" };

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: 16, padding: "1.5rem",
    }}>
      <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-3)", letterSpacing: "0.08em", marginBottom: "1.25rem" }}>
        DECISION BREAKDOWN
      </div>
      {decisions.length === 0 ? (
        <div style={{ textAlign: "center", padding: "2rem 0", color: "var(--text-3)", fontSize: "0.85rem" }}>
          No queries yet — start chatting!
        </div>
      ) : decisions.map(({ decision, count }) => {
        const pct = Math.round((count / total) * 100);
        const col = COLS[decision] || "#6366f1";
        const labels = { ANSWER: "✅ Answered", CLARIFY: "💡 Needs Clarity", FLAG_CONFLICT: "⚠️ Conflict", REFUSED: "🚫 Declined" };
        return (
          <div key={decision} style={{ marginBottom: "1rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
              <span style={{ fontSize: "0.8rem", fontWeight: 500 }}>{labels[decision] || decision}</span>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-3)" }}>{count}</span>
                <span style={{
                  fontSize: "0.72rem", fontWeight: 700, color: col,
                  background: `${col}15`, padding: "0.1rem 0.5rem", borderRadius: 20,
                }}>{pct}%</span>
              </div>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{
                width: `${pct}%`,
                background: `linear-gradient(90deg, ${col}60, ${col})`,
                boxShadow: `0 0 8px ${col}40`,
              }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ── Recent queries table ──────────────────────── */
function RecentTable({ queries }) {
  const DCOL = { ANSWER: "tag-green", CLARIFY: "tag-blue", FLAG_CONFLICT: "tag-amber", REFUSED: "tag-red" };
  return (
    <div style={{ background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 16, overflow: "hidden" }}>
      <div style={{ padding: "1.25rem 1.5rem", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-3)", letterSpacing: "0.08em" }}>
          RECENT QUERIES
        </div>
        <span style={{ fontSize: "0.72rem", color: "var(--text-3)" }}>{queries.length} total</span>
      </div>
      {queries.length === 0 ? (
        <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-3)", fontSize: "0.85rem" }}>
          No queries yet
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="pg-table">
            <thead>
              <tr>
                <th>Question</th>
                <th>Category</th>
                <th>Decision</th>
                <th>Latency</th>
                <th>Anon</th>
              </tr>
            </thead>
            <tbody>
              {queries.slice(0,12).map((q, i) => (
                <tr key={i}>
                  <td style={{ maxWidth: 300 }}>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--text)", fontSize: "0.82rem" }}>
                      {q.question}
                    </div>
                  </td>
                  <td>
                    {q.issue_category
                      ? <span style={{ fontSize: "0.75rem", color: "var(--text-2)" }}>{q.issue_category}</span>
                      : <span style={{ color: "var(--text-3)", fontSize: "0.75rem" }}>—</span>
                    }
                  </td>
                  <td>
                    <span className={`tag ${DCOL[q.decision] || "tag-blue"}`}>{q.decision}</span>
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--text-2)", fontVariantNumeric: "tabular-nums" }}>
                    {q.latency ? `${Number(q.latency).toFixed(1)}s` : "—"}
                  </td>
                  <td>
                    {q.anonymous
                      ? <span className="tag tag-indigo" style={{ fontSize: "0.65rem" }}>Yes</span>
                      : <span style={{ color: "var(--text-3)", fontSize: "0.8rem" }}>—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ── Insights card ─────────────────────────────── */
function InsightCard({ title, items, icon, color }) {
  if (!items || items.length === 0) return null;
  return (
    <div style={{
      background: "var(--surface)",
      border: `1px solid ${color}25`,
      borderRadius: 16, padding: "1.25rem 1.5rem",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: "1rem" }}>
        <span style={{ fontSize: "1rem" }}>{icon}</span>
        <span style={{ fontSize: "0.72rem", fontWeight: 600, color, letterSpacing: "0.06em" }}>
          {title}
        </span>
      </div>
      <ul style={{ listStyle: "none", display: "flex", flexDirection: "column", gap: "0.6rem" }}>
        {items.map((item, i) => (
          <li key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, fontSize: "0.82rem", color: "var(--text-2)", lineHeight: 1.5 }}>
            <div style={{
              width: 5, height: 5, borderRadius: "50%",
              background: color, marginTop: 7, flexShrink: 0,
            }} />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Main Dashboard ────────────────────────────── */
export default function Dashboard() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const { data: d } = await api.get("/api/dashboard");
      setData(d);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const downloadReport = async () => {
    try {
      const res = await api.get("/api/report", { responseType: "blob" });
      const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
      Object.assign(document.createElement("a"), { href: url, download: "policyguard_audit.pdf" }).click();
    } catch { alert("Report generation failed. Try again."); }
  };

  if (loading) return (
    <Layout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh", gap: 16, color: "var(--text-2)" }}>
        <span className="spinner spinner-lg" />
        <div>
          <div style={{ fontWeight: 600 }}>Loading analytics…</div>
          <div style={{ fontSize: "0.78rem", color: "var(--text-3)", marginTop: 2 }}>Aggregating query data</div>
        </div>
      </div>
    </Layout>
  );

  if (error) return (
    <Layout>
      <div style={{ maxWidth: 500, margin: "4rem auto", textAlign: "center" }}>
        <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>⚠️</div>
        <h2 style={{ marginBottom: "0.5rem" }}>Dashboard unavailable</h2>
        <p style={{ color: "var(--text-2)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>{error}</p>
        <button className="btn-primary" onClick={load}>Try again</button>
      </div>
    </Layout>
  );

  const hs = data.health_score || {};
  const pillars = [
    { label: "Coverage",    score: hs.coverage_score    || 0, color: "#6366f1" },
    { label: "Freshness",   score: hs.freshness_score   || 0, color: "#22d3ee" },
    { label: "Consistency", score: hs.consistency_score || 0, color: "#10b981" },
  ];

  return (
    <Layout>
      <div style={{ maxWidth: 1050, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "2rem" }}>
          <div>
            <h1 style={{ fontSize: "1.6rem", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: 4 }}>
              Analytics Dashboard
            </h1>
            <p style={{ color: "var(--text-2)", fontSize: "0.82rem" }}>
              Real-time compliance intelligence and policy health monitoring
            </p>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn-ghost" onClick={load} style={{ fontSize: "0.8rem" }}>
              ↻ Refresh
            </button>
            <button className="btn-primary" onClick={downloadReport} style={{ fontSize: "0.8rem" }}>
              ⬇ Audit PDF
            </button>
          </div>
        </div>

        {/* KPI cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1.25rem" }}>
          <StatCard
            icon="📨" label="Total Queries" value={data.total_queries ?? 0}
            gradient={["rgba(99,102,241,0.12)", "rgba(139,92,246,0.06)"]}
            glow="#6366f1"
          />
          <StatCard
            icon="⚡" label="Avg Response" value={`${Number(data.avg_latency||0).toFixed(1)}s`}
            gradient={["rgba(34,211,238,0.1)", "rgba(6,182,212,0.05)"]}
            glow="#22d3ee"
          />
          <StatCard
            icon="🛡️" label="Guardrail Hits" value={data.guardrail_triggers ?? 0}
            gradient={["rgba(245,158,11,0.1)", "rgba(251,191,36,0.05)"]}
            glow="#f59e0b"
          />
          <StatCard
            icon="📄" label="Active Policies" value={data.document_count ?? 0}
            gradient={["rgba(16,185,129,0.1)", "rgba(52,211,153,0.05)"]}
            glow="#10b981"
          />
        </div>

        {/* Health + decisions row */}
        <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
          <HealthGauge
            score={hs.score || 0}
            grade={hs.grade || "—"}
            color={hs.color || "green"}
            pillars={pillars}
          />
          <DecisionChart decisions={data.decisions || []} />
        </div>

        {/* Insights row */}
        {(hs.insights?.length > 0 || hs.gaps?.length > 0) && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.25rem" }}>
            <InsightCard title="INSIGHTS" items={hs.insights} icon="💡" color="#6366f1" />
            <InsightCard title="POLICY GAPS" items={hs.gaps}    icon="🔴" color="#ef4444" />
          </div>
        )}

        {/* Recent queries */}
        <RecentTable queries={data.recent_queries || []} />
      </div>
    </Layout>
  );
}
