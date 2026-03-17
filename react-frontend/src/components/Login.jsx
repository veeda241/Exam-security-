import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { login, error } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitting(true);
    const success = await login(username, password);
    setSubmitting(false);
    if (success) {
      navigate('/');
    }
  }

  return (
    <div className="login-page">
      <div className="login-backdrop"></div>
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">
            <i className="fas fa-shield-alt"></i>
            <span>ExamGuard<strong>Pro</strong></span>
          </div>
          <h1>Proctor Portal</h1>
          <p>Oracle Red Bull Racing - Security Division</p>
        </div>

        {error && <div className="login-error"><i className="fas fa-exclamation-circle"></i> {error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label>Username</label>
            <div className="input-with-icon">
              <i className="fas fa-user"></i>
              <input 
                type="text" 
                value={username} 
                onChange={e => setUsername(e.target.value)} 
                placeholder="admin_id"
                required 
              />
            </div>
          </div>

          <div className="form-group">
            <label>Password</label>
            <div className="input-with-icon">
              <i className="fas fa-lock"></i>
              <input 
                type="password" 
                value={password} 
                onChange={e => setPassword(e.target.value)} 
                placeholder="••••••••"
                required 
              />
            </div>
          </div>

          <button type="submit" className="login-btn" disabled={submitting}>
            {submitting ? <i className="fas fa-spinner fa-spin"></i> : 'Authenticate'}
          </button>
        </form>

        <div className="login-footer">
          <span>&copy; 2026 Oracle Red Bull Racing</span>
          <span>Security Protocol v2.0.0</span>
        </div>
      </div>
    </div>
  );
}
