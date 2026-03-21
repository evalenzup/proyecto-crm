// src/lib/axios.ts
import axios from 'axios';
import { message } from 'antd';
import { normalizeHttpError } from '@/utils/httpError';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const isEmailConfigNotFound = (
      status === 404 &&
      error?.config?.url?.includes('/email-config')
    );
    const isValidationError = status === 422;
    // Los 401/403 son manejados silenciosamente por el interceptor de refresh token
    const isAuthError = status === 401 || status === 403;

    if (!isEmailConfigNotFound && !isValidationError && !isAuthError) {
      const msg = normalizeHttpError(error);
      message.error(msg);
    }
    return Promise.reject(error);
  }
);

// Request interceptor for API calls
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor — manejo de 401 con refresh token automático
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const is401 = error.response?.status === 401 || error.response?.status === 403;
    const isRefreshEndpoint = originalRequest?.url?.includes('/login/refresh-token');

    if (is401 && !originalRequest._retry && !isRefreshEndpoint) {
      originalRequest._retry = true;

      const refreshToken = typeof window !== 'undefined'
        ? localStorage.getItem('refresh_token')
        : null;

      if (refreshToken) {
        try {
          // Importación dinámica para evitar dependencia circular con authService
          const { authService } = await import('@/services/authService');
          const tokens = await authService.refreshToken(refreshToken);

          localStorage.setItem('token', tokens.access_token);
          localStorage.setItem('refresh_token', tokens.refresh_token);

          // Reintentar request original con el nuevo token
          originalRequest.headers = {
            ...originalRequest.headers,
            Authorization: `Bearer ${tokens.access_token}`,
          };
          return api(originalRequest);
        } catch {
          // Refresh falló — limpiar sesión y redirigir a login
          localStorage.removeItem('token');
          localStorage.removeItem('refresh_token');
          if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
            window.location.href = '/login';
          }
        }
      } else {
        localStorage.removeItem('token');
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default api;
