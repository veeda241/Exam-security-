import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import Sidebar from './components/Sidebar';
import ToastContainer from './components/ToastContainer';
import Dashboard from './components/Dashboard';
import Sessions from './components/Sessions';
import Students from './components/Students';
import Alerts from './components/Alerts';
import Reports from './components/Reports';
import Analytics from './components/Analytics';

import '@fortawesome/fontawesome-free/css/all.min.css';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Sidebar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/students" element={<Students />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/analytics" element={<Analytics />} />
          </Routes>
        </main>
        <ToastContainer />
      </AppProvider>
    </BrowserRouter>
  );
}

export default App;
