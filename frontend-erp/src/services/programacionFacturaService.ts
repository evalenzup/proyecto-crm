import api from '@/lib/axios';

export type Periodicidad =
  | 'unica' | 'semanal' | 'quincenal' | 'mensual'
  | 'bimestral' | 'trimestral' | 'semestral' | 'anual';

export const PERIODICIDAD_LABELS: Record<Periodicidad, string> = {
  unica:      'Única vez',
  semanal:    'Semanal',
  quincenal:  'Quincenal',
  mensual:    'Mensual',
  bimestral:  'Bimestral',
  trimestral: 'Trimestral',
  semestral:  'Semestral',
  anual:      'Anual',
};

export interface ConceptoPlantilla {
  tipo?:                 string | null;
  producto_servicio_id?: string | null;
  clave_producto:        string;
  clave_unidad:          string;
  descripcion:           string;
  cantidad:              string;
  valor_unitario:        string;
  descuento:             string;
  iva_tasa?:             string | null;
  ret_iva_tasa?:         string | null;
  ret_isr_tasa?:         string | null;
  no_identificacion?:    string | null;
  unidad?:               string | null;
  objeto_imp?:           string | null;
}

export interface ProgramacionFacturaOut {
  id:                  string;
  empresa_id:          string;
  cliente_id:          string;
  nombre?:             string | null;
  serie?:              string | null;
  tipo_comprobante:    string;
  forma_pago?:         string | null;
  metodo_pago?:        string | null;
  uso_cfdi?:           string | null;
  moneda:              string;
  lugar_expedicion?:   string | null;
  condiciones_pago?:   string | null;
  observaciones?:      string | null;
  retencion_local_desc?: string | null;
  retencion_local_tasa?: string | null;
  conceptos:           ConceptoPlantilla[];
  periodicidad:        Periodicidad;
  proxima_ejecucion:   string;   // YYYY-MM-DD
  fecha_fin?:          string | null;
  auto_timbrar:        boolean;
  auto_enviar:         boolean;
  emails_destino:      string[];
  activo:              boolean;
  ultima_ejecucion?:   string | null;
  facturas_generadas:  number;
  creado_en:           string;
  actualizado_en:      string;
  cliente_nombre?:     string | null;
  empresa_nombre?:     string | null;
}

export interface ProgramacionFacturaCreate {
  empresa_id:          string;
  cliente_id:          string;
  nombre?:             string;
  serie?:              string;
  tipo_comprobante?:   string;
  forma_pago?:         string;
  metodo_pago?:        string;
  uso_cfdi?:           string;
  moneda?:             string;
  lugar_expedicion?:   string;
  condiciones_pago?:   string;
  observaciones?:      string;
  retencion_local_desc?: string;
  retencion_local_tasa?: string;
  conceptos:           ConceptoPlantilla[];
  periodicidad:        Periodicidad;
  proxima_ejecucion:   string;
  fecha_fin?:          string;
  auto_timbrar:        boolean;
  auto_enviar:         boolean;
  emails_destino:      string[];
}

export type ProgramacionFacturaUpdate = Partial<ProgramacionFacturaCreate> & { activo?: boolean };

export interface ProgramacionFacturaListOut {
  items: ProgramacionFacturaOut[];
  total: number;
}

export const programacionFacturaService = {
  list: (params?: {
    empresa_id?: string;
    activo?: boolean;
    offset?: number;
    limit?: number;
  }) =>
    api.get<ProgramacionFacturaListOut>('/programacion-facturas', { params }).then(r => r.data),

  get: (id: string) =>
    api.get<ProgramacionFacturaOut>(`/programacion-facturas/${id}`).then(r => r.data),

  create: (data: ProgramacionFacturaCreate) =>
    api.post<ProgramacionFacturaOut>('/programacion-facturas', data).then(r => r.data),

  update: (id: string, data: ProgramacionFacturaUpdate) =>
    api.patch<ProgramacionFacturaOut>(`/programacion-facturas/${id}`, data).then(r => r.data),

  delete: (id: string) =>
    api.delete(`/programacion-facturas/${id}`),

  ejecutarAhora: (id: string) =>
    api.post<ProgramacionFacturaOut>(`/programacion-facturas/${id}/ejecutar-ahora`).then(r => r.data),
};
