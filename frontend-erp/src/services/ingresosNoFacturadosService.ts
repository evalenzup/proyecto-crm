// src/services/ingresosNoFacturadosService.ts
import api from '../lib/axios';

export const PERMISO_INGRESOS = 'ingresos_no_facturados';

export const canVerIngresos = (u?: { rol?: string; permisos?: string[] } | null): boolean =>
  u?.rol === 'superadmin' || (u?.permisos || []).includes(PERMISO_INGRESOS);

export interface IngresoRow {
  orden_id: string;
  folio_os: string;
  fecha_programada: string;
  cliente_id: string;
  cliente_nombre: string;
  estado: string;
  precio_acordado?: number | null;
  cobrado: boolean;
  fecha_cobro?: string | null;
  forma_cobro?: string | null;
}

export interface IngresosResumen {
  total_no_facturado: number;
  total_cobrado: number;
  total_pendiente: number;
  num_ordenes: number;
  num_cobradas: number;
}

export interface IngresosNoFacturados {
  resumen: IngresosResumen;
  items: IngresoRow[];
}

export interface MarcarCobroInput {
  cobrado: boolean;
  fecha_cobro?: string | null;
  forma_cobro?: string | null;
}

export const obtenerIngresos = (params: {
  empresa_id?: string;
  cliente_id?: string;
  anio?: number;
  mes?: number;
  cobrado?: boolean;
}) => api.get<IngresosNoFacturados>('/ingresos-no-facturados', { params }).then((r) => r.data);

export const marcarCobro = (ordenId: string, payload: MarcarCobroInput) =>
  api.patch(`/ingresos-no-facturados/${ordenId}/cobro`, payload).then((r) => r.data);
