// src/services/planServicioService.ts
import api from '../lib/axios';

export type Periodicidad = 'QUINCENAL' | 'MENSUAL' | 'BIMESTRAL' | 'TRIMESTRAL';

export const PERIODICIDAD_LABELS: Record<Periodicidad, string> = {
  QUINCENAL: 'Quincenal',
  MENSUAL: 'Mensual',
  BIMESTRAL: 'Bimestral',
  TRIMESTRAL: 'Trimestral',
};

export type EstatusPeriodo = 'SIN_PROGRAMAR' | 'PROGRAMADA' | 'COMPLETADA' | 'CANCELADA';

export interface PlanServicio {
  id: string;
  empresa_id: string;
  cliente_id: string;
  servicio_id?: string | null;
  tecnico_id?: string | null;
  vigencia_desde: string;
  vigencia_hasta?: string | null;
  periodicidad: Periodicidad;
  dia_preferido?: number | null;
  precio_pactado?: number | null;
  certificado_id?: string | null;
  notas?: string | null;
  activo: boolean;
  creado_en: string;
  actualizado_en: string;
  cliente_nombre?: string | null;
  servicio_nombre?: string | null;
  tecnico_nombre?: string | null;
  certificado_folio?: number | null;
}

export interface PlanServicioInput {
  empresa_id: string;
  cliente_id: string;
  servicio_id?: string | null;
  tecnico_id?: string | null;
  vigencia_desde: string;
  vigencia_hasta?: string | null;
  periodicidad: Periodicidad;
  dia_preferido?: number | null;
  precio_pactado?: number | null;
  certificado_id?: string | null;
  notas?: string | null;
  activo?: boolean;
}

export interface PeriodoTablero {
  fecha_tentativa: string;
  estatus: EstatusPeriodo;
  orden_id?: string | null;
  orden_folio?: string | null;
  orden_estado?: string | null;
}

export interface PlanTableroRow {
  plan_id: string;
  cliente_id: string;
  cliente_nombre: string;
  servicio_nombre?: string | null;
  tecnico_nombre?: string | null;
  periodicidad: Periodicidad;
  precio_pactado?: number | null;
  por_vencer: boolean;
  vigencia_hasta?: string | null;
  periodos: PeriodoTablero[];
}

export interface Tablero {
  anio: number;
  mes: number;
  planes: PlanTableroRow[];
}

export interface ProgramarInput {
  fecha: string;
  hora_inicio?: string;
  tecnico_id?: string | null;
}

export const listarPlanes = (params: { empresa_id?: string; cliente_id?: string; activo?: boolean }) =>
  api.get<PlanServicio[]>('/planes-servicio', { params }).then((r) => r.data);

export const obtenerPlan = (id: string) =>
  api.get<PlanServicio>(`/planes-servicio/${id}`).then((r) => r.data);

export const crearPlan = (payload: PlanServicioInput) =>
  api.post<PlanServicio>('/planes-servicio', payload).then((r) => r.data);

export const actualizarPlan = (id: string, payload: Partial<PlanServicioInput>) =>
  api.put<PlanServicio>(`/planes-servicio/${id}`, payload).then((r) => r.data);

export const eliminarPlan = (id: string) =>
  api.delete(`/planes-servicio/${id}`).then((r) => r.data);

export const obtenerTablero = (empresa_id: string, anio: number, mes: number) =>
  api.get<Tablero>('/planes-servicio/tablero', { params: { empresa_id, anio, mes } }).then((r) => r.data);

export const programarServicio = (planId: string, payload: ProgramarInput) =>
  api.post(`/planes-servicio/${planId}/programar`, payload).then((r) => r.data);
