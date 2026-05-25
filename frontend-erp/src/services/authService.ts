import axios from 'axios';
import api, { getAccessToken } from '@/lib/axios';
import { LoginResponse, Usuario } from '@/types/auth';

export const authService = {
    /**
     * Inicia sesión. El backend devuelve el access_token en body
     * y establece el refresh_token como cookie httpOnly automáticamente.
     */
    login: async (email: string, password: string): Promise<LoginResponse> => {
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await api.post<LoginResponse>('/login/access-token', formData, {
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        });
        return response.data;
    },

    /**
     * Renueva el access token usando la cookie httpOnly del refresh token.
     * No se envía ningún body — el navegador adjunta la cookie automáticamente.
     * Se usa axios directo (no la instancia `api`) para evitar bucle infinito
     * con el interceptor de 401.
     */
    refreshToken: async (): Promise<LoginResponse> => {
        const response = await axios.post<LoginResponse>(
            `${process.env.NEXT_PUBLIC_API_URL}/login/refresh-token`,
            {},
            { withCredentials: true },
        );
        return response.data;
    },

    /**
     * Cierra la sesión. El backend invalida el JTI leyendo la cookie httpOnly
     * y borra la cookie en la respuesta.
     */
    logout: async (): Promise<void> => {
        try {
            await axios.post(
                `${process.env.NEXT_PUBLIC_API_URL}/login/logout`,
                {},
                {
                    withCredentials: true,
                    headers: { Authorization: `Bearer ${getAccessToken() ?? ''}` },
                },
            );
        } catch {
            // Si falla (token ya expirado, red caída) no bloqueamos el logout local
        }
    },

    getMe: async (): Promise<Usuario> => {
        const response = await api.get<Usuario>('/users/me');
        return response.data;
    },
};
