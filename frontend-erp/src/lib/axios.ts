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
    const isEmailConfigNotFound = (
      error?.response?.status === 404 &&
      error?.config?.url &&
      error.config.url.includes('/email-config')
    );
    const isValidationError = error?.response?.status === 422;

    // Evitar toasts ruidosos para 404 del email-config y para validaciones 422;
    // las pantallas de formularios manejarán el 422 localmente.
    if (!isEmailConfigNotFound && !isValidationError) {
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

// Response interceptor for API calls
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if ((error.response?.status === 401 || error.response?.status === 403) && !originalRequest._retry) {
      originalRequest._retry = true;
      localStorage.removeItem('token');
      // Redirigir a login si es necesario, aunque esto se maneja mejor en el AuthProvider
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
