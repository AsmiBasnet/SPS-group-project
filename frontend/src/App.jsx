import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login      from "./pages/Login";
import Chat       from "./pages/Chat";
import Dashboard  from "./pages/Dashboard";
import Documents  from "./pages/Documents";

function RequireAuth({ children }) {
  const token = localStorage.getItem("pg_token");
  return token ? children : <Navigate to="/" replace />;
}

function RequireRole({ children, roles }) {
  const user = JSON.parse(localStorage.getItem("pg_user") || "{}");
  return roles.includes(user.role) ? children : <Navigate to="/chat" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        <Route path="/chat" element={
          <RequireAuth><Chat /></RequireAuth>
        } />
        <Route path="/dashboard" element={
          <RequireAuth>
            <RequireRole roles={["Policy Admin", "HR Manager"]}>
              <Dashboard />
            </RequireRole>
          </RequireAuth>
        } />
        <Route path="/documents" element={
          <RequireAuth>
            <RequireRole roles={["Policy Admin"]}>
              <Documents />
            </RequireRole>
          </RequireAuth>
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
