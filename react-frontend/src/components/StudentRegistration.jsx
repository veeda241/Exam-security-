import React, { useState } from 'react';
import { API_BASE } from '../config';

const StudentRegistration = () => {
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    email: '',
    department: '',
    year: ''
  });
  
  const [status, setStatus] = useState({ type: '', message: '' });
  const [loading, setLoading] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus({ type: '', message: '' });

    try {
      // Call the create_student backend API endpoint
      const response = await fetch(`${API_BASE}/students/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed. Check if ID or Email is already used.');
      }

      setStatus({ 
        type: 'success', 
        message: `Success! You are registered. Please use ID: ${data.id} in the Chrome Extension.` 
      });
      setFormData({ id: '', name: '', email: '', department: '', year: '' });
      
    } catch (err) {
      setStatus({ type: 'error', message: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-primary)',
      padding: '2rem',
      fontFamily: "'Inter', -apple-system, sans-serif",
      overflowY: 'auto'
    }}>
      <div style={{
        background: 'var(--bg-secondary)',
        padding: '2.5rem',
        borderRadius: 'var(--radius-xl)',
        boxShadow: 'var(--shadow-lg)',
        width: '100%',
        maxWidth: '460px',
        border: '1px solid var(--border-color)',
        boxSizing: 'border-box',
        backdropFilter: 'var(--glass-blur)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '0.75rem', filter: 'drop-shadow(0 0 10px rgba(225,6,0,0.5))' }}>🛡️</div>
          <h1 style={{ color: 'white', marginBottom: '0.4rem', fontSize: '1.5rem', fontWeight: 800 }}>ExamGuard <span style={{ color: 'var(--accent-red)' }}>Pro</span></h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', margin: 0, textTransform: 'uppercase', letterSpacing: '0.1em' }}>Student Registration Portal</p>
        </div>

        {status.message && (
          <div style={{
            padding: '0.85rem 1rem',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '1.5rem',
            backgroundColor: status.type === 'success' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(225, 6, 0, 0.12)',
            color: status.type === 'success' ? '#34d399' : '#ff8e8e',
            border: `1px solid ${status.type === 'success' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(225, 6, 0, 0.25)'}`,
            fontSize: '0.875rem',
            lineHeight: '1.5'
          }}>
            {status.message}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem' }}>
          {[
            { label: 'Student ID', name: 'id', type: 'text', placeholder: 'e.g. CS1042', required: true },
            { label: 'Full Name', name: 'name', type: 'text', placeholder: 'Enter your full name', required: true },
            { label: 'Email Address', name: 'email', type: 'email', placeholder: 'your.email@university.edu' },
            { label: 'Department / Major', name: 'department', type: 'text', placeholder: 'e.g. Computer Science' },
          ].map(field => (
            <div key={field.name}>
              <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{field.label}</label>
              <input
                type={field.type}
                name={field.name}
                value={formData[field.name]}
                onChange={handleChange}
                placeholder={field.placeholder}
                required={field.required || false}
                style={{
                  width: '100%',
                  padding: '0.75rem 1rem',
                  borderRadius: 'var(--radius-md)',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-color)',
                  color: 'white',
                  fontSize: '0.9rem',
                  boxSizing: 'border-box',
                  outline: 'none',
                  transition: 'all 0.2s'
                }}
              />
            </div>
          ))}

          <div>
            <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Year of Study</label>
            <select
              name="year"
              value={formData.year}
              onChange={handleChange}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(0,0,0,0.3)',
                border: '1px solid var(--border-color)',
                color: 'white',
                fontSize: '0.9rem',
                boxSizing: 'border-box',
                outline: 'none'
              }}
            >
              <option value="">Select Year...</option>
              <option value="1st Year">1st Year</option>
              <option value="2nd Year">2nd Year</option>
              <option value="3rd Year">3rd Year</option>
              <option value="4th Year">4th Year</option>
              <option value="Graduate">Graduate</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              marginTop: '0.75rem',
              padding: '0.85rem',
              background: 'var(--gradient-primary)',
              color: 'white',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.95rem',
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              transition: 'all 0.2s',
              letterSpacing: '0.05em',
              textTransform: 'uppercase'
            }}
          >
            {loading ? <i className="fas fa-spinner fa-spin"></i> : '✅ Complete Registration'}
          </button>
        </form>

        <div style={{ marginTop: '2rem', textAlign: 'center', borderTop: '1px solid var(--border-color)', paddingTop: '1.25rem' }}>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', margin: 0, lineHeight: '1.6' }}>
            After registering, use your <strong style={{ color: 'white' }}>Student ID</strong> in the ExamGuard Chrome Extension to start your proctored session.
          </p>
        </div>
      </div>
    </div>
  );
};

export default StudentRegistration;

