import type { EstadoOS, PrioridadOS } from '@/services/ordenServicioService';

// Colores para <Tag color="..."> — nombres reconocidos por Ant Design
export const ESTADO_COLOR: Record<EstadoOS, string> = {
  PENDIENTE:   'gold',
  ASIGNADO:    'blue',
  EN_CAMINO:   'cyan',
  EN_PROGRESO: 'geekblue',
  COMPLETADO:  'green',
  CANCELADO:   'red',
  REAGENDADO:  'orange',
};

// Colores para <Badge status="..."> — solo acepta los valores semánticos de Ant Design
export const ESTADO_BADGE: Record<EstadoOS, 'default' | 'success' | 'processing' | 'error' | 'warning'> = {
  PENDIENTE:   'warning',
  ASIGNADO:    'processing',
  EN_CAMINO:   'processing',
  EN_PROGRESO: 'processing',
  COMPLETADO:  'success',
  CANCELADO:   'error',
  REAGENDADO:  'warning',
};

// Colores HEX para bloques en el timeline — deben coincidir visualmente con ESTADO_COLOR
export const ESTADO_HEX: Record<EstadoOS, string> = {
  PENDIENTE:   '#d48806',  // gold-7 (Ant Design)
  ASIGNADO:    '#1677ff',  // blue-6
  EN_CAMINO:   '#08979c',  // cyan-7
  EN_PROGRESO: '#2f54eb',  // geekblue-6
  COMPLETADO:  '#389e0d',  // green-7
  CANCELADO:   '#cf1322',  // red-7
  REAGENDADO:  '#d46b08',  // orange-7
};

// Fondo suave para los bloques del timeline (mismo tono pero muy claro)
export const ESTADO_BG: Record<EstadoOS, string> = {
  PENDIENTE:   '#fffbe6',
  ASIGNADO:    '#e6f4ff',
  EN_CAMINO:   '#e6fffb',
  EN_PROGRESO: '#f0f5ff',
  COMPLETADO:  '#f6ffed',
  CANCELADO:   '#fff2f0',
  REAGENDADO:  '#fff7e6',
};

export const ESTADO_LABEL: Record<EstadoOS, string> = {
  PENDIENTE:   'Pendiente',
  ASIGNADO:    'Asignado',
  EN_CAMINO:   'En camino',
  EN_PROGRESO: 'En progreso',
  COMPLETADO:  'Completado',
  CANCELADO:   'Cancelado',
  REAGENDADO:  'Reagendado',
};

export const PRIORIDAD_COLOR: Record<PrioridadOS, string> = {
  BAJA:    'green',
  MEDIA:   'blue',
  ALTA:    'orange',
  URGENTE: 'red',
};
