import { useCallback, useEffect, useState } from 'react';
import { isApiConfigured, maporaApi } from '../services/api';
import { SAMPLE_PROJECTS, type MapProject } from '../types';
import { useAuth } from '../auth/AuthContext';

export function useProjects() {
  const { session } = useAuth();
  const [projects, setProjects] = useState<MapProject[]>(isApiConfigured ? [] : SAMPLE_PROJECTS);
  const [loading, setLoading] = useState(isApiConfigured);
  const [error, setError] = useState('');
  const refresh = useCallback(async () => {
    if (!isApiConfigured) { setProjects(SAMPLE_PROJECTS); setError(''); setLoading(false); return; }
    setLoading(true); setError('');
    try { setProjects(await maporaApi.listProjects(session?.accessToken)); }
    catch (cause) { setProjects([]); setError(cause instanceof Error ? cause.message : 'Projects could not be loaded.'); }
    finally { setLoading(false); }
  }, [session]);
  useEffect(() => { void refresh(); }, [refresh]);
  return { projects, loading, error, refresh, isDemo: !isApiConfigured, isApiConfigured };
}
