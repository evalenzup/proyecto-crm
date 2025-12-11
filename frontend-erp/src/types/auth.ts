export enum RolUsuario {
    ADMIN = 'admin',
    SUPERVISOR = 'supervisor',
}

export interface Usuario {
    id: string;
    email: string;
    nombre_completo?: string;
    rol: RolUsuario;
    is_active: boolean;
    empresa_id?: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export interface AuthState {
    user: Usuario | null;
    isAuthenticated: boolean;
    isLoading: boolean;
    error: string | null;
}
