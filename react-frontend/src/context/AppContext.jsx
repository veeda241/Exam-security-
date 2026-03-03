import { createContext, useContext, useReducer, useCallback, useEffect, useRef } from 'react';
import { fetchStudents, fetchSessions } from '../hooks/api';
import { useWebSocket } from '../hooks/useWebSocket';
import { CONFIG } from '../config';

const AppContext = createContext(null);

function getRiskStatus(score) {
  if (score > 60) return 'suspicious';
  if (score > 30) return 'review';
  return 'safe';
}

const initialState = {
  students: [],
  sessions: [],
  activities: [],
  alerts: [],
  isConnected: false,
  toasts: [],
};

function reducer(state, action) {
  switch (action.type) {
    case 'SET_STUDENTS':
      return { ...state, students: action.payload };
    case 'SET_SESSIONS':
      return { ...state, sessions: action.payload };
    case 'SET_CONNECTED':
      return { ...state, isConnected: action.payload };
    case 'ADD_ACTIVITY': {
      const activities = [
        { ...action.payload, timestamp: new Date() },
        ...state.activities,
      ].slice(0, CONFIG.ACTIVITY_MAX_ITEMS);
      return { ...state, activities };
    }
    case 'CLEAR_ACTIVITIES':
      return { ...state, activities: [] };
    case 'ADD_TOAST': {
      const toast = { ...action.payload, id: Date.now() + Math.random() };
      return { ...state, toasts: [...state.toasts, toast] };
    }
    case 'REMOVE_TOAST':
      return { ...state, toasts: state.toasts.filter(t => t.id !== action.payload) };
    case 'UPDATE_RISK': {
      const { student_id, risk_score } = action.payload;
      const students = state.students.map(s => {
        if (s.id === student_id || s.student_id === student_id) {
          return { ...s, risk_score, status: getRiskStatus(risk_score) };
        }
        return s;
      });
      return { ...state, students };
    }
    default:
      return state;
  }
}

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const refreshRef = useRef(null);

  const loadStudents = useCallback(async () => {
    try {
      const data = await fetchStudents();
      dispatch({ type: 'SET_STUDENTS', payload: data });
    } catch (err) {
      console.error('[API] Students error:', err);
      dispatch({
        type: 'ADD_TOAST',
        payload: { type: 'error', title: 'Connection Error', message: 'Failed to load student data' },
      });
    }
  }, []);

  const loadSessions = useCallback(async () => {
    try {
      const data = await fetchSessions();
      dispatch({ type: 'SET_SESSIONS', payload: data });
    } catch (err) {
      console.error('[API] Sessions error:', err);
    }
  }, []);

  const handleWsMessage = useCallback((data) => {
    if (data.type === '__connection') {
      dispatch({ type: 'SET_CONNECTED', payload: data.connected });
      return;
    }

    const eventType = data.event_type || data.type;

    switch (eventType) {
      case 'heartbeat':
      case 'pong':
        break;

      case 'risk_score_update': {
        const { student_id, data: evData } = data;
        dispatch({
          type: 'UPDATE_RISK',
          payload: { student_id, risk_score: evData.risk_score },
        });
        dispatch({
          type: 'ADD_ACTIVITY',
          payload: {
            type: evData.risk_score > 60 ? 'danger' : evData.risk_score > 30 ? 'warning' : 'info',
            icon: 'fa-chart-line',
            title: 'Risk Score Updated',
            description: `Student ${student_id}: ${Math.round(evData.risk_score)}%`,
          },
        });
        if (evData.risk_score > 60) {
          dispatch({
            type: 'ADD_TOAST',
            payload: {
              type: 'error',
              title: 'High Risk Detected',
              message: `Student ${student_id} risk score: ${Math.round(evData.risk_score)}%`,
            },
          });
        }
        break;
      }

      case 'student_joined':
      case 'student_left':
        dispatch({
          type: 'ADD_ACTIVITY',
          payload: {
            type: eventType === 'student_joined' ? 'success' : 'info',
            icon: eventType === 'student_joined' ? 'fa-user-plus' : 'fa-user-minus',
            title: eventType === 'student_joined' ? 'Student Joined' : 'Student Left',
            description: data.student_id || 'Unknown student',
          },
        });
        loadStudents();
        break;

      case 'alert_triggered':
      case 'face_missing':
      case 'multiple_faces':
      case 'plagiarism_detected':
      case 'unusual_behavior':
      case 'tab_switch':
      case 'copy_paste':
      case 'text_analysis':
      case 'forbidden_site': {
        const alertData = data.data || {};
        dispatch({
          type: 'ADD_ACTIVITY',
          payload: {
            type: 'danger',
            icon: getAlertIcon(eventType),
            title: formatEventType(eventType),
            description: alertData.message || `Student: ${data.student_id}`,
          },
        });
        dispatch({
          type: 'ADD_TOAST',
          payload: {
            type: 'warning',
            title: formatEventType(eventType),
            message: alertData.message || `Alert for student ${data.student_id}`,
          },
        });
        // Refresh data when suspicious events arrive
        if (['plagiarism_detected', 'forbidden_site', 'text_analysis'].includes(eventType)) {
          loadStudents();
          loadSessions();
        }
        break;
      }
      default:
        break;
    }
  }, [loadStudents]);

  useWebSocket(handleWsMessage);

  // Initial load & auto-refresh
  useEffect(() => {
    loadStudents();
    loadSessions();

    refreshRef.current = setInterval(() => {
      if (!state.isConnected) {
        loadStudents();
      }
    }, CONFIG.REFRESH_INTERVAL);

    return () => clearInterval(refreshRef.current);
  }, [loadStudents, loadSessions, state.isConnected]);

  const value = {
    state,
    dispatch,
    loadStudents,
    loadSessions,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp() {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be inside AppProvider');
  return ctx;
}

// Helpers
function getAlertIcon(eventType) {
  const icons = {
    face_missing: 'fa-user-slash',
    multiple_faces: 'fa-users',
    tab_switch: 'fa-window-restore',
    copy_paste: 'fa-clipboard',
    plagiarism_detected: 'fa-copy',
    unusual_behavior: 'fa-exclamation-triangle',
    text_analysis: 'fa-brain',
    forbidden_site: 'fa-ban',
  };
  return icons[eventType] || 'fa-bell';
}

function formatEventType(type) {
  return type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}
