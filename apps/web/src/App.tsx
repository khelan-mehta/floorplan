import { useEffect } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import { Login, Register } from './routes/Auth';
import { Dashboard } from './routes/Dashboard';
import { ProtectedRoute } from './routes/ProtectedRoute';
import { BoundaryRoute, CodesRoute, ProgramRoute, ProjectLayout } from './routes/ProjectPages';
import { DemoWorkspace, ProjectWorkspace } from './routes/Workspaces';
import { installShortcuts } from './shortcuts';
import { useAuth } from './store/auth';

export function App() {
  const loadMe = useAuth((s) => s.loadMe);

  useEffect(() => {
    installShortcuts();
    void loadMe();
  }, [loadMe]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/demo" element={<DemoWorkspace />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:id"
        element={
          <ProtectedRoute>
            <ProjectLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<ProjectWorkspace />} />
        <Route path="boundary" element={<BoundaryRoute />} />
        <Route path="program" element={<ProgramRoute />} />
        <Route path="codes" element={<CodesRoute />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
