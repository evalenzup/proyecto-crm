import api from '@/lib/axios';

export interface RestriccionesAcceso {
    /** false bloquea cualquier eliminación en el sistema */
    puede_eliminar?: boolean;
    /** false bloquea las exportaciones a Excel */
    puede_exportar?: boolean;
    /** "HH:MM" u "HH:MM:SS", hora del centro */
    horario_inicio?: string | null;
    horario_fin?: string | null;
    /** ISO: 1=lunes … 7=domingo, separados por coma. Ej. "1,2,3,4,5" */
    dias_laborales?: string | null;
    /** IPs o rangos CIDR separados por coma */
    ips_permitidas?: string | null;
    /** Horario por día; manda sobre horario_inicio/fin. {"1": ["08:00","18:00"]} */
    horario_semanal?: Record<string, [string, string]> | null;
}

export interface Usuario {
    id: string;
    email: string;
    nombre_completo: string | null;
    rol: 'superadmin' | 'admin' | 'supervisor' | 'estandar' | 'operativo';
    is_active: boolean;
    empresa_id: string | null;
    empresas_ids: string[];
    permisos: string[];
    puede_eliminar: boolean;
    puede_exportar: boolean;
    horario_inicio: string | null;
    horario_fin: string | null;
    dias_laborales: string | null;
    ips_permitidas: string | null;
    horario_semanal: Record<string, [string, string]> | null;
    empresa?: {
        id: string;
        nombre_comercial: string;
    };
}

export interface UsuarioCreate {
    email: string;
    password: string;
    nombre_completo?: string;
    rol: 'admin' | 'supervisor' | 'estandar' | 'operativo';
    is_active?: boolean;
    empresa_id?: string | null;
    empresas_ids?: string[];
    permisos?: string[];
    restricciones?: RestriccionesAcceso;
}

export interface UsuarioUpdate {
    email?: string;
    password?: string;
    nombre_completo?: string;
    rol?: 'admin' | 'supervisor' | 'estandar' | 'operativo';
    is_active?: boolean;
    empresa_id?: string | null;
    empresas_ids?: string[];
    permisos?: string[];
    restricciones?: RestriccionesAcceso;
}

export interface UsuarioPreferences {
    theme: string;
    font_size?: number;
}

export interface UsuarioPreferencesUpdate {
    theme?: string;
    font_size?: number;
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
    },

    cambiarPassword: async (data: { password_actual: string; password_nuevo: string }) => {
        const response = await api.put<Usuario>('/users/me/password', data);
        return response.data;
    },

    asignarEmpresas: async (userId: string, empresas_ids: string[]) => {
        const response = await api.put<Usuario>(`/users/${userId}/empresas`, { empresas_ids });
        return response.data;
    },

    asignarPermisos: async (userId: string, permisos: string[]) => {
        const response = await api.put<Usuario>(`/users/${userId}/permisos`, { permisos });
        return response.data;
    },
};
