import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import {
  getStoredSession,
  isTokenExpired,
  maporaApi,
  refreshAccessToken,
  storeSession,
} from '../services/api';
import type { AuthSession } from '../types';

interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  sessionExpiredMessage: string | null;
  clearSessionExpiredMessage: () => void;
  signIn: (email: string, password: string) => Promise<AuthSession>;
  signOut: () => Promise<void>;
  refresh: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => {
    const stored = getStoredSession();
    if (!stored) return null;

    // If access token is expired and there is no refresh token, clear immediately
    if (isTokenExpired(stored.accessToken) && !stored.refreshToken) {
      storeSession(null);
      return null;
    }
    return stored;
  });

  const [sessionExpiredMessage, setSessionExpiredMessage] = useState<string | null>(null);

  const clearSessionExpiredMessage = useCallback(() => {
    setSessionExpiredMessage(null);
  }, []);

  const refresh = useCallback(async (): Promise<string | null> => {
    const token = await refreshAccessToken();
    if (!token) {
      setSession(null);
      setSessionExpiredMessage('Your session has expired. Please sign in again.');
      return null;
    }
    const updated = getStoredSession();
    setSession(updated);
    setSessionExpiredMessage(null);
    return token;
  }, []);

  // Listen to cross-cutting session events dispatched from api.ts
  useEffect(() => {
    // If mounted with an expired access token, proactively refresh using refresh token
    const initial = getStoredSession();
    if (initial?.accessToken && isTokenExpired(initial.accessToken) && initial.refreshToken) {
      void refreshAccessToken().then((token) => {
        if (!token) {
          setSession(null);
          setSessionExpiredMessage('Your session has expired. Please sign in again.');
        } else {
          setSession(getStoredSession());
          setSessionExpiredMessage(null);
        }
      });
    }

    const handleRefreshed = (event: Event) => {
      const customEvent = event as CustomEvent<AuthSession>;
      if (customEvent.detail) {
        setSession(customEvent.detail);
        setSessionExpiredMessage(null);
      }
    };

    const handleExpired = (event: Event) => {
      const customEvent = event as CustomEvent<{ message?: string }>;
      setSession(null);
      setSessionExpiredMessage(customEvent.detail?.message || 'Your session has expired. Please sign in again.');
    };

    window.addEventListener('mapora:session-refreshed', handleRefreshed);
    window.addEventListener('mapora:session-expired', handleExpired);

    return () => {
      window.removeEventListener('mapora:session-refreshed', handleRefreshed);
      window.removeEventListener('mapora:session-expired', handleExpired);
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: Boolean(session && !isTokenExpired(session.accessToken, -300)), // active within grace period
      sessionExpiredMessage,
      clearSessionExpiredMessage,
      async signIn(email, password) {
        const result = await maporaApi.login(email, password);
        if (!result.accessToken || !result.user?.id || !['admin', 'surveyor'].includes(result.user.role)) {
          throw new Error('The authentication service returned an incomplete or unsupported session.');
        }
        storeSession(result);
        setSession(result);
        setSessionExpiredMessage(null);
        return result;
      },
      async signOut() {
        const current = getStoredSession();
        storeSession(null);
        setSession(null);
        setSessionExpiredMessage(null);
        if (current?.refreshToken) {
          await maporaApi.logout(current.refreshToken, current.accessToken);
        }
      },
      refresh,
    }),
    [session, sessionExpiredMessage, clearSessionExpiredMessage, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used within AuthProvider.');
  return value;
}
