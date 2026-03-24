//src/services/facturaService.ts

import api from '@/lib/axios';
import type { ProductoServicioCreate } from './productoServicioService';

// Helpers — tipados con la forma mínima de AxiosResponse que usamos
const getData = <T>(p: Promise<{ data: T }>): Promise<T> => p.then((r) => r.data);
const getBlob = (p: Promise<{ data: Blob }>): Promise<Blob> => p.then((r) => r.data);

// ── Tipos: Concepto ──────────────────────────────────────────
export interface Concepto {
  id?: string;
  clave_prod_serv: string;
  no_identificacion?: string | null;
  cantidad: number;
  clave_unidad: string;
  unidad?: string | null;
  descripcion: string;
  valor_unitario: number;
  descuento?: number | null;
  objeto_imp?: string | null;
  impuestos?: Record<string, unknown> | null;
  // campos calculados (solo lectura)
  importe?: number;
  subtotal?: number;
  iva?: number;
  total?: number;
}

// ── Tipos: Factura ───────────────────────────────────────────
export type EstatusCFDI = 'BORRADOR' | 'TIMBRADA' | 'CANCELADA';
export type EstatusPago = 'PAGADA' | 'NO_PAGADA';

export interface FacturaRow {
  id: string;
  empresa_id: string;
  cliente_id: string;
  serie: string;
  folio: number;
  creado_en: string;
  estatus: EstatusCFDI;
  status_pago: EstatusPago;
  total: number;
  fecha_pago?: string | null;
  fecha_cobro?: string | null;
  cliente?: { id: string; nombre_comercial: string; email?: string };
}

export interface FacturaListResponse {
  items: FacturaRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface FacturaListParams {
  limit?: number;
  offset?: number;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
  empresa_id?: string;
  cliente_id?: string;
  estatus?: EstatusCFDI;
  status_pago?: EstatusPago;
  fecha_desde?: string;
  fecha_hasta?: string;
  folio?: string | number;
}

export interface FacturaOut extends FacturaRow {
  moneda?: string;
  tipo_cambio?: number | null;
  metodo_pago?: string | null;
  forma_pago?: string | null;
  uso_cfdi?: string | null;
  lugar_expedicion?: string | null;
  condiciones_pago?: string | null;
  cfdi_relacionados_tipo?: string | null;
  cfdi_relacionados?: string | null;
  folio_fiscal?: string | null;
  fecha_emision?: string | null;
  fecha_timbrado?: string | null;
  fecha_pago?: string | null;
  fecha_cobro?: string | null;
  observaciones?: string | null;
  conceptos?: Concepto[];
  actualizado_en: string;
  message?: string;
}

export interface FacturaCreate {
  empresa_id: string;
  cliente_id: string;
  serie?: string;
  moneda?: string;
  tipo_cambio?: number | null;
  metodo_pago?: string | null;
  forma_pago?: string | null;
  uso_cfdi?: string | null;
  lugar_expedicion?: string | null;
  condiciones_pago?: string | null;
  cfdi_relacionados_tipo?: string | null;
  cfdi_relacionados?: string | null;
  fecha_pago?: string | null;
  observaciones?: string | null;
  conceptos: Concepto[];
}

export type FacturaUpdate = Partial<FacturaCreate>;

// ── Tipos: Empresa (uso interno) ─────────────────────────────
interface EmpresaItem {
  id: string;
  nombre_comercial: string;
  nombre?: string;
  logo?: string | null;
  tiene_config_email?: boolean;
  rfc?: string;
  regimen_fiscal?: string;
  codigo_postal?: string;
}

interface EmpresaPageOut {
  items: EmpresaItem[];
  total: number;
  limit: number;
  offset: number;
}

// ── Tipos: Export params ─────────────────────────────────────
export interface ExportFacturasParams {
  empresa_id?: string;
  estatus?: EstatusCFDI;
  status_pago?: EstatusPago;
  fecha_desde?: string;
  fecha_hasta?: string;
  cliente_id?: string;
}

// ── Facturas ─────────────────────────────────────────────────
export const getFacturas = (params: FacturaListParams) =>
  getData<FacturaListResponse>(api.get('/facturas/', { params }));

export const exportFacturasExcel = (params: ExportFacturasParams) =>
  getBlob(api.get('/facturas/export-excel', { params, responseType: 'blob' }));

export const getFacturaById = (id: string) =>
  getData<FacturaOut>(api.get(`/facturas/${id}`));

export const createFactura = (payload: FacturaCreate) =>
  getData<FacturaOut>(api.post('/facturas/', payload));

export const updateFactura = (id: string, payload: FacturaUpdate) =>
  getData<FacturaOut>(api.put(`/facturas/${id}`, payload));

export const timbrarFactura = (id: string) =>
  getData<FacturaOut>(api.post(`/facturas/${id}/timbrar`));

export const cancelarFactura = (id: string, motivo: string, folioSustituto?: string) =>
  getData<FacturaOut>(
    api.post(`/facturas/${id}/cancelar`, {
      motivo_cancelacion: motivo,
      folio_fiscal_sustituto: folioSustituto ?? null,
    })
  );

export const getPdfPreview = (id: string) =>
  getBlob(api.get(`/facturas/${id}/preview-pdf`, { responseType: 'blob' }));

export const getPdf = (id: string) =>
  getBlob(api.get(`/facturas/${id}/pdf`, { responseType: 'blob' }));

export const downloadPdf = (id: string) =>
  getBlob(api.get(`/facturas/${id}/pdf`, { responseType: 'blob' }));

export const downloadXml = (id: string) =>
  getBlob(api.get(`/facturas/${id}/xml`, { responseType: 'blob' }));

export const sendEmail = (id: string, recipients: string | string[]) => {
  const payload = Array.isArray(recipients)
    ? { recipients }
    : { recipient_emails: String(recipients) };
  return getData<{ message: string }>(api.post(`/facturas/${id}/send-email`, payload));
};

export const sendPreviewEmail = (id: string, recipients: string | string[]) => {
  const payload = Array.isArray(recipients)
    ? { recipients }
    : { recipient_emails: String(recipients) };
  return getData<{ message: string }>(api.post(`/facturas/${id}/send-preview-email`, payload));
};

export const duplicarFactura = (id: string) =>
  getData<FacturaOut>(api.post(`/facturas/${id}/duplicar`));

// ── Empresas / Clientes ──────────────────────────────────────
export const getEmpresas = async () => {
  const response = await api.get<EmpresaPageOut>('/empresas/', {
    params: { limit: 1000, offset: 0 },
  });
  return response.data.items;
};

export const getEmpresaById = async (id: string): Promise<EmpresaItem> =>
  (await api.get<EmpresaItem>(`/empresas/${id}`)).data;

export const getClientesByEmpresa = async (empresaId: string) =>
  (await api.get(`/clientes/?empresa_id=${empresaId}`)).data;

export const searchClientes = async (
  query: string,
  empresaId?: string,
  searchField: 'comercial' | 'fiscal' | 'both' = 'comercial'
) => {
  const params: { q: string; limit: number; search_field: string; empresa_id?: string } = {
    q: query,
    limit: 10,
    search_field: searchField,
  };
  if (empresaId) params.empresa_id = empresaId;
  return (await api.get(`/clientes/busqueda`, { params })).data;
};

export const getClienteById = async (id: string) =>
  (await api.get(`/clientes/${id}`)).data;

// ── Productos / Servicios ────────────────────────────────────
export const getProductosServicios = async (empresaId?: string) => {
  const params = empresaId ? { empresa_id: empresaId } : {};
  return (await api.get('/productos-servicios/', { params })).data;
};

export const searchProductosServicios = async (empresaId: string, query: string) =>
  (await api.get(
    `/productos-servicios/busqueda?empresa_id=${encodeURIComponent(empresaId)}&q=${encodeURIComponent(query)}`
  )).data;

export const createProductoServicio = async (payload: ProductoServicioCreate) =>
  (await api.post('/productos-servicios/', payload)).data;

// ── Catálogos ────────────────────────────────────────────────
export const getMetodosPago = async () => (await api.get('/catalogos/cfdi/metodos-pago')).data;
export const getFormasPago = async () => (await api.get('/catalogos/cfdi/formas-pago')).data;
export const getUsosCfdi = async () => (await api.get('/catalogos/cfdi/usos-cfdi')).data;
export const getRegimenesFiscales = async () => (await api.get('/catalogos/regimen-fiscal')).data;
export const getTiposRelacion = async () => (await api.get('/catalogos/cfdi/tipos-relacion')).data;
export const getMotivosCancelacion = async () => (await api.get('/catalogos/cfdi/motivos-cancelacion')).data;

export const searchSatProductos = async (q: string) =>
  (await api.get(`/catalogos/busqueda/productos?q=${encodeURIComponent(q)}&limit=20`)).data;

export const searchSatUnidades = async (q: string) =>
  (await api.get(`/catalogos/busqueda/unidades?q=${encodeURIComponent(q)}&limit=20`)).data;
