import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { ApiError, apiFetch, clearToken, getToken, setToken } from '../api/client';
import type { LoginResponse, User } from '../types';

interface AuthState {
  user: User | null;
  /** True while we are restoring a session from a stored token on first load. */
  initializing: boolean;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [initializing, setInitializing] = useState(true);

  // Restore the session on load so a refresh does not log the user out.
  useEffect(() => {
    let cancelled = false;

    async function restore() {
      if (!getToken()) {
        setInitializing(false);
        return;
      }
      try {
        const me = await apiFetch<User>('/auth/me');
        if (!cancelled) setUser(me);
      } catch {
        // Expired or invalid token - drop it rather than leaving a broken session.
        clearToken();
      } finally {
        if (!cancelled) setInitializing(false);
      }
    }

    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await apiFetch<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    setToken(result.access_token);
    setUser(result.user);
    return result.user;
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, initializing, login, logout }),
    [user, initializing, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside an AuthProvider');
  }
  return context;
}

export { ApiError };
