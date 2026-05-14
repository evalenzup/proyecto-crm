// src/services/unidadService.ts
import api from '../lib/axios';
import { ServicioOperativoSimpleOut } from './servicioOperativoService';

export type TipoUnidad = 'SEDAN' | 'PICKUP' | 'CAMIONETA' | 'MOTOCICLETA' | 'VAN' | 'CAMION' | 'OTRO';
export type TipoMantenimiento = 'PREVENTIVO' | 'CORRECTIVO';

// ─── Póliza de Seguro ─────────────────────────────────────────────────────────

export interface PolizaSeguroOut {
  id: string;
  unidad_id: string;
  num_poliza: string;
  compania: string;
  fecha_expedicion?: string | null;
  fecha_vencimiento?: string | null;
  activo: boolean;
  documento?: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface PolizaSeguroCreate {
  num_poliza: string;
  compania: string;
  fecha_expedicion?: string | null;
  fecha_vencimiento?: string | null;
  activo?: boolean;
}

export type PolizaSeguroUpdate = Partial<PolizaSeguroCreate>;

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

  // Información del vehículo
  numero_serie?: string | null;
  marca?: string | null;
  version?: string | null;
  modelo_anio?: number | null;
  capacidad_personas?: number | null;
  color?: string | null;
  numero_motor?: string | null;
  numero_economico?: string | null;
  propietario?: string | null;

  // Fotos
  foto_frontal?: string | null;
  foto_lateral?: string | null;
  foto_placa?: string | null;

  // Tarjeta de circulación
  tarjeta_circulacion?: string | null;
  fecha_expedicion_tc?: string | null;
  fecha_vencimiento_tc?: string | null;
  doc_tarjeta_circulacion?: string | null;

  creado_en: string;
  actualizado_en: string;
  servicios_compatibles: ServicioOperativoSimpleOut[];
  polizas_seguro: PolizaSeguroOut[];
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

  // Información del vehículo
  numero_serie?: string | null;
  marca?: string | null;
  version?: string | null;
  modelo_anio?: number | null;
  capacidad_personas?: number | null;
  color?: string | null;
  numero_motor?: string | null;
  numero_economico?: string | null;
  propietario?: string | null;

  // Tarjeta de circulación
  tarjeta_circulacion?: string | null;
  fecha_expedicion_tc?: string | null;
  fecha_vencimiento_tc?: string | null;
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

  // ── Fotos ──────────────────────────────────────────────────────────────────

  subirFoto: async (
    unidadId: string,
    campo: 'foto_frontal' | 'foto_lateral' | 'foto_placa',
    file: File
  ): Promise<UnidadOut> => {
    const form = new FormData();
    form.append('file', file);
    const response = await api.post<UnidadOut>(
      `/unidades/${unidadId}/fotos/${campo}`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  eliminarFoto: async (
    unidadId: string,
    campo: 'foto_frontal' | 'foto_lateral' | 'foto_placa'
  ): Promise<void> => {
    await api.delete(`/unidades/${unidadId}/fotos/${campo}`);
  },

  // ── Documentos ────────────────────────────────────────────────────────────

  subirDocTarjetaCirculacion: async (
    unidadId: string,
    file: File
  ): Promise<UnidadOut> => {
    const form = new FormData();
    form.append('file', file);
    const response = await api.post<UnidadOut>(
      `/unidades/${unidadId}/doc-tarjeta-circulacion`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  eliminarDocTarjetaCirculacion: async (unidadId: string): Promise<void> => {
    await api.delete(`/unidades/${unidadId}/doc-tarjeta-circulacion`);
  },

  // ── Pólizas de Seguro ─────────────────────────────────────────────────────

  crearPoliza: async (
    unidadId: string,
    data: PolizaSeguroCreate
  ): Promise<PolizaSeguroOut> => {
    const response = await api.post<PolizaSeguroOut>(
      `/unidades/${unidadId}/polizas-seguro`,
      data
    );
    return response.data;
  },

  actualizarPoliza: async (
    unidadId: string,
    polizaId: string,
    data: PolizaSeguroUpdate
  ): Promise<PolizaSeguroOut> => {
    const response = await api.put<PolizaSeguroOut>(
      `/unidades/${unidadId}/polizas-seguro/${polizaId}`,
      data
    );
    return response.data;
  },

  eliminarPoliza: async (unidadId: string, polizaId: string): Promise<void> => {
    await api.delete(`/unidades/${unidadId}/polizas-seguro/${polizaId}`);
  },

  subirDocPoliza: async (
    unidadId: string,
    polizaId: string,
    file: File
  ): Promise<PolizaSeguroOut> => {
    const form = new FormData();
    form.append('file', file);
    const response = await api.post<PolizaSeguroOut>(
      `/unidades/${unidadId}/polizas-seguro/${polizaId}/documento`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  eliminarDocPoliza: async (unidadId: string, polizaId: string): Promise<void> => {
    await api.delete(`/unidades/${unidadId}/polizas-seguro/${polizaId}/documento`);
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
