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
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-dark)',
      padding: '2rem'
    }}>
      <div style={{
        background: 'var(--bg-surface)',
        padding: '3rem',
        borderRadius: '16px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.5)',
        width: '100%',
        maxWidth: '500px',
        border: '1px solid var(--border-light)'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🛡️</div>
          <h1 style={{ color: 'var(--text-light)', marginBottom: '0.5rem' }}>ExamGuard Pro</h1>
          <p style={{ color: 'var(--text-muted)' }}>Student Registration Portal</p>
        </div>

        {status.message && (
          <div style={{
            padding: '1rem',
            borderRadius: '8px',
            marginBottom: '1.5rem',
            backgroundColor: status.type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            color: status.type === 'success' ? '#10b981' : '#ef4444',
            border: `1px solid ${status.type === 'success' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)'}`
          }}>
            {status.message}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Student ID</label>
            <input 
              type="text" 
              name="id"
              value={formData.id}
              onChange={handleChange}
              placeholder="e.g. CS1042" 
              required
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                background: 'var(--bg-dark)',
                border: '1px solid var(--border-light)',
                color: 'var(--text-light)'
              }}
            />
          </div>
          
          <div>
            <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Full Name</label>
            <input 
              type="text" 
              name="name"
              value={formData.name}
              onChange={handleChange}
              placeholder="Enter your full name" 
              required
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                background: 'var(--bg-dark)',
                border: '1px solid var(--border-light)',
                color: 'var(--text-light)'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Email Address</label>
            <input 
              type="email" 
              name="email"
              value={formData.email}
              onChange={handleChange}
              placeholder="your.email@university.edu" 
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                background: 'var(--bg-dark)',
                border: '1px solid var(--border-light)',
                color: 'var(--text-light)'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Department / Major</label>
            <input 
              type="text" 
              name="department"
              value={formData.department}
              onChange={handleChange}
              placeholder="e.g. Computer Science" 
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                background: 'var(--bg-dark)',
                border: '1px solid var(--border-light)',
                color: 'var(--text-light)'
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', color: 'var(--text-muted)', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Year of Study</label>
            <select 
              name="year"
              value={formData.year}
              onChange={handleChange}
              style={{
                width: '100%',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                background: 'var(--bg-dark)',
                border: '1px solid var(--border-light)',
                color: 'var(--text-light)',
                appearance: 'none'
              }}
            >
              <option value="">Select Year...</option>
              <option value="Freshman">Freshman</option>
              <option value="Sophomore">Sophomore</option>
              <option value="Junior">Junior</option>
              <option value="Senior">Senior</option>
              <option value="Graduate">Graduate</option>
              <option value="Other">Other</option>
            </select>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            style={{
              marginTop: '1rem',
              padding: '1rem',
              background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
              transition: 'all 0.2s'
            }}
          >
            {loading ? 'Registering...' : 'Complete Registration'}
          </button>
        </form>

        <div style={{ marginTop: '2.5rem', textAlign: 'center', borderTop: '1px solid var(--border-light)', paddingTop: '1.5rem' }}>
          <h3 style={{ color: 'var(--text-light)', fontSize: '1rem', marginBottom: '1rem' }}>Next Steps:</h3>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem', lineHeight: '1.5' }}>
            After registering, install the ExamGuard Pro Chrome Extension and enter your Student ID to begin your proctored session.
          </p>
          <a href="#" style={{ 
            color: '#3b82f6', 
            textDecoration: 'none', 
            fontWeight: '500', 
            display: 'inline-flex', 
            alignItems: 'center', 
            gap: '0.5rem' 
          }}>
            <i className="fa-brands fa-chrome"></i> Download Extension
          </a>
        </div>
      </div>
    </div>
  );
};

export default StudentRegistration;
