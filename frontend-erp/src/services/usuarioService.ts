import api from '@/lib/axios';

export interface Usuario {
    id: string;
    email: string;
    nombre_completo: string | null;
    rol: 'admin' | 'supervisor';
    is_active: boolean;
    empresa_id: string | null;
    empresa?: {
        id: string;
        nombre_comercial: string;
    };
}

export interface UsuarioCreate {
    email: string;
    password: string;
    nombre_completo?: string;
    rol: 'admin' | 'supervisor';
    is_active?: boolean;
    empresa_id?: string | null;
}

export interface UsuarioUpdate {
    email?: string;
    password?: string;
    nombre_completo?: string;
    rol?: 'admin' | 'supervisor';
    is_active?: boolean;
    empresa_id?: string | null;
}

export interface UsuarioPreferences {
    theme: string;
}

export interface UsuarioPreferencesUpdate {
    theme: string;
}

export const usuarioService = {
    getPreferences: async () => {
        const response = await api.get<UsuarioPreferences>('/users/preferences');
        return response.data;
    },

    updatePreferences: async (data: UsuarioPreferencesUpdate) => {
        const response = await api.put<UsuarioPreferences>('/users/preferences', data);
        return response.data;
    },

    getUsuarios: async () => {
        const response = await api.get<Usuario[]>('/users/');
        return response.data;
    },

    getUsuario: async (id: string) => {
        // Usamos el endpoint específico ahora disponible en backend
        const response = await api.get<Usuario>(`/users/${id}`);
        return response.data;
    },

    // Update: Agregando endpoint getById real si decido implementarlo en backend
    getUsuarioReal: async (id: string) => {
        const response = await api.get<Usuario>(`/users/${id}`);
        return response.data;
    },

    createUsuario: async (data: UsuarioCreate) => {
        const response = await api.post<Usuario>('/users/', data);
        return response.data;
    },

    updateUsuario: async (id: string, data: UsuarioUpdate) => {
        const response = await api.put<Usuario>(`/users/${id}`, data);
        return response.data;
    },

    deleteUsuario: async (id: string) => {
        const response = await api.delete<Usuario>(`/users/${id}`);
        return response.data;
    }
};
