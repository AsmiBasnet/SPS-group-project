import { Link, useNavigate, useLocation } from "react-router-dom";

const NAV = [
  { path: "/chat",      label: "💬 Policy Chat",     roles: ["Policy Admin","HR Manager","Employee"] },
  { path: "/dashboard", label: "📊 Dashboard",        roles: ["Policy Admin","HR Manager"] },
  { path: "/documents", label: "📁 Documents",        roles: ["Policy Admin"] },
];

export default function Layout({ children }) {
  const navigate  = useNavigate();
  const location  = useLocation();
  const user      = JSON.parse(localStorage.getItem("pg_user") || "{}");
  const role      = user.role || "";

  const logout = () => {
    localStorage.clear();
    navigate("/");
  };

  const roleColor = {
    "Policy Admin": "tag-purple",
    "HR Manager":   "tag-blue",
    "Employee":     "tag-green",
  }[role] || "tag-blue";

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* ── Sidebar ── */}
      <aside style={{
        width: 220,
        background: "var(--surface)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        padding: "1.25rem 0",
        flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{ padding: "0 1.25rem 1.5rem" }}>
          <div style={{
            fontSize: "1.25rem",
            fontWeight: 700,
            background: "linear-gradient(135deg, var(--accent), var(--accent2))",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}>
            🛡️ PolicyGuard
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", marginTop: 2 }}>
            HR Compliance AI
          </div>
        </div>

        {/* Nav links */}
        <nav style={{ flex: 1 }}>
          {NAV.filter(n => n.roles.includes(role)).map(({ path, label }) => {
            const active = location.pathname === path;
            return (
              <Link key={path} to={path} style={{
                display: "block",
                padding: "0.65rem 1.25rem",
                margin: "0.1rem 0.75rem",
                borderRadius: 8,
                fontSize: "0.875rem",
                fontWeight: active ? 600 : 400,
                color: active ? "var(--accent)" : "var(--text-muted)",
                background: active ? "rgba(79,110,247,0.12)" : "transparent",
                textDecoration: "none",
                transition: "all 0.15s",
              }}
              onMouseEnter={e => { if (!active) e.target.style.background = "var(--surface2)"; e.target.style.color = "var(--text)"; }}
              onMouseLeave={e => { if (!active) e.target.style.background = "transparent"; e.target.style.color = "var(--text-muted)"; }}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        {/* User info + logout */}
        <div style={{
          padding: "1rem 1.25rem",
          borderTop: "1px solid var(--border)",
          marginTop: "auto",
        }}>
          <div style={{ fontSize: "0.8rem", fontWeight: 600, marginBottom: 4 }}>
            {user.username || "—"}
          </div>
          <span className={`tag ${roleColor}`} style={{ marginBottom: "0.75rem", display: "inline-block" }}>
            {role}
          </span>
          <br />
          <button className="btn-ghost" style={{ width: "100%", marginTop: "0.5rem" }} onClick={logout}>
            Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main content ── */}
      <main style={{ flex: 1, overflow: "auto", padding: "2rem" }}>
        {children}
      </main>
    </div>
  );
}
