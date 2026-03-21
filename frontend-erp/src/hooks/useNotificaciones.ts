import { useCallback, useEffect, useRef, useState } from 'react';
import { notificacionService, NotificacionOut } from '@/services/notificacionService';
import { useAuth } from '@/context/AuthContext';

const POLL_INTERVAL_MS = 30_000; // 30 segundos

export function useNotificaciones() {
  const { isAuthenticated } = useAuth();
  const [items, setItems] = useState<NotificacionOut[]>([]);
  const [noLeidas, setNoLeidas] = useState(0);
  const [loading, setLoading] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetch = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const data = await notificacionService.getNotificaciones({ limit: 20 });
      setItems(data.items);
      setNoLeidas(data.no_leidas);
    } catch {
      // Silencioso — no mostrar error de notificaciones en cada poll
    }
  }, [isAuthenticated]);

  // Fetch inicial + polling
  useEffect(() => {
    if (!isAuthenticated) return;
    fetch();
    intervalRef.current = setInterval(fetch, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isAuthenticated, fetch]);

  const marcarLeida = useCallback(async (id: string) => {
    await notificacionService.marcarLeida(id);
    setItems(prev => prev.map(n => n.id === id ? { ...n, leida: true } : n));
    setNoLeidas(prev => Math.max(0, prev - 1));
  }, []);

  const marcarTodasLeidas = useCallback(async () => {
    await notificacionService.marcarTodasLeidas();
    setItems(prev => prev.map(n => ({ ...n, leida: true })));
    setNoLeidas(0);
  }, []);

  return { items, noLeidas, loading, marcarLeida, marcarTodasLeidas, refresh: fetch };
}
