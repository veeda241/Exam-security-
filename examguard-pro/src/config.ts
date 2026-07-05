const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

export const config = {
  apiUrl: import.meta.env.VITE_API_URL || '/api/v1',
  wsUrl: import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}/api/v1/ws`,
};
