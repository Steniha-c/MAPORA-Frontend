import { Link, Navigate, useLocation } from 'react-router-dom';
import type { ReactNode } from 'react';
import { useAuth } from './AuthContext';
import type { UserRole } from '../types';

export function ProtectedRoute({ children, role }: { children: ReactNode; role?: UserRole }) {
  const { session } = useAuth();
  const location = useLocation();
  if (!session) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />;
  if (role && session.user.role !== role) return <div className="access-denied"><span className="section-kicker">ACCESS RESTRICTED</span><h1>Admin access required.</h1><p>Your current role does not include administrator access.</p><Link className="button button-quiet" to="/dashboard">Return to workspace</Link></div>;
  return <>{children}</>;
}
