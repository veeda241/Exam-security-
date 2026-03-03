import { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';

export default function Header({ title }) {
  const { state } = useApp();
  const [time, setTime] = useState(new Date().toLocaleTimeString());
  const [theme, setTheme] = useState(localStorage.getItem('examguard-theme') || 'dark');

  useEffect(() => {
    const timer = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('examguard-theme', theme);
  }, [theme]);

  const alertCount = state.activities.filter(a => a.type === 'danger' || a.type === 'warning').length;

  return (
    <header className="top-header">
      <div className="header-left">
        <div className="breadcrumb">
          <span>Dashboard</span>
          <i className="fas fa-chevron-right"></i>
          <span className="current">{title}</span>
        </div>
      </div>

      <div className="header-center">
        <div className="search-box">
          <i className="fas fa-search"></i>
          <input type="text" placeholder="Search students, sessions..." />
          <kbd>Ctrl+K</kbd>
        </div>
      </div>

      <div className="header-right">
        <div className={`connection-status ${state.isConnected ? 'connected' : 'disconnected'}`}>
          <span className="status-dot"></span>
          <span className="status-text">{state.isConnected ? 'Live' : 'Offline'}</span>
        </div>
        <span className="current-time">{time}</span>
        <button className="btn-icon notification-btn">
          <i className="fas fa-bell"></i>
          <span className="notification-badge">{alertCount}</span>
        </button>
        <button
          className="btn-icon theme-toggle"
          title="Toggle Theme"
          onClick={() => setTheme(t => t === 'dark' ? 'light' : 'dark')}
        >
          <i className={`fas fa-${theme === 'dark' ? 'moon' : 'sun'}`}></i>
        </button>
      </div>
    </header>
  );
}
