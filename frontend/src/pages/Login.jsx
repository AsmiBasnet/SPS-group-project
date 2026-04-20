import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

const FEATURES = [
  { icon: "🔒", title: "100% Local AI",        desc: "Your data never leaves your server" },
  { icon: "⚡", title: "Instant Answers",       desc: "RAG pipeline with vector search" },
  { icon: "🛡️", title: "Policy Compliance",    desc: "Automated conflict detection" },
  { icon: "📊", title: "Real-time Analytics",  desc: "Query trends and health scoring" },
];

const DEMO_CREDS = [
  { label: "Policy Admin",  user: "policy_admin",  pass: "admin123",  color: "#818cf8" },
  { label: "HR Manager",    user: "hr_manager",    pass: "hr123",     color: "#22d3ee" },
  { label: "Employee",      user: "employee",      pass: "emp123",    color: "#10b981" },
];

export default function Login() {
  const [form, setForm]     = useState({ username: "", password: "" });
  const [error, setError]   = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const { data } = await api.post("/api/login", form);
      localStorage.setItem("pg_token", data.access_token);
      localStorage.setItem("pg_user", JSON.stringify({ username: data.username, role: data.role }));
      navigate("/chat");
    } catch (err) {
      setError(err.response?.data?.detail || "Invalid credentials. Try again.");
    } finally {
      setLoading(false);
    }
  };

  const fillCreds = (user, pass) => setForm({ username: user, password: pass });

  return (
    <div style={{ minHeight: "100vh", display: "flex" }}>

      {/* ── LEFT: Brand panel ────────────────────── */}
      <div style={{
        flex: "0 0 48%",
        background: "linear-gradient(145deg, #0a0d1a 0%, #0d1030 40%, #0a1020 100%)",
        borderRight: "1px solid rgba(255,255,255,0.06)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "4rem",
        position: "relative",
        overflow: "hidden",
      }}>
        {/* Decorative blobs */}
        <div style={{
          position: "absolute", top: "-10%", left: "-10%",
          width: "60%", height: "60%",
          background: "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />
        <div style={{
          position: "absolute", bottom: "-10%", right: "-10%",
          width: "50%", height: "50%",
          background: "radial-gradient(circle, rgba(139,92,246,0.1) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />
        {/* Grid overlay */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: "linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          pointerEvents: "none",
        }} />

        <div style={{ position: "relative", zIndex: 1 }}>
          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: "3rem" }}>
            <div style={{
              width: 48, height: 48,
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              borderRadius: 14,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "1.4rem",
              boxShadow: "0 8px 24px rgba(99,102,241,0.5)",
            }}>🛡️</div>
            <div>
              <div style={{
                fontSize: "1.4rem", fontWeight: 900, letterSpacing: "-0.04em",
                background: "linear-gradient(135deg, #818cf8, #c084fc)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              }}>PolicyGuard</div>
              <div style={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.3)", letterSpacing: "0.1em" }}>
                HR COMPLIANCE INTELLIGENCE
              </div>
            </div>
          </div>

          {/* Headline */}
          <h1 style={{
            fontSize: "2.6rem", fontWeight: 900,
            lineHeight: 1.1, letterSpacing: "-0.04em",
            marginBottom: "1.25rem",
          }}>
            AI-powered HR
            <br />
            <span style={{
              background: "linear-gradient(135deg, #818cf8 0%, #c084fc 50%, #22d3ee 100%)",
              WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            }}>
              compliance at
            </span>
            <br />
            <span style={{ color: "rgba(255,255,255,0.9)" }}>your fingertips.</span>
          </h1>
          <p style={{
            fontSize: "1rem", color: "rgba(255,255,255,0.45)",
            lineHeight: 1.7, marginBottom: "2.5rem", maxWidth: 360,
          }}>
            Query HR policies instantly with a local LLM — zero cloud exposure, full privacy, instant compliance answers.
          </p>

          {/* Feature list */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {FEATURES.map(({ icon, title, desc }) => (
              <div key={title} style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                <div style={{
                  width: 36, height: 36, flexShrink: 0,
                  background: "rgba(99,102,241,0.12)",
                  border: "1px solid rgba(99,102,241,0.2)",
                  borderRadius: 9,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontSize: "0.95rem",
                }}>
                  {icon}
                </div>
                <div>
                  <div style={{ fontSize: "0.875rem", fontWeight: 600, marginBottom: 1 }}>{title}</div>
                  <div style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.35)" }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── RIGHT: Login form ────────────────────── */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "3rem 3.5rem",
        background: "var(--bg)",
      }}>
        <div style={{ width: "100%", maxWidth: 400 }}>

          {/* Form header */}
          <div style={{ marginBottom: "2rem" }}>
            <h2 style={{ fontSize: "1.75rem", fontWeight: 800, letterSpacing: "-0.03em", marginBottom: "0.4rem" }}>
              Welcome back
            </h2>
            <p style={{ color: "var(--text-2)", fontSize: "0.9rem" }}>
              Sign in to access the policy compliance platform
            </p>
          </div>

          {/* Form */}
          <form onSubmit={submit} style={{ marginBottom: "1.5rem" }}>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{
                display: "block", fontSize: "0.78rem", fontWeight: 600,
                color: "var(--text-2)", marginBottom: 6, letterSpacing: "0.02em",
              }}>
                USERNAME
              </label>
              <input
                type="text"
                placeholder="Enter your username"
                value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })}
                required autoFocus
              />
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <label style={{
                display: "block", fontSize: "0.78rem", fontWeight: 600,
                color: "var(--text-2)", marginBottom: 6, letterSpacing: "0.02em",
              }}>
                PASSWORD
              </label>
              <input
                type="password"
                placeholder="••••••••"
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                required
              />
            </div>

            {error && (
              <div className="slide-up" style={{
                display: "flex", alignItems: "center", gap: 8,
                background: "rgba(239,68,68,0.08)",
                border: "1px solid rgba(239,68,68,0.25)",
                borderRadius: 9, padding: "0.7rem 1rem",
                fontSize: "0.82rem", color: "#f87171", marginBottom: "1.25rem",
              }}>
                <span>⚠️</span> {error}
              </div>
            )}

            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
              style={{ width: "100%", padding: "0.85rem", fontSize: "0.95rem", fontWeight: 600 }}
            >
              {loading
                ? <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
                    <span className="spinner" /> Authenticating…
                  </span>
                : "Sign In →"
              }
            </button>
          </form>

          {/* Demo credentials */}
          <div style={{
            border: "1px solid var(--border)",
            borderRadius: 14,
            overflow: "hidden",
          }}>
            <div style={{
              padding: "0.65rem 1rem",
              background: "var(--surface-up)",
              fontSize: "0.72rem", fontWeight: 600,
              color: "var(--text-3)", letterSpacing: "0.06em",
              borderBottom: "1px solid var(--border)",
            }}>
              DEMO CREDENTIALS — CLICK TO FILL
            </div>
            {DEMO_CREDS.map(({ label, user, pass, color }) => (
              <button
                key={label}
                type="button"
                onClick={() => fillCreds(user, pass)}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  width: "100%", padding: "0.7rem 1rem",
                  background: "transparent", borderRadius: 0,
                  borderBottom: "1px solid var(--border)", fontSize: "0.82rem",
                  color: "var(--text-2)", textAlign: "left",
                  transition: "background 0.1s",
                }}
                onMouseEnter={e => e.currentTarget.style.background = "var(--surface-up)"}
                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{
                    width: 8, height: 8, borderRadius: "50%",
                    background: color, flexShrink: 0,
                    boxShadow: `0 0 6px ${color}80`,
                  }} />
                  <span style={{ fontWeight: 600, color: "var(--text)" }}>{label}</span>
                </div>
                <div style={{ fontFamily: "monospace", fontSize: "0.78rem", color: "var(--text-3)" }}>
                  {user} / {pass}
                </div>
              </button>
            ))}
            <div style={{
              padding: "0.65rem 1rem",
              fontSize: "0.72rem", color: "var(--text-3)",
              display: "flex", alignItems: "center", gap: 5,
            }}>
              <span style={{ fontSize: "0.8rem" }}>🔒</span>
              Runs 100% locally — no external API calls
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
