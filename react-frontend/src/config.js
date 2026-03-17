// API & WebSocket Configuration
const isProduction = import.meta.env.PROD;
const hostname = window.location.hostname;
const port = window.location.port;
const protocol = window.location.protocol;

// In production, API is served from the same origin
// In dev, Vite proxy forwards /api and /ws to localhost:8000
export const API_BASE = isProduction
  ? `${protocol}//${hostname}${port ? ':' + port : ''}/api`
  : 'http://localhost:8000/api';

export const WS_URL = isProduction
  ? `${protocol === 'https:' ? 'wss' : 'ws'}://${hostname}${port ? ':' + port : ''}/ws/dashboard`
  : `ws://localhost:8000/ws/dashboard`;

export const CONFIG = {
  API_BASE,
  WS_URL,
  REFRESH_INTERVAL: 30000,
  MAX_RECONNECT_ATTEMPTS: 5,
  ACTIVITY_MAX_ITEMS: 50,
  TOAST_DURATION: 5000,
};
