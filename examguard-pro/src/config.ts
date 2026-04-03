// Detect dev mode (running on Vite dev server)
const isDevMode = window.location.port === '3000' || window.location.port === '5173';
const backendHost = isDevMode ? 'localhost:8000' : window.location.host;
const httpProtocol = window.location.protocol === 'https:' ? 'https:' : 'http:';
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

export const config = {
  // In dev mode, use full backend URL; in production, use relative path
  apiUrl: import.meta.env.VITE_API_URL || (isDevMode ? `${httpProtocol}//${backendHost}/api` : '/api'),
  wsUrl: import.meta.env.VITE_WS_URL || `${wsProtocol}//${backendHost}/ws`,
};
