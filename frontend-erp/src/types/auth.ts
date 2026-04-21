export enum RolUsuario {
    SUPERADMIN = 'superadmin',
    ADMIN = 'admin',
    SUPERVISOR = 'supervisor',
    ESTANDAR = 'estandar',
    OPERATIVO = 'operativo',
}

export interface Usuario {
    id: string;
    email: string;
    nombre_completo?: string;
    rol: RolUsuario;
    is_active: boolean;
    empresa_id?: string;
    /** IDs de empresas accesibles (admin/superadmin) */
    empresas_ids: string[];
    /** Módulos habilitados (estandar) */
    permisos: string[];
}

export interface LoginResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
}

export interface AuthState {
    user: Usuario | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
}
