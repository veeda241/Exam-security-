// API & WebSocket Configuration
const isProduction = window.location.protocol === 'https:';

export const API_BASE = 'http://localhost:8000/api';
export const WS_URL = `${isProduction ? 'wss' : 'ws'}://localhost:8000/ws/dashboard`;

export const CONFIG = {
  API_BASE,
  WS_URL,
  REFRESH_INTERVAL: 30000,
  MAX_RECONNECT_ATTEMPTS: 5,
  ACTIVITY_MAX_ITEMS: 50,
  TOAST_DURATION: 5000,
};
