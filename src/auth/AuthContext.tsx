import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { maporaApi } from '../services/api';
import type { AuthSession } from '../types';

interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  signIn: (email: string, password: string) => Promise<AuthSession>;
  signOut: () => void;
}

const STORAGE_KEY = 'mapora_auth_session';

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (!saved) return null;
      const parsed = JSON.parse(saved) as AuthSession;
      if (parsed?.accessToken && parsed?.user?.id) {
        return parsed;
      }
      return null;
    } catch {
      return null;
    }
  });

  const value = useMemo<AuthContextValue>(() => ({
    session,
    isAuthenticated: Boolean(session),
    async signIn(email, password) {
      const result = await maporaApi.login(email, password);
      if (!result.accessToken || !result.user?.id || !['admin', 'surveyor'].includes(result.user.role)) {
        throw new Error('The authentication service returned an incomplete or unsupported session.');
      }
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(result));
      } catch { /* Ignore storage errors */ }
      setSession(result);
      return result;
    },
    signOut() {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch { /* Ignore storage errors */ }
      setSession(null);
    },
  }), [session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used within AuthProvider.');
  return value;
}
