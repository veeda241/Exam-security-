const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';

export const config = {
  // Use same-origin proxy paths unless an explicit override is provided.
  apiUrl: import.meta.env.VITE_API_URL || '/api',
  wsUrl: import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}/ws`,
};
