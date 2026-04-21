// src/lib/axios.ts
import axios from 'axios';
import { message } from 'antd';
import { normalizeHttpError } from '@/utils/httpError';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

// ─── Cola para peticiones que llegan mientras se está renovando el token ──────
// Evita que múltiples 401 simultáneos lancen N llamadas de refresh en paralelo.
// Solo la primera petición hace el refresh; las demás esperan en esta cola.
let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: any) => void }> = [];

const processQueue = (error: any, token: string | null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token!);
  });
  failedQueue = [];
};

const clearSessionAndRedirect = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('refresh_token');
  if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
    window.location.href = '/login';
  }
};

// ─── Interceptor de request: adjunta el token vigente ────────────────────────
api.interceptors.request.use(
  (config) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ─── Interceptor de response: muestra errores genéricos ──────────────────────
// Los 401 se manejan silenciosamente en el siguiente interceptor.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const isEmailConfigNotFound = status === 404 && error?.config?.url?.includes('/email-config');
    const isValidationError = status === 422;
    const isAuthError = status === 401 || status === 403;

    if (!isEmailConfigNotFound && !isValidationError && !isAuthError) {
      message.error(normalizeHttpError(error));
    }
    return Promise.reject(error);
  },
);

// ─── Interceptor de response: renovación automática del access token ──────────
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const isRefreshEndpoint = originalRequest?.url?.includes('/login/refresh-token');

    // Solo actuar ante 401/403 en peticiones que aún no se han reintentado
    if ((status === 401 || status === 403) && !originalRequest._retry && !isRefreshEndpoint) {
      const refreshToken = typeof window !== 'undefined'
        ? localStorage.getItem('refresh_token')
        : null;

      // Sin refresh token → sesión inválida, ir a login
      if (!refreshToken) {
        clearSessionAndRedirect();
        return Promise.reject(error);
      }

      // Si YA hay un refresh en curso, encolar esta petición y esperar
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((newToken) => {
            originalRequest._retry = true;
            originalRequest.headers = {
              ...originalRequest.headers,
              Authorization: `Bearer ${newToken}`,
            };
            return api(originalRequest);
          })
          .catch((err) => Promise.reject(err));
      }

      // Primera petición en fallar — iniciar refresh
      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Usamos axios directo para evitar que este request también pase
        // por nuestro interceptor y genere un bucle infinito.
        const { authService } = await import('@/services/authService');
        const tokens = await authService.refreshToken(refreshToken);

        localStorage.setItem('token', tokens.access_token);
        localStorage.setItem('refresh_token', tokens.refresh_token);

        // Desencolar todas las peticiones en espera con el nuevo token
        processQueue(null, tokens.access_token);

        // Reintentar la petición original
        originalRequest.headers = {
          ...originalRequest.headers,
          Authorization: `Bearer ${tokens.access_token}`,
        };
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh falló (token expirado o inválido) → cerrar sesión
        processQueue(refreshError, null);
        clearSessionAndRedirect();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

export default api;
