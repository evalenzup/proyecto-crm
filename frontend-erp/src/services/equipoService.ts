// src/services/equipoService.ts
import api from '../lib/axios';

export type TipoDato = 'TEXTO' | 'NUMERO' | 'FECHA' | 'BOOLEANO' | 'LISTA';

export interface TipoEquipoCampo {
  id?: string;
  tipo_equipo_id?: string;
  etiqueta: string;
  clave: string;
  tipo_dato: TipoDato;
  opciones?: string[] | null;
  requerido: boolean;
  orden: number;
}

export interface TipoEquipo {
  id: string;
  empresa_id: string;
  nombre: string;
  descripcion?: string | null;
  orden: number;
  activo: boolean;
  campos: TipoEquipoCampo[];
  creado_en: string;
  actualizado_en: string;
}

export interface TipoEquipoCreate {
  empresa_id: string;
  nombre: string;
  descripcion?: string | null;
  orden?: number;
  activo?: boolean;
  campos?: Omit<TipoEquipoCampo, 'id' | 'tipo_equipo_id'>[];
}

export type TipoEquipoUpdate = Partial<Omit<TipoEquipoCreate, 'empresa_id'>>;

export interface EstadoEquipo {
  id: string;
  empresa_id: string;
  nombre: string;
  orden: number;
  activo: boolean;
}

export interface EstadoEquipoCreate {
  empresa_id: string;
  nombre: string;
  orden?: number;
  activo?: boolean;
}

export type EstadoEquipoUpdate = Partial<Omit<EstadoEquipoCreate, 'empresa_id'>>;

export interface EquipoControl {
  id: string;
  empresa_id: string;
  cliente_id: string;
  tipo_equipo_id: string;
  tipo_equipo_nombre?: string | null;
  estado_id?: string | null;
  estado_nombre?: string | null;
  identificador?: string | null;
  area?: string | null;
  fecha_instalacion?: string | null;
  notas?: string | null;
  activo: boolean;
  valores?: Record<string, unknown> | null;
  creado_en: string;
  actualizado_en: string;
}

export interface EquipoControlCreate {
  empresa_id: string;
  cliente_id: string;
  tipo_equipo_id: string;
  estado_id?: string | null;
  identificador?: string | null;
  area?: string | null;
  fecha_instalacion?: string | null;
  notas?: string | null;
  activo?: boolean;
  valores?: Record<string, unknown> | null;
}

export type EquipoControlUpdate = Partial<Omit<EquipoControlCreate, 'empresa_id' | 'cliente_id'>>;

export interface EquipoControlBulkCreate {
  empresa_id: string;
  cliente_id: string;
  tipo_equipo_id: string;
  estado_id?: string | null;
  area?: string | null;
  fecha_instalacion?: string | null;
  cantidad: number;
  prefijo?: string | null;
  numero_inicial?: number;
  relleno_ceros?: number;
  valores?: Record<string, unknown> | null;
}

export interface EquipoControlPageOut {
  items: EquipoControl[];
  total: number;
  limit: number;
  offset: number;
}

export const equipoService = {
  // ── Tipos ──────────────────────────────────────────────
  getTipos: async (empresaId: string, activo?: boolean): Promise<TipoEquipo[]> => {
    const { data } = await api.get<TipoEquipo[]>('/equipos/tipos', {
      params: { empresa_id: empresaId, activo },
    });
    return data;
  },
  createTipo: async (payload: TipoEquipoCreate): Promise<TipoEquipo> => {
    const { data } = await api.post<TipoEquipo>('/equipos/tipos', payload);
    return data;
  },
  updateTipo: async (id: string, payload: TipoEquipoUpdate): Promise<TipoEquipo> => {
    const { data } = await api.put<TipoEquipo>(`/equipos/tipos/${id}`, payload);
    return data;
  },
  deleteTipo: async (id: string): Promise<void> => {
    await api.delete(`/equipos/tipos/${id}`);
  },

  // ── Estados ────────────────────────────────────────────
  getEstados: async (empresaId: string, activo?: boolean): Promise<EstadoEquipo[]> => {
    const { data } = await api.get<EstadoEquipo[]>('/equipos/estados', {
      params: { empresa_id: empresaId, activo },
    });
    return data;
  },
  createEstado: async (payload: EstadoEquipoCreate): Promise<EstadoEquipo> => {
    const { data } = await api.post<EstadoEquipo>('/equipos/estados', payload);
    return data;
  },
  updateEstado: async (id: string, payload: EstadoEquipoUpdate): Promise<EstadoEquipo> => {
    const { data } = await api.put<EstadoEquipo>(`/equipos/estados/${id}`, payload);
    return data;
  },
  deleteEstado: async (id: string): Promise<void> => {
    await api.delete(`/equipos/estados/${id}`);
  },

  // ── Equipos ────────────────────────────────────────────
  getEquipos: async (params: {
    cliente_id?: string;
    empresa_id?: string;
    tipo_equipo_id?: string;
    estado_id?: string;
    q?: string;
    activo?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<EquipoControlPageOut> => {
    const { data } = await api.get<EquipoControlPageOut>('/equipos', { params });
    return data;
  },
  createEquipo: async (payload: EquipoControlCreate): Promise<EquipoControl> => {
    const { data } = await api.post<EquipoControl>('/equipos', payload);
    return data;
  },
  bulkCreate: async (payload: EquipoControlBulkCreate): Promise<EquipoControl[]> => {
    const { data } = await api.post<EquipoControl[]>('/equipos/bulk', payload);
    return data;
  },
  updateEquipo: async (id: string, payload: EquipoControlUpdate): Promise<EquipoControl> => {
    const { data } = await api.put<EquipoControl>(`/equipos/${id}`, payload);
    return data;
  },
  deleteEquipo: async (id: string): Promise<void> => {
    await api.delete(`/equipos/${id}`);
  },
};
