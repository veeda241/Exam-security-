import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useApp } from '../context/AppContext';
import { useAuth } from '../context/AuthContext';

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const { state } = useApp();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  const alertCount = state.activities.filter(a => a.type === 'danger' || a.type === 'warning').length;
  const sessionCount = state.sessions.length;

  const navItems = [
    { to: '/', icon: 'fa-chart-line', label: 'Dashboard' },
    { to: '/sessions', icon: 'fa-desktop', label: 'Active Sessions', badge: sessionCount },
    { to: '/students', icon: 'fa-users', label: 'Students' },
    { to: '/alerts', icon: 'fa-bell', label: 'Alerts', badge: alertCount, badgeDanger: true },
    { to: '/reports', icon: 'fa-file-alt', label: 'Reports' },
    { to: '/analytics', icon: 'fa-chart-pie', label: 'Analytics' },
  ];

  return (
    <aside className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="logo">
          <i className="fas fa-shield-alt"></i>
          {!collapsed && <span>ExamGuard<strong>Pro</strong></span>}
        </div>
        <button className="sidebar-toggle" onClick={() => setCollapsed(c => !c)}>
          <i className="fas fa-bars"></i>
        </button>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <i className={`fas ${item.icon}`}></i>
            {!collapsed && <span>{item.label}</span>}
            {!collapsed && item.badge > 0 && (
              <span className={`nav-badge ${item.badgeDanger ? 'danger' : ''}`}>
                {item.badge}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="user-info">
          <div className="user-avatar"><i className="fas fa-user"></i></div>
          {!collapsed && (
            <div className="user-details">
              <span className="user-name">{user?.full_name || user?.username || 'Proctor'}</span>
              <span className="user-role">{user?.role?.toUpperCase() || 'ADMINISTRATOR'}</span>
            </div>
          )}
        </div>
        <button className="btn-icon" title="Logout" onClick={handleLogout}><i className="fas fa-sign-out-alt"></i></button>
      </div>
    </aside>
  );
}
