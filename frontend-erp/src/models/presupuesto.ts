// frontend-erp/src/models/presupuesto.ts

export interface PresupuestoDetalle {
  id: string;
  producto_servicio_id?: string;
  descripcion: string;
  cantidad: number;
  unidad?: string;
  precio_unitario: number;
  tasa_impuesto: number;
  costo_estimado?: number;
  importe: number;
  margen_estimado?: number;
}

export interface PresupuestoAdjunto {
  id: string;
  archivo: string;
  nombre: string;
  tipo?: string;
  fecha_subida: string;
}

export interface PresupuestoEvento {
  id: string;
  usuario_id: string;
  accion: string;
  comentario?: string;
  fecha_evento: string;
}

export interface Presupuesto {
  id: string;
  folio: string;
  version: number;
  estado: string;
  cliente_id: string;
  empresa_id: string;
  responsable_id?: string;
  fecha_emision: string;
  fecha_vencimiento?: string;
  moneda: 'MXN' | 'USD';
  tipo_cambio?: number;
  condiciones_comerciales?: string;
  notas_internas?: string;
  subtotal: number;
  descuento_total: number;
  impuestos: number;
  total: number;
  creado_en: string;
  actualizado_en: string;
  detalles: PresupuestoDetalle[];
  adjuntos: PresupuestoAdjunto[];
  eventos: PresupuestoEvento[];
  firma_cliente?: string;
  cliente: {
    id: string;
    nombre_comercial: string;
  };
}
