import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import FundList from './pages/Fund/FundList';
import FundDetail from './pages/Fund/FundDetail';
import ProjectList from './pages/Project/ProjectList';
import ProjectDetail from './pages/Project/ProjectDetail';
import WorkflowList from './pages/Workflow/WorkflowList';

function App() {
  const isAuthenticated = !!localStorage.getItem('token');

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          isAuthenticated ? <Layout /> : <Navigate to="/login" replace />
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="funds" element={<FundList />} />
        <Route path="funds/:id" element={<FundDetail />} />
        <Route path="projects" element={<ProjectList />} />
        <Route path="projects/:id" element={<ProjectDetail />} />
        <Route path="workflows" element={<WorkflowList />} />
      </Route>
    </Routes>
  );
}

export default App;
