import { Link, useNavigate, useLocation } from "react-router-dom";

const NAV = [
  { path: "/chat",      icon: "💬", label: "Policy Chat",    roles: ["Policy Admin","HR Manager","Employee"] },
  { path: "/dashboard", icon: "📊", label: "Analytics",      roles: ["Policy Admin","HR Manager"] },
  { path: "/documents", icon: "📁", label: "Documents",      roles: ["Policy Admin"] },
];

const ROLE_COLORS = {
  "Policy Admin": { tag: "tag-indigo", dot: "#818cf8" },
  "HR Manager":   { tag: "tag-cyan",   dot: "#22d3ee" },
  "Employee":     { tag: "tag-green",  dot: "#10b981" },
};

function Avatar({ name }) {
  const initials = (name || "?").slice(0,2).toUpperCase();
  return (
    <div style={{
      width: 34, height: 34,
      borderRadius: "50%",
      background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: "0.78rem", fontWeight: 700, color: "#fff",
      flexShrink: 0,
      boxShadow: "0 2px 8px rgba(99,102,241,0.4)",
    }}>
      {initials}
    </div>
  );
}

export default function Layout({ children }) {
  const navigate  = useNavigate();
  const location  = useLocation();
  const user      = JSON.parse(localStorage.getItem("pg_user") || "{}");
  const role      = user.role || "";
  const rc        = ROLE_COLORS[role] || { tag: "tag-blue", dot: "#3b82f6" };

  const logout = () => { localStorage.clear(); navigate("/"); };

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>

      {/* ── Sidebar ─────────────────────────────── */}
      <aside style={{
        width: 236,
        background: "rgba(8,12,23,0.95)",
        borderRight: "1px solid rgba(255,255,255,0.06)",
        display: "flex",
        flexDirection: "column",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        flexShrink: 0,
        position: "sticky",
        top: 0,
        height: "100vh",
        overflowY: "auto",
      }}>
        {/* Logo */}
        <div style={{ padding: "1.5rem 1.25rem 1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 36, height: 36,
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              borderRadius: 10,
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "1rem",
              boxShadow: "0 4px 12px rgba(99,102,241,0.4)",
            }}>
              🛡️
            </div>
            <div>
              <div style={{
                fontSize: "1rem", fontWeight: 800, letterSpacing: "-0.03em",
                background: "linear-gradient(135deg, #818cf8 0%, #c084fc 100%)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              }}>
                PolicyGuard
              </div>
              <div style={{ fontSize: "0.62rem", color: "var(--text-3)", marginTop: -1, letterSpacing: "0.04em" }}>
                HR COMPLIANCE AI
              </div>
            </div>
          </div>

          {/* Live status */}
          <div style={{
            marginTop: "1rem",
            display: "flex", alignItems: "center", gap: 7,
            padding: "0.45rem 0.75rem",
            background: "rgba(16,185,129,0.06)",
            border: "1px solid rgba(16,185,129,0.15)",
            borderRadius: 8,
            fontSize: "0.72rem",
            color: "var(--text-2)",
          }}>
            <span className="dot-live" />
            Local AI — Privacy Safe
          </div>
        </div>

        {/* Divider */}
        <div style={{ height: "1px", background: "rgba(255,255,255,0.05)", margin: "0 1.25rem" }} />

        {/* Nav */}
        <nav style={{ flex: 1, padding: "0.75rem 0.75rem" }}>
          <div style={{ fontSize: "0.65rem", color: "var(--text-3)", letterSpacing: "0.08em", fontWeight: 600, padding: "0 0.5rem", marginBottom: "0.4rem" }}>
            NAVIGATION
          </div>
          {NAV.filter(n => n.roles.includes(role)).map(({ path, icon, label }) => {
            const active = location.pathname === path;
            return (
              <Link key={path} to={path} style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                padding: "0.6rem 0.75rem",
                margin: "0.15rem 0",
                borderRadius: 9,
                fontSize: "0.875rem",
                fontWeight: active ? 600 : 400,
                color: active ? "#fff" : "var(--text-2)",
                background: active
                  ? "linear-gradient(135deg, rgba(99,102,241,0.25), rgba(139,92,246,0.15))"
                  : "transparent",
                border: active ? "1px solid rgba(99,102,241,0.2)" : "1px solid transparent",
                textDecoration: "none",
                transition: "all 0.15s",
                boxShadow: active ? "0 2px 8px rgba(99,102,241,0.15)" : "none",
                position: "relative",
              }}
              onMouseEnter={e => {
                if (!active) {
                  e.currentTarget.style.background = "rgba(255,255,255,0.04)";
                  e.currentTarget.style.color = "var(--text)";
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--text-2)";
                }
              }}
              >
                {/* Active indicator bar */}
                {active && (
                  <div style={{
                    position: "absolute", left: 0, top: "20%", bottom: "20%",
                    width: 3, background: "linear-gradient(180deg, #6366f1, #8b5cf6)",
                    borderRadius: "0 3px 3px 0",
                  }} />
                )}
                <span style={{ fontSize: "1rem", opacity: active ? 1 : 0.7 }}>{icon}</span>
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Bottom: Model info */}
        <div style={{
          margin: "0.75rem",
          padding: "0.75rem",
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.05)",
          borderRadius: 10,
          fontSize: "0.72rem",
          color: "var(--text-3)",
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
            <span>Model</span>
            <span style={{ color: "#a5b4fc" }}>qwen3.5:4b</span>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span>Embeddings</span>
            <span style={{ color: "#67e8f9" }}>nomic-embed</span>
          </div>
        </div>

        {/* User profile */}
        <div style={{
          padding: "0.75rem 1rem",
          borderTop: "1px solid rgba(255,255,255,0.05)",
          display: "flex", alignItems: "center", gap: 10,
        }}>
          <Avatar name={user.username} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "0.82rem", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {user.username}
            </div>
            <span className={`tag ${rc.tag}`} style={{ marginTop: 2 }}>
              {role}
            </span>
          </div>
          <button
            onClick={logout}
            className="btn-icon"
            data-tip="Sign out"
            style={{ flexShrink: 0 }}
          >
            →
          </button>
        </div>
      </aside>

      {/* ── Main ─────────────────────────────────── */}
      <main style={{
        flex: 1,
        overflow: "auto",
        padding: "2rem 2.5rem",
        minHeight: "100vh",
      }}>
        {children}
      </main>
    </div>
  );
}
