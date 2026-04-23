// src/services/unidadService.ts
import api from '../lib/axios';
import { ServicioOperativoSimpleOut } from './servicioOperativoService';

export type TipoUnidad = 'SEDAN' | 'PICKUP' | 'CAMIONETA' | 'MOTOCICLETA' | 'OTRO';
export type TipoMantenimiento = 'PREVENTIVO' | 'CORRECTIVO';

// ─── Unidad ───────────────────────────────────────────────────────────────────

export interface UnidadOut {
  id: string;
  empresa_id: string;
  nombre: string;
  placa?: string | null;
  tipo: TipoUnidad;
  max_servicios_dia?: number | null;
  activo: boolean;
  notas?: string | null;
  creado_en: string;
  actualizado_en: string;
  servicios_compatibles: ServicioOperativoSimpleOut[];
}

export interface UnidadCreate {
  empresa_id: string;
  nombre: string;
  placa?: string | null;
  tipo?: TipoUnidad;
  max_servicios_dia?: number | null;
  activo?: boolean;
  notas?: string | null;
  servicios_ids?: string[];
}

export type UnidadUpdate = Partial<Omit<UnidadCreate, 'empresa_id'>>;

export interface UnidadPageOut {
  items: UnidadOut[];
  total: number;
  limit: number;
  offset: number;
}

// ─── MantenimientoUnidad ──────────────────────────────────────────────────────

export interface MantenimientoOut {
  id: string;
  unidad_id: string;
  tipo: TipoMantenimiento;
  fecha_realizado: string;
  kilometraje_actual?: number | null;
  descripcion?: string | null;
  costo?: number | null;
  proveedor?: string | null;
  proxima_fecha?: string | null;
  proximo_kilometraje?: number | null;
  creado_en: string;
}

export interface MantenimientoCreate {
  tipo?: TipoMantenimiento;
  fecha_realizado: string;
  kilometraje_actual?: number | null;
  descripcion?: string | null;
  costo?: number | null;
  proveedor?: string | null;
  proxima_fecha?: string | null;
  proximo_kilometraje?: number | null;
}

export type MantenimientoUpdate = Partial<MantenimientoCreate>;

export interface MantenimientoPageOut {
  items: MantenimientoOut[];
  total: number;
  limit: number;
  offset: number;
}

// ─── Service functions ────────────────────────────────────────────────────────

export const unidadService = {
  getUnidades: async (params: {
    empresa_id?: string | null;
    q?: string;
    activo?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<UnidadPageOut> => {
    const response = await api.get<UnidadPageOut>('/unidades', { params });
    return response.data;
  },

  getUnidad: async (id: string): Promise<UnidadOut> => {
    const response = await api.get<UnidadOut>(`/unidades/${id}`);
    return response.data;
  },

  createUnidad: async (data: UnidadCreate): Promise<UnidadOut> => {
    const response = await api.post<UnidadOut>('/unidades', data);
    return response.data;
  },

  updateUnidad: async (id: string, data: UnidadUpdate): Promise<UnidadOut> => {
    const response = await api.put<UnidadOut>(`/unidades/${id}`, data);
    return response.data;
  },

  deleteUnidad: async (id: string): Promise<void> => {
    await api.delete(`/unidades/${id}`);
  },

  // ── Mantenimientos ─────────────────────────────────────────────────────────
  getMantenimientos: async (
    unidadId: string,
    params?: { limit?: number; offset?: number }
  ): Promise<MantenimientoPageOut> => {
    const response = await api.get<MantenimientoPageOut>(
      `/unidades/${unidadId}/mantenimientos`,
      { params }
    );
    return response.data;
  },

  createMantenimiento: async (
    unidadId: string,
    data: MantenimientoCreate
  ): Promise<MantenimientoOut> => {
    const response = await api.post<MantenimientoOut>(
      `/unidades/${unidadId}/mantenimientos`,
      data
    );
    return response.data;
  },

  updateMantenimiento: async (
    unidadId: string,
    mantId: string,
    data: MantenimientoUpdate
  ): Promise<MantenimientoOut> => {
    const response = await api.put<MantenimientoOut>(
      `/unidades/${unidadId}/mantenimientos/${mantId}`,
      data
    );
    return response.data;
  },

  deleteMantenimiento: async (unidadId: string, mantId: string): Promise<void> => {
    await api.delete(`/unidades/${unidadId}/mantenimientos/${mantId}`);
  },
};
