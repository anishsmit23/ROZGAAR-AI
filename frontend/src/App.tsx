import type { ReactNode } from "react";
import { Navigate, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { clearToken, getToken } from "./api/client";
import ApplicationsPage from "./pages/ApplicationsPage";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import TaskStatusPage from "./pages/TaskStatusPage";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  if (!getToken()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

function Layout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();

  const logout = () => {
    clearToken();
    navigate("/login");
  };

  return (
    <div className="min-h-screen bg-ink text-slate-100">
      <header className="border-b border-line bg-panel">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-signal">Rozgaar AI</p>
            <h1 className="text-xl font-semibold">Job Operations Console</h1>
          </div>
          <nav className="flex items-center gap-2 text-sm">
            <NavLink className={({ isActive }) => `btn ${isActive ? "border-signal" : ""}`} to="/">
              Dashboard
            </NavLink>
            <NavLink className={({ isActive }) => `btn ${isActive ? "border-signal" : ""}`} to="/applications">
              Applications
            </NavLink>
            <NavLink className={({ isActive }) => `btn ${isActive ? "border-signal" : ""}`} to="/tasks">
              Tasks
            </NavLink>
            <button className="btn" onClick={logout} type="button">
              Logout
            </button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-5 py-6">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout>
              <DashboardPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/applications"
        element={
          <ProtectedRoute>
            <Layout>
              <ApplicationsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/tasks"
        element={
          <ProtectedRoute>
            <Layout>
              <TaskStatusPage />
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
