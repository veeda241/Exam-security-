// API & WebSocket Configuration
const isProduction = import.meta.env.PROD;
const hostname = window.location.hostname;
const port = window.location.port;
const protocol = window.location.protocol;

// Backend API URL
// If VITE_API_URL env var is set (separate frontend deploy), use that
// Otherwise, assume API is on the same origin (single deploy)
const backendUrl = import.meta.env.VITE_API_URL || '';

export const API_BASE = isProduction
  ? (backendUrl ? `${backendUrl}/api` : `${protocol}//${hostname}${port ? ':' + port : ''}/api`)
  : 'http://localhost:8000/api';

const wsProtocol = protocol === 'https:' ? 'wss' : 'ws';
const wsHost = backendUrl
  ? backendUrl.replace(/^https?:\/\//, '')
  : `${hostname}${port ? ':' + port : ''}`;

export const WS_URL = isProduction
  ? `${wsProtocol}://${wsHost}/ws/dashboard`
  : `ws://localhost:8000/ws/dashboard`;

export const CONFIG = {
  API_BASE,
  WS_URL,
  REFRESH_INTERVAL: 30000,
  MAX_RECONNECT_ATTEMPTS: 5,
  ACTIVITY_MAX_ITEMS: 50,
  TOAST_DURATION: 5000,
};
