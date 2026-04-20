import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "../components/Layout";
import api from "../api";

function StatCard({ icon, label, value, sub, color }) {
  return (
    <div className="card" style={{ position: "relative", overflow: "hidden" }}>
      <div style={{
        position: "absolute", top: 0, left: 0, bottom: 0, width: 4,
        background: color || "var(--accent)",
      }} />
      <div style={{ paddingLeft: 8 }}>
        <div style={{ fontSize: "1.5rem", marginBottom: 4 }}>{icon}</div>
        <div style={{ fontSize: "1.75rem", fontWeight: 800, lineHeight: 1 }}>{value}</div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", marginTop: 4 }}>{label}</div>
        {sub && <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: 2 }}>{sub}</div>}
      </div>
    </div>
  );
}

function HealthGauge({ score, grade, color }) {
  const colorMap = { green: "#22c55e", orange: "#f59e0b", red: "#ef4444" };
  const c = colorMap[color] || "#4f6ef7";
  const dash = (score / 100) * 251;

  return (
    <div className="card" style={{
      background: "linear-gradient(135deg, rgba(79,110,247,0.08), rgba(124,58,237,0.08))",
      border: "1px solid rgba(79,110,247,0.25)",
      display: "flex", alignItems: "center", gap: "2rem",
      gridColumn: "span 2",
    }}>
      <div style={{ position: "relative", width: 110, height: 110, flexShrink: 0 }}>
        <svg width="110" height="110" viewBox="0 0 110 110">
          <circle cx="55" cy="55" r="40" fill="none" stroke="var(--border)" strokeWidth="8" />
          <circle
            cx="55" cy="55" r="40" fill="none"
            stroke={c} strokeWidth="8"
            strokeDasharray={`${dash} 251`}
            strokeLinecap="round"
            transform="rotate(-90 55 55)"
            style={{ transition: "stroke-dasharray 1s ease" }}
          />
        </svg>
        <div style={{
          position: "absolute", inset: 0, display: "flex",
          flexDirection: "column", alignItems: "center", justifyContent: "center",
        }}>
          <span style={{ fontSize: "1.6rem", fontWeight: 800, color: c }}>{score}</span>
          <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>/ 100</span>
        </div>
      </div>
      <div>
        <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 4 }}>
          POLICY HEALTH SCORE
        </div>
        <div style={{ fontSize: "2rem", fontWeight: 800, color: c, marginBottom: 4 }}>
          Grade {grade}
        </div>
        <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
          Coverage · Freshness · Consistency
        </div>
      </div>
    </div>
  );
}

function DecisionChart({ decisions }) {
  const total = decisions.reduce((s, d) => s + d.count, 0) || 1;
  const colors = { ANSWER: "#22c55e", CLARIFY: "#3b82f6", FLAG_CONFLICT: "#f59e0b", REFUSED: "#ef4444" };

  return (
    <div className="card">
      <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "1rem" }}>
        Decision Breakdown
      </h3>
      {decisions.length === 0 ? (
        <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "1rem 0" }}>
          No queries yet
        </div>
      ) : (
        decisions.map(({ decision, count }) => {
          const pct = Math.round((count / total) * 100);
          const col = colors[decision] || "var(--accent)";
          return (
            <div key={decision} style={{ marginBottom: "0.75rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", marginBottom: 4 }}>
                <span>{decision}</span>
                <span style={{ color: "var(--text-muted)" }}>{count} ({pct}%)</span>
              </div>
              <div style={{ background: "var(--surface2)", borderRadius: 4, height: 6, overflow: "hidden" }}>
                <div style={{
                  width: `${pct}%`, height: "100%",
                  background: col, borderRadius: 4,
                  transition: "width 0.8s ease",
                }} />
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

function RecentQueries({ queries }) {
  const decColor = { ANSWER: "tag-green", CLARIFY: "tag-blue", FLAG_CONFLICT: "tag-amber", REFUSED: "tag-red" };

  return (
    <div className="card" style={{ gridColumn: "span 2" }}>
      <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "1rem" }}>
        Recent Queries
      </h3>
      {queries.length === 0 ? (
        <div style={{ color: "var(--text-muted)", fontSize: "0.85rem", textAlign: "center", padding: "1rem" }}>
          No queries logged yet
        </div>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.82rem" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border)" }}>
                {["Question", "Category", "Decision", "Latency", "Anon"].map(h => (
                  <th key={h} style={{
                    textAlign: "left", padding: "0.5rem 0.75rem",
                    color: "var(--text-muted)", fontWeight: 600, fontSize: "0.75rem",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {queries.slice(0, 10).map((q, i) => (
                <tr key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                  <td style={{ padding: "0.6rem 0.75rem", maxWidth: 280 }}>
                    <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {q.question}
                    </div>
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", color: "var(--text-muted)" }}>
                    {q.issue_category || "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    <span className={`tag ${decColor[q.decision] || "tag-blue"}`}>
                      {q.decision}
                    </span>
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem", color: "var(--text-muted)" }}>
                    {q.latency ? `${Number(q.latency).toFixed(1)}s` : "—"}
                  </td>
                  <td style={{ padding: "0.6rem 0.75rem" }}>
                    {q.anonymous ? <span className="tag tag-purple">Yes</span> : "—"}
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

export default function Dashboard() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");
  const navigate = useNavigate();

  const load = async () => {
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

  if (loading) return (
    <Layout>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 400, gap: 12, color: "var(--text-muted)" }}>
        <span className="spinner" /> Loading dashboard…
      </div>
    </Layout>
  );

  if (error) return (
    <Layout>
      <div style={{ maxWidth: 600, margin: "3rem auto", textAlign: "center" }}>
        <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>⚠️</div>
        <p style={{ color: "var(--red)" }}>{error}</p>
        <button className="btn-ghost" style={{ marginTop: "1rem" }} onClick={load}>Retry</button>
      </div>
    </Layout>
  );

  const hs = data.health_score || {};

  return (
    <Layout>
      <div style={{ maxWidth: 960, margin: "0 auto" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.5rem" }}>
          <div>
            <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>Analytics Dashboard</h1>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginTop: 2 }}>
              Policy compliance overview
            </p>
          </div>
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <button className="btn-ghost" onClick={load} style={{ fontSize: "0.8rem" }}>
              ↻ Refresh
            </button>
            <button
              className="btn-primary"
              style={{ fontSize: "0.8rem" }}
              onClick={async () => {
                try {
                  const res = await api.get("/api/report", { responseType: "blob" });
                  const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
                  const a = document.createElement("a");
                  a.href = url; a.download = "policyguard_audit.pdf"; a.click();
                } catch { alert("Report generation failed"); }
              }}
            >
              ⬇ Audit Report
            </button>
          </div>
        </div>

        {/* Top stats */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "1rem", marginBottom: "1rem" }}>
          <StatCard icon="📨" label="Total Queries"     value={data.total_queries}                 color="var(--accent)" />
          <StatCard icon="⚡" label="Avg Latency"       value={`${Number(data.avg_latency||0).toFixed(1)}s`} color="#a78bfa" />
          <StatCard icon="🛡️" label="Guardrail Triggers" value={data.guardrail_triggers}            color="var(--amber)" />
          <StatCard icon="📄" label="Active Documents"  value={data.document_count}                color="var(--green)" />
        </div>

        {/* Health score + decisions */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
          <HealthGauge score={hs.score || 0} grade={hs.grade || "—"} color={hs.color || "blue"} />
          <DecisionChart decisions={data.decisions || []} />
        </div>

        {/* Health insights */}
        {(hs.insights?.length > 0 || hs.gaps?.length > 0) && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1rem" }}>
            {hs.insights?.length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "0.75rem" }}>💡 Insights</h3>
                <ul style={{ paddingLeft: "1.1rem", fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.7 }}>
                  {hs.insights.map((ins, i) => <li key={i}>{ins}</li>)}
                </ul>
              </div>
            )}
            {hs.gaps?.length > 0 && (
              <div className="card">
                <h3 style={{ fontSize: "0.9rem", fontWeight: 700, marginBottom: "0.75rem" }}>🔴 Policy Gaps</h3>
                <ul style={{ paddingLeft: "1.1rem", fontSize: "0.82rem", color: "var(--text-muted)", lineHeight: 1.7 }}>
                  {hs.gaps.map((g, i) => <li key={i}>{g}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}

        {/* Recent queries */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "1rem" }}>
          <RecentQueries queries={data.recent_queries || []} />
        </div>
      </div>
    </Layout>
  );
}
