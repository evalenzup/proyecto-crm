// src/services/tecnicoService.ts
import api from '../lib/axios';
import { ServicioOperativoSimpleOut } from './servicioOperativoService';

export interface TecnicoOut {
  id: string;
  empresa_id: string;
  nombre_completo: string;
  telefono?: string | null;
  email?: string | null;
  max_servicios_dia?: number | null;
  activo: boolean;
  notas?: string | null;
  creado_en: string;
  actualizado_en: string;
  especialidades: ServicioOperativoSimpleOut[];
}

export interface TecnicoCreate {
  empresa_id: string;
  nombre_completo: string;
  telefono?: string | null;
  email?: string | null;
  max_servicios_dia?: number | null;
  activo?: boolean;
  notas?: string | null;
  especialidades_ids?: string[];
}

export type TecnicoUpdate = Partial<Omit<TecnicoCreate, 'empresa_id'>>;

export interface TecnicoPageOut {
  items: TecnicoOut[];
  total: number;
  limit: number;
  offset: number;
}

export const tecnicoService = {
  getTecnicos: async (params: {
    empresa_id?: string | null;
    q?: string;
    activo?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<TecnicoPageOut> => {
    const response = await api.get<TecnicoPageOut>('/tecnicos', { params });
    return response.data;
  },

  getTecnico: async (id: string): Promise<TecnicoOut> => {
    const response = await api.get<TecnicoOut>(`/tecnicos/${id}`);
    return response.data;
  },

  createTecnico: async (data: TecnicoCreate): Promise<TecnicoOut> => {
    const response = await api.post<TecnicoOut>('/tecnicos', data);
    return response.data;
  },

  updateTecnico: async (id: string, data: TecnicoUpdate): Promise<TecnicoOut> => {
    const response = await api.put<TecnicoOut>(`/tecnicos/${id}`, data);
    return response.data;
  },

  deleteTecnico: async (id: string): Promise<void> => {
    await api.delete(`/tecnicos/${id}`);
  },
};
