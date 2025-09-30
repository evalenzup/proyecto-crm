// src/lib/axios.ts
import axios from 'axios';
import { message } from 'antd';

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

    if (!isEmailConfigNotFound) {
      const msg =
        error?.response?.data?.detail ||
        error?.response?.statusText ||
        'Error en la comunicación con el servidor';
      message.error(msg);
    }
    return Promise.reject(error);
  }
);

export default api;
