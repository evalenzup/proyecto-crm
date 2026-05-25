import type { EstadoOS, PrioridadOS } from '@/services/ordenServicioService';

export const ESTADO_COLOR: Record<EstadoOS, string> = {
  PENDIENTE: 'default',
  ASIGNADO: 'blue',
  EN_CAMINO: 'cyan',
  EN_PROGRESO: 'processing',
  COMPLETADO: 'success',
  CANCELADO: 'error',
  REAGENDADO: 'warning',
};

export const ESTADO_LABEL: Record<EstadoOS, string> = {
  PENDIENTE: 'Pendiente',
  ASIGNADO: 'Asignado',
  EN_CAMINO: 'En camino',
  EN_PROGRESO: 'En progreso',
  COMPLETADO: 'Completado',
  CANCELADO: 'Cancelado',
  REAGENDADO: 'Reagendado',
};

export const PRIORIDAD_COLOR: Record<PrioridadOS, string> = {
  BAJA: 'green',
  MEDIA: 'blue',
  ALTA: 'orange',
  URGENTE: 'red',
};
