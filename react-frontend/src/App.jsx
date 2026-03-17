import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import ToastContainer from './components/ToastContainer';
import Dashboard from './components/Dashboard';
import Sessions from './components/Sessions';
import Students from './components/Students';
import Alerts from './components/Alerts';
import Reports from './components/Reports';
import Analytics from './components/Analytics';
import StudentRegistration from './components/StudentRegistration';
import Login from './components/Login';

import '@fortawesome/fontawesome-free/css/all.min.css';
import './index.css';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  
  if (loading) return (
    <div className="loading-screen">
      <i className="fas fa-spinner fa-spin"></i>
      <span>Securing Connection...</span>
    </div>
  );
  
  if (!user) return <Navigate to="/login" replace />;
  
  return children;
}

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AuthProvider>
        <AppProvider>
          <Routes>
            {/* Public Access */}
            <Route path="/login" element={<Login />} />
            <Route path="/student/register" element={<StudentRegistration />} />

            {/* Admin / Authenticated Routes */}
            <Route path="/*" element={
              <ProtectedRoute>
                <div className="app-container">
                  <Sidebar />
                  <main className="main-content">
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/sessions" element={<Sessions />} />
                      <Route path="/students" element={<Students />} />
                      <Route path="/alerts" element={<Alerts />} />
                      <Route path="/reports" element={<Reports />} />
                      <Route path="/analytics" element={<Analytics />} />
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </main>
                </div>
              </ProtectedRoute>
            } />
          </Routes>
          <ToastContainer />
        </AppProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
