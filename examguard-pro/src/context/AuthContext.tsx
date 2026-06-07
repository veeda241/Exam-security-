import { createContext, useContext, useState, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { config } from '../config';

interface AuthContextType {
  isAuthenticated: boolean;
  user: { username: string } | null;
  login: (u: string, p: string) => Promise<boolean>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<{ username: string } | null>(null);
  const navigate = useNavigate();
  const isDevFallbackEnabled = import.meta.env.DEV || window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

  const login = async (u: string, p: string) => {
    try {
      // Create FormData-like body if backend expects password/username
      const response = await fetch(`${config.apiUrl}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: u, password: p })
      });
      
      if (response.ok) {
        const data = await response.json();
        localStorage.setItem('token', data.access_token);
        setUser({ username: u });
        setIsAuthenticated(true);
        navigate('/');
        return true;
      }

      if (response.status >= 500 && isDevFallbackEnabled) {
        console.warn('[Auth] Backend auth unavailable, using local dev session fallback');
        localStorage.removeItem('token');
        setUser({ username: u || 'Admin' });
        setIsAuthenticated(true);
        navigate('/');
        return true;
      }

      return false;
    } catch (error) {
       console.error("Login failed:", error);

       if (isDevFallbackEnabled) {
         console.warn('[Auth] Falling back to local dev session after login failure');
         localStorage.removeItem('token');
         setUser({ username: u || 'Admin' });
         setIsAuthenticated(true);
         navigate('/');
         return true;
       }

       return false;
    }
  };

  const logout = () => {
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
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
};
