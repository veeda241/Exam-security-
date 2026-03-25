import { config } from '../config';

export const useApi = () => {
  const fetchWithAuth = async (endpoint: string, options: RequestInit = {}) => {
    const response = await fetch(`${config.apiUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    if (!response.ok) throw new Error('API request failed');
    return response.json();
  };

  return { fetchWithAuth };
};
