import { useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { CONFIG } from '../config';

export default function ToastContainer() {
  const { state, dispatch } = useApp();

  useEffect(() => {
    if (state.toasts.length === 0) return;
    const latest = state.toasts[state.toasts.length - 1];
    const timer = setTimeout(() => {
      dispatch({ type: 'REMOVE_TOAST', payload: latest.id });
    }, CONFIG.TOAST_DURATION);
    return () => clearTimeout(timer);
  }, [state.toasts, dispatch]);

  const icons = {
    info: 'fa-info-circle',
    success: 'fa-check-circle',
    warning: 'fa-exclamation-triangle',
    error: 'fa-times-circle',
  };

  return (
    <div className="toast-container">
      {state.toasts.map(toast => (
        <div key={toast.id} className={`toast ${toast.type}`}>
          <div className="toast-icon">
            <i className={`fas ${icons[toast.type] || 'fa-info-circle'}`}></i>
          </div>
          <div className="toast-content">
            <div className="toast-title">{toast.title}</div>
            <div className="toast-message">{toast.message}</div>
          </div>
          <button className="toast-close" onClick={() => dispatch({ type: 'REMOVE_TOAST', payload: toast.id })}>
            <i className="fas fa-times"></i>
          </button>
        </div>
      ))}
    </div>
  );
}
