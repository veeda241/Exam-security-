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
      background: '#0a0e1a',
      padding: '2rem',
      fontFamily: "'Inter', -apple-system, sans-serif",
      overflowY: 'auto'
    }}>
      <div style={{
        background: '#141928',
        padding: '2.5rem',
        borderRadius: '16px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
        width: '100%',
        maxWidth: '460px',
        border: '1px solid rgba(255,255,255,0.08)',
        boxSizing: 'border-box'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '0.75rem' }}>🛡️</div>
          <h1 style={{ color: '#f1f5f9', marginBottom: '0.4rem', fontSize: '1.5rem', fontWeight: 700 }}>ExamGuard Pro</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem', margin: 0 }}>Student Registration Portal</p>
        </div>

        {status.message && (
          <div style={{
            padding: '0.85rem 1rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            backgroundColor: status.type === 'success' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
            color: status.type === 'success' ? '#34d399' : '#f87171',
            border: `1px solid ${status.type === 'success' ? 'rgba(16, 185, 129, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
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
              <label style={{ display: 'block', color: '#94a3b8', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 500 }}>{field.label}</label>
              <input
                type={field.type}
                name={field.name}
                value={formData[field.name]}
                onChange={handleChange}
                placeholder={field.placeholder}
                required={field.required || false}
                style={{
                  width: '100%',
                  padding: '0.7rem 0.9rem',
                  borderRadius: '8px',
                  background: '#0d1117',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: '#e2e8f0',
                  fontSize: '0.9rem',
                  boxSizing: 'border-box',
                  outline: 'none',
                  transition: 'border-color 0.2s'
                }}
              />
            </div>
          ))}

          <div>
            <label style={{ display: 'block', color: '#94a3b8', marginBottom: '0.4rem', fontSize: '0.8rem', fontWeight: 500 }}>Year of Study</label>
            <select
              name="year"
              value={formData.year}
              onChange={handleChange}
              style={{
                width: '100%',
                padding: '0.7rem 0.9rem',
                borderRadius: '8px',
                background: '#0d1117',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#e2e8f0',
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
              background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '0.95rem',
              fontWeight: 600,
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              transition: 'all 0.2s',
              letterSpacing: '0.02em'
            }}
          >
            {loading ? 'Registering...' : '✅ Complete Registration'}
          </button>
        </form>

        <div style={{ marginTop: '2rem', textAlign: 'center', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '1.25rem' }}>
          <p style={{ color: '#64748b', fontSize: '0.8rem', margin: 0, lineHeight: '1.6' }}>
            After registering, use your <strong style={{ color: '#94a3b8' }}>Student ID</strong> in the ExamGuard Chrome Extension to start your proctored session.
          </p>
        </div>
      </div>
    </div>
  );
};

export default StudentRegistration;

