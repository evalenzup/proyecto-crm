import api from '@/lib/axios';

export interface EmpresaMapa {
    id: string;
    nombre: string;
}

export interface ClienteMapa {
    id: string;
    nombre_comercial: string;
    latitud: number;
    longitud: number;
    telefono?: string;
    email?: string;
    actividad?: string;
    total_facturas: number;
    empresas: EmpresaMapa[];
}

export interface ClientesMapaResponse {
    total: number;
    empresas: EmpresaMapa[];
    clientes: ClienteMapa[];
}

export const mapaService = {
    getClientesConServicio: async (): Promise<ClientesMapaResponse> => {
        const { data } = await api.get<ClientesMapaResponse>('/mapa/clientes-servicio');
        return data;
    },
};

export const canViewMapa = (rol?: string | null): boolean =>
    rol === 'superadmin' || rol === 'admin';
