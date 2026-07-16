import api from '@/lib/axios';

export interface AuditoriaLog {
    id: string;
    empresa_id: string | null;
    usuario_id: string | null;
    usuario_email: string | null;
    accion: string;
    entidad: string;
    entidad_id: string | null;
    detalle: string | null; // JSON string
    ip: string | null;
    creado_en: string;
}

export interface AuditoriaPageOut {
    items: AuditoriaLog[];
    total: number;
    limit: number;
    offset: number;
}

export const getAuditoria = (params: {
    empresa_id?: string | null;
    accion?: string | null;
    entidad?: string | null;
    fecha_desde?: string | null;
    fecha_hasta?: string | null;
    offset?: number;
    limit?: number;
    order_by?: string;
    order_dir?: 'asc' | 'desc';
}) => api.get<AuditoriaPageOut>('/auditoria/', { params }).then((r) => r.data);

// ── Reporte de actividad del personal (solo administradores) ─────────────────
export interface ActividadUsuario {
  usuario_id: string;
  email: string;
  nombre: string;
  rol: string;
  total: number;
  dias_activos: number;
  dias_rango: number;
  cobertura_horario: number;
  primera_accion_prom: string | null;
  ultima_accion_prom: string | null;
  accion_top: string | null;
  por_tipo: { accion: string; label: string; total: number }[];
  por_dia: { fecha: string; total: number }[];
  heatmap: { dow: number; hora: number; total: number }[];
  resultados: {
    facturas_timbradas: number; pagos: number; ordenes_creadas: number;
    ordenes_completadas: number; certificados: number; clientes: number;
  };
}
export interface ActividadReporte {
  rango: { desde: string; hasta: string; hora_ini: number; hora_fin: number; dias_rango: number };
  usuarios: ActividadUsuario[];
}

export const getActividad = (params: {
  usuario_ids: string;
  fecha_desde: string;
  fecha_hasta: string;
  empresa_id?: string | null;
  hora_ini?: number;
  hora_fin?: number;
}) => api.get<ActividadReporte>('/auditoria/actividad', { params }).then((r) => r.data);

export const exportAuditoriaExcel = (params: {
  empresa_id?: string | null;
  accion?: string | null;
  entidad?: string | null;
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
}) => api.get('/auditoria/export-excel', { params, responseType: 'blob' }).then((r) => r.data as Blob);

// Cualquier usuario autenticado (admin o supervisor) puede ver auditoría.
// El backend se encarga de acotar los registros:
//   - admin: ve todos los registros de cualquier empresa
//   - supervisor: solo ve los registros de su empresa
export const canViewAuditoria = (rol?: string | null): boolean =>
    rol === 'superadmin' || rol === 'admin' || rol === 'supervisor';

// Permiso (info sensible) que otorga el superadmin por usuario.
export const PERMISO_ACTIVIDAD = 'reportes_actividad';
export const canVerActividad = (
    u?: { rol?: string | null; permisos?: string[] | null } | null
): boolean =>
    u?.rol === 'superadmin' || (u?.permisos || []).includes(PERMISO_ACTIVIDAD);

// Catálogo de acciones para el filtro
export const ACCIONES_AUDITORIA = [
    { label: 'Login', value: 'LOGIN' },
    { label: 'Crear Factura', value: 'CREAR_FACTURA' },
    { label: 'Timbrar Factura', value: 'TIMBRAR_FACTURA' },
    { label: 'Cancelar Factura', value: 'CANCELAR_FACTURA' },
    { label: 'Eliminar Factura', value: 'ELIMINAR_FACTURA' },
    { label: 'Enviar Factura Email', value: 'ENVIAR_FACTURA_EMAIL' },
    { label: 'Crear Pago', value: 'CREAR_PAGO' },
    { label: 'Timbrar Pago', value: 'TIMBRAR_PAGO' },
    { label: 'Cancelar Pago', value: 'CANCELAR_PAGO' },
    { label: 'Enviar Pago Email', value: 'ENVIAR_PAGO_EMAIL' },
    { label: 'Crear Cliente', value: 'CREAR_CLIENTE' },
    { label: 'Actualizar Cliente', value: 'ACTUALIZAR_CLIENTE' },
    { label: 'Eliminar Cliente', value: 'ELIMINAR_CLIENTE' },
    { label: 'Crear Egreso', value: 'CREAR_EGRESO' },
    { label: 'Actualizar Egreso', value: 'ACTUALIZAR_EGRESO' },
    { label: 'Eliminar Egreso', value: 'ELIMINAR_EGRESO' },
    { label: 'Crear Empresa', value: 'CREAR_EMPRESA' },
    { label: 'Actualizar Empresa', value: 'ACTUALIZAR_EMPRESA' },
    { label: 'Crear Presupuesto', value: 'CREAR_PRESUPUESTO' },
    { label: 'Actualizar Presupuesto', value: 'ACTUALIZAR_PRESUPUESTO' },
    { label: 'Cambiar Estado Presupuesto', value: 'CAMBIAR_ESTADO_PRESUPUESTO' },
    { label: 'Eliminar Presupuesto', value: 'ELIMINAR_PRESUPUESTO' },
    { label: 'Enviar Presupuesto', value: 'ENVIAR_PRESUPUESTO' },
    { label: 'Exportar Excel', value: 'EXPORTAR_EXCEL' },
];
