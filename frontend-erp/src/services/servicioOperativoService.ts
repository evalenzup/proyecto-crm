// src/services/servicioOperativoService.ts
import api from '../lib/axios';

export interface ServicioOperativoSimpleOut {
  id: string;
  nombre: string;
  activo: boolean;
}

export interface ServicioOperativoOut {
  id: string;
  empresa_id: string;
  nombre: string;
  descripcion?: string | null;
  duracion_estimada_min?: number | null;
  duracion_variable: boolean;
  personal_requerido: number;
  requiere_vehiculo: boolean;
  servicio_padre_id?: string | null;
  observaciones?: string | null;
  activo: boolean;
  creado_en: string;
  actualizado_en: string;
  servicio_padre?: ServicioOperativoSimpleOut | null;
}

export interface ServicioOperativoCreate {
  empresa_id: string;
  nombre: string;
  descripcion?: string | null;
  duracion_estimada_min?: number | null;
  duracion_variable?: boolean;
  personal_requerido?: number;
  requiere_vehiculo?: boolean;
  servicio_padre_id?: string | null;
  observaciones?: string | null;
  activo?: boolean;
}

export type ServicioOperativoUpdate = Partial<Omit<ServicioOperativoCreate, 'empresa_id'>>;

export interface ServicioOperativoPageOut {
  items: ServicioOperativoOut[];
  total: number;
  limit: number;
  offset: number;
}

export const servicioOperativoService = {
  getServicios: async (params: {
    empresa_id?: string | null;
    q?: string;
    activo?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<ServicioOperativoPageOut> => {
    const response = await api.get<ServicioOperativoPageOut>('/servicios-operativos', { params });
    return response.data;
  },

  getServicio: async (id: string): Promise<ServicioOperativoOut> => {
    const response = await api.get<ServicioOperativoOut>(`/servicios-operativos/${id}`);
    return response.data;
  },

  createServicio: async (data: ServicioOperativoCreate): Promise<ServicioOperativoOut> => {
    const response = await api.post<ServicioOperativoOut>('/servicios-operativos', data);
    return response.data;
  },

  updateServicio: async (id: string, data: ServicioOperativoUpdate): Promise<ServicioOperativoOut> => {
    const response = await api.put<ServicioOperativoOut>(`/servicios-operativos/${id}`, data);
    return response.data;
  },

  deleteServicio: async (id: string): Promise<void> => {
    await api.delete(`/servicios-operativos/${id}`);
  },
};
