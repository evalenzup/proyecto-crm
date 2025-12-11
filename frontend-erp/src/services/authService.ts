import api from '@/lib/axios';
import { LoginResponse, Usuario } from '@/types/auth';

export const authService = {
    login: async (email: string, password: string): Promise<LoginResponse> => {
        // Usamos x-www-form-urlencoded como espera OAuth2PasswordRequestForm
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const response = await api.post<LoginResponse>('/login/access-token', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        });
        return response.data;
    },

    getMe: async (): Promise<Usuario> => {
        // Implementar endpoint /me en backend o usar /users/me si existiera.
        // Como no creamos /users/me explícitamente en el plan, usaremos /login/test-token o similar,
        // pero lo ideal es un endpoint que devuelva el usuario actual.
        // Vamos a asumir que existirá /api/users/me o similar. 
        // Por ahora, para desbloquear, podemos decodificar el token o crear el endpoint en backend rapido.
        // Revisando deps.py, get_current_user ya existe. Solo falta exponerlo.

        // TODO: Asegurar que exista el endpoint en backend. 
        // Agregaremos este endpoint en backend/users.py o main.py si falta.
        const response = await api.get<Usuario>('/users/me');
        return response.data;
    },
};
