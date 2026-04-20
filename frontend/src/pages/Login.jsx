import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

const ROLE_INFO = [
  { role: "Policy Admin",  icon: "🔐", desc: "Upload & manage policy documents" },
  { role: "HR Manager",    icon: "📊", desc: "View analytics and audit reports" },
  { role: "Employee",      icon: "💬", desc: "Ask policy questions confidentially" },
];

export default function Login() {
  const [form, setForm]   = useState({ username: "", password: "" });
  const [error, setError] = useState("");
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
      setError(err.response?.data?.detail || "Login failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "radial-gradient(ellipse at 60% 20%, rgba(79,110,247,0.12) 0%, transparent 60%), var(--bg)",
      padding: "2rem",
    }}>
      <div style={{ width: "100%", maxWidth: 420 }}>
        {/* Hero */}
        <div style={{ textAlign: "center", marginBottom: "2.5rem" }}>
          <div style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>🛡️</div>
          <h1 style={{
            fontSize: "2rem", fontWeight: 800,
            background: "linear-gradient(135deg, var(--accent), var(--accent2))",
            WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
            marginBottom: "0.4rem",
          }}>
            PolicyGuard
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            HR Compliance Intelligence — Local AI, Zero Data Leaks
          </p>
        </div>

        {/* Login card */}
        <div className="card fade-in" style={{ marginBottom: "1.5rem" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: 700, marginBottom: "1.25rem" }}>
            Sign In
          </h2>
          <form onSubmit={submit}>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 4 }}>
                Username
              </label>
              <input
                type="text"
                placeholder="policy_admin / hr_manager / employee"
                value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })}
                style={{ width: "100%" }}
                required
                autoFocus
              />
            </div>
            <div style={{ marginBottom: "1.25rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", color: "var(--text-muted)", marginBottom: 4 }}>
                Password
              </label>
              <input
                type="password"
                placeholder="••••••••"
                value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                style={{ width: "100%" }}
                required
              />
            </div>

            {error && (
              <div style={{
                background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)",
                borderRadius: 8, padding: "0.6rem 0.9rem", fontSize: "0.8rem",
                color: "var(--red)", marginBottom: "1rem",
              }}>
                ⚠️ {error}
              </div>
            )}

            <button
              type="submit"
              className="btn-primary"
              disabled={loading}
              style={{ width: "100%", padding: "0.75rem", fontSize: "1rem" }}
            >
              {loading ? <><span className="spinner" style={{ marginRight: 8 }} /> Signing in…</> : "Sign In →"}
            </button>
          </form>
        </div>

        {/* Role cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.75rem" }}>
          {ROLE_INFO.map(({ role, icon, desc }) => (
            <div key={role} className="card" style={{ padding: "0.85rem", textAlign: "center" }}>
              <div style={{ fontSize: "1.5rem", marginBottom: "0.3rem" }}>{icon}</div>
              <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--accent)", marginBottom: 3 }}>
                {role}
              </div>
              <div style={{ fontSize: "0.65rem", color: "var(--text-muted)", lineHeight: 1.4 }}>
                {desc}
              </div>
            </div>
          ))}
        </div>

        <div style={{ textAlign: "center", marginTop: "1.5rem", fontSize: "0.72rem", color: "var(--text-muted)" }}>
          🔒 Fully local — no data sent to external servers
        </div>
      </div>
    </div>
  );
}
