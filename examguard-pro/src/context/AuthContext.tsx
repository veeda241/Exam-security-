import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { authApi } from '../api/client';

interface User {
  id?: string;
  username?: string;
  email?: string;
  role?: string;
  full_name?: string;
}

interface AuthContextType {
  isAuthenticated: boolean;
  user: User | null;
  login: (u: string, p: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const token = localStorage.getItem('access_token') || localStorage.getItem('token');
    if (!token) return;

    authApi
      .me()
      .then((res) => {
        setUser(res.data);
        setIsAuthenticated(true);
      })
      .catch(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('token');
      });
  }, []);

  const login = async (u: string, p: string) => {
    try {
      const response = await authApi.login(u, p);
      const data = response.data;
      const tokens = data.tokens || data;
      const accessToken = tokens.access_token || data.access_token;
      const refreshToken = tokens.refresh_token;

      if (accessToken) {
        localStorage.setItem('access_token', accessToken);
        localStorage.removeItem('token');
        if (refreshToken) localStorage.setItem('refresh_token', refreshToken);
        setUser(data.user || { username: u });
        setIsAuthenticated(true);
        navigate('/');
        return true;
      }
      return false;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
    navigate('/login');
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};
