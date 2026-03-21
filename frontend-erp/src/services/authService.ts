import axios from 'axios';
import api from '@/lib/axios';
import { LoginResponse, Usuario } from '@/types/auth';

export const authService = {
    login: async (email: string, password: string): Promise<LoginResponse> => {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await api.post<LoginResponse>('/login/access-token', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
        return response.data;
    },

    refreshToken: async (refreshToken: string): Promise<LoginResponse> => {
        // Usamos axios directo (no la instancia `api`) para evitar que el interceptor
        // de 401 capture este request y genere un bucle infinito.
        const response = await axios.post<LoginResponse>(
            `${process.env.NEXT_PUBLIC_API_URL}/login/refresh-token`,
            { refresh_token: refreshToken },
        );
        return response.data;
    },

    getMe: async (): Promise<Usuario> => {
        const response = await api.get<Usuario>('/users/me');
        return response.data;
    },
};
