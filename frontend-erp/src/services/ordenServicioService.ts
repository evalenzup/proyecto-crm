// src/services/ordenServicioService.ts
import api from '../lib/axios';

export type EstadoOS =
  | 'PENDIENTE'
  | 'ASIGNADO'
  | 'EN_CAMINO'
  | 'EN_PROGRESO'
  | 'COMPLETADO'
  | 'CANCELADO'
  | 'REAGENDADO';

export type PrioridadOS = 'BAJA' | 'MEDIA' | 'ALTA' | 'URGENTE';

export interface ClienteSimpleOut {
  id: string;
  nombre_comercial: string;
  telefono?: string | null;
}

export interface TecnicoSimpleOut {
  id: string;
  nombre_completo: string;
}

export interface UnidadSimpleOut {
  id: string;
  nombre: string;
  placas?: string | null;
}

export interface ServicioSimpleOut {
  id: string;
  nombre: string;
}

export interface HistorialEstadoOSOut {
  id: string;
  estado_anterior?: string | null;
  estado_nuevo: string;
  notas?: string | null;
  creado_en: string;
  usuario_nombre?: string | null;
}

export interface OrdenServicioOut {
  id: string;
  empresa_id: string;
  folio_os: string;
  cliente_id: string;
  tecnico_id?: string | null;
  unidad_id?: string | null;
  servicio_id?: string | null;
  presupuesto_id?: string | null;
  fecha_programada: string;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  duracion_minutos?: number | null;
  estado: EstadoOS;
  prioridad: PrioridadOS;
  direccion_servicio?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  precio_acordado?: number | null;
  notas_tecnico?: string | null;
  notas_internas?: string | null;
  notas_cierre?: string | null;
  activo: boolean;
  creado_en: string;
  actualizado_en: string;
  factura_id?: string | null;
  // Relacionados
  cliente?: ClienteSimpleOut | null;
  tecnico?: TecnicoSimpleOut | null;
  unidad?: UnidadSimpleOut | null;
  servicio?: ServicioSimpleOut | null;
  factura?: FacturaResumenOut | null;
  historial: HistorialEstadoOSOut[];
}

export interface FacturaResumenOut {
  id: string;
  serie?: string | null;
  folio?: number | null;
  estatus?: string | null;
  status_pago?: string | null;
  total?: number | null;
}

export interface OrdenServicioListOut {
  id: string;
  folio_os: string;
  fecha_programada: string;
  hora_inicio?: string | null;
  hora_fin?: string | null;
  estado: EstadoOS;
  prioridad: PrioridadOS;
  cliente_nombre?: string | null;
  tecnico_nombre?: string | null;
  direccion_servicio?: string | null;
  precio_acordado?: number | null;
  notas_tecnico?: string | null;
}

export interface OrdenServicioCreate {
  cliente_id: string;
  tecnico_id?: string | null;
  unidad_id?: string | null;
  servicio_id?: string | null;
  presupuesto_id?: string | null;
  fecha_programada: string; // YYYY-MM-DD
  hora_inicio?: string | null; // HH:MM:SS
  hora_fin?: string | null;
  duracion_minutos?: number | null;
  estado?: EstadoOS;
  prioridad?: PrioridadOS;
  direccion_servicio?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  precio_acordado?: number | null;
  notas_tecnico?: string | null;
  notas_internas?: string | null;
  notas_cierre?: string | null;
}

export type OrdenServicioUpdate = Partial<Omit<OrdenServicioCreate, 'cliente_id'>>;

export interface CambioEstadoOS {
  estado: EstadoOS;
  notas?: string | null;
}

export interface ListOrdenesParams {
  empresa_id?: string;
  fecha_desde?: string;
  fecha_hasta?: string;
  estado?: EstadoOS;
  prioridad?: PrioridadOS;
  tecnico_id?: string;
  cliente_id?: string;
  q?: string;
  activo?: boolean;
  limit?: number;
  offset?: number;
}

const ordenServicioService = {
  list: async (params: ListOrdenesParams = {}): Promise<{ items: OrdenServicioListOut[]; total: number }> => {
    const { data } = await api.get('/ordenes-servicio', { params });
    return data;
  },

  get: async (id: string): Promise<OrdenServicioOut> => {
    const { data } = await api.get(`/ordenes-servicio/${id}`);
    return data;
  },

  create: async (orden: OrdenServicioCreate, empresaId?: string): Promise<OrdenServicioOut> => {
    const params = empresaId ? { empresa_id: empresaId } : {};
    const { data } = await api.post('/ordenes-servicio', orden, { params });
    return data;
  },

  update: async (id: string, orden: OrdenServicioUpdate): Promise<OrdenServicioOut> => {
    const { data } = await api.put(`/ordenes-servicio/${id}`, orden);
    return data;
  },

  cambiarEstado: async (id: string, payload: CambioEstadoOS): Promise<OrdenServicioOut> => {
    const { data } = await api.patch(`/ordenes-servicio/${id}/estado`, payload);
    return data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/ordenes-servicio/${id}`);
  },

  // ── Factura ────────────────────────────────────────────────────────────────
  crearFactura: async (id: string): Promise<{ factura_id: string; serie: string; folio: number }> => {
    const { data } = await api.post(`/ordenes-servicio/${id}/crear-factura`);
    return data;
  },

  vincularFactura: async (id: string, factura_id: string): Promise<OrdenServicioOut> => {
    const { data } = await api.post(`/ordenes-servicio/${id}/vincular-factura`, { factura_id });
    return data;
  },

  desvincularFactura: async (id: string): Promise<OrdenServicioOut> => {
    const { data } = await api.delete(`/ordenes-servicio/${id}/factura`);
    return data;
  },
};

export default ordenServicioService;
