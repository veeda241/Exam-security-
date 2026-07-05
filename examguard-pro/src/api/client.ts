import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return null;

  try {
    const res = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    const tokens = res.data;
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
    return tokens.access_token;
  } catch {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token');
    return null;
  }
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && original && !original._retry) {
      original._retry = true;
      refreshPromise = refreshPromise ?? refreshAccessToken();
      const token = await refreshPromise;
      refreshPromise = null;
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return apiClient(original);
      }
    }
    return Promise.reject(error);
  }
);

export interface Exam {
  id: string;
  title: string;
  duration_minutes?: number;
  ruleset?: Record<string, unknown>;
}

export interface Session {
  id: string;
  exam_id: string;
  student_id?: string;
  status: string;
  risk_score: number;
  risk_level: string;
  started_at?: string;
}

export interface SessionEvent {
  id: string;
  session_id: string;
  type: string;
  payload: Record<string, unknown>;
  weight: number;
  created_at?: string;
}

export const examsApi = {
  list: () => apiClient.get<Exam[]>('/exams/'),
  get: (id: string) => apiClient.get<Exam>(`/exams/${id}`),
  create: (data: { title: string; duration_minutes?: number; ruleset?: Record<string, unknown> }) =>
    apiClient.post<Exam>('/exams/', data),
};

export const sessionsApi = {
  list: (params?: { exam_id?: string; status_filter?: string }) =>
    apiClient.get<Session[]>('/sessions/', { params }),
  get: (id: string) => apiClient.get<Session>(`/sessions/${id}`),
  start: (exam_id: string, consent_metadata?: Record<string, unknown>) =>
    apiClient.post<Session>('/sessions/', { exam_id, consent_metadata }),
  update: (id: string, data: { status?: string }) =>
    apiClient.patch<Session>(`/sessions/${id}`, data),
};

export const eventsApi = {
  list: (sessionId: string) => apiClient.get<SessionEvent[]>(`/events/session/${sessionId}`),
};

export const reportsApi = {
  get: (sessionId: string) => apiClient.get(`/reports/session/${sessionId}`),
  trigger: (sessionId: string) => apiClient.post(`/reports/session/${sessionId}`),
};

export const authApi = {
  login: (username: string, password: string) =>
    apiClient.post('/auth/login', { username, password }),
  me: () => apiClient.get('/auth/me'),
};
