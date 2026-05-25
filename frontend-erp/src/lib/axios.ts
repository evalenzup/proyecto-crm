// src/lib/axios.ts
import axios from 'axios';
import { message } from 'antd';
import { normalizeHttpError } from '@/utils/httpError';

// ─── Access token en memoria (no en localStorage) ────────────────────────────
// El refresh token viaja como httpOnly cookie y el navegador lo adjunta solo.
// Este módulo es la fuente de verdad del access token vigente.
let _accessToken: string | null = null;

export const setAccessToken = (token: string | null): void => {
  _accessToken = token;
};

export const getAccessToken = (): string | null => _accessToken;

// ─── Instancia de axios ───────────────────────────────────────────────────────
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  withCredentials: true, // envía la cookie httpOnly del refresh token automáticamente
});

// ─── Cola para peticiones que llegan mientras se está renovando el token ──────
// Evita que múltiples 401 simultáneos lancen N llamadas de refresh en paralelo.
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
  setAccessToken(null);
  if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
    window.location.href = '/login';
  }
};

// ─── Interceptor de request: adjunta el access token vigente ─────────────────
api.interceptors.request.use(
  (config) => {
    if (_accessToken) {
      config.headers.Authorization = `Bearer ${_accessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ─── Interceptor de response: errores genéricos ───────────────────────────────
// Los 401/403 se manejan silenciosamente en el siguiente interceptor.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const isEmailConfigNotFound = status === 404 && error?.config?.url?.includes('/email-config');
    const isValidationError = status === 422;
    const isAuthError = status === 401 || status === 403;
    const isSilent = error?.config?.silentError === true;

    if (!isEmailConfigNotFound && !isValidationError && !isAuthError && !isSilent) {
      const msg = normalizeHttpError(error);
      if (msg) message.error(msg);
      error._handled = true;
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

    // Solo refrescamos en 401 (token expirado/inválido).
    // El 403 es "acceso denegado" (permiso), no un problema de token — no refrescar.
    if (status === 401 && !originalRequest._retry && !isRefreshEndpoint) {
      // Si ya hay un refresh en curso, encolar esta petición y esperar
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

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        // Importación dinámica para evitar dependencia circular en inicialización
        const { authService } = await import('@/services/authService');
        // El refresh token viaja automáticamente como cookie — no se envía en body
        const tokens = await authService.refreshToken();

        setAccessToken(tokens.access_token);
        processQueue(null, tokens.access_token);

        originalRequest.headers = {
          ...originalRequest.headers,
          Authorization: `Bearer ${tokens.access_token}`,
        };
        return api(originalRequest);
      } catch (refreshError) {
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
