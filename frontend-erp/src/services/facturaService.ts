//src/services/facturaService.ts

import api from '@/lib/axios';

// Helpers
const getData = <T = any>(p: Promise<any>): Promise<T> => p.then((r) => r.data);
const getBlob = (p: Promise<any>): Promise<Blob> => p.then((r) => r.data as Blob);

// ---------------------- Facturas ----------------------
export const getFacturas = (params: any) =>
  getData(api.get('/facturas/', { params }));

export const getFacturaById = (id: string) =>
  getData(api.get(`/facturas/${id}`));

export const createFactura = (payload: any) =>
  getData(api.post('/facturas/', payload));

export const updateFactura = (id: string, payload: any) =>
  getData(api.put(`/facturas/${id}`, payload));

export const timbrarFactura = (id: string) =>
  getData(api.post(`/facturas/${id}/timbrar`));

export const cancelarFactura = (id: string, motivo: string, folioSustituto?: string) =>
  getData(
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

// Enviar factura por email. Acepta uno o varios destinatarios.
export const sendEmail = (id: string, recipients: string | string[]) => {
  const payload = Array.isArray(recipients)
    ? { recipients }
    : { recipient_emails: String(recipients) };
  return getData(api.post(`/facturas/${id}/send-email`, payload));
};

// ---------------------- Empresas / Clientes ----------------------
interface EmpresaPageOut {
  items: any[];
  total: number;
  limit: number;
  offset: number;
}

export const getEmpresas = async () => {
  const response = await api.get<EmpresaPageOut>("/empresas/", {
    params: { limit: 1000, offset: 0 },
  });
  return response.data.items;
};

export const getEmpresaById = async (id: string) =>
  (await api.get(`/empresas/${id}`)).data;

export const getClientesByEmpresa = async (empresaId: string) =>
  (await api.get(`/clientes/?empresa_id=${empresaId}`)).data;

export const searchClientes = async (query: string, empresaId?: string) => {
  const params: any = { q: query, limit: 10 };
  if (empresaId) params.empresa_id = empresaId;
  return (await api.get(`/clientes/busqueda`, { params })).data;
};

export const getClienteById = async (id: string) =>
  (await api.get(`/clientes/${id}`)).data;

// ---------------------- Productos / Servicios ----------------------
export const getProductosServicios = async (empresaId?: string) => {
  const params = empresaId ? { empresa_id: empresaId } : {};
  return (await api.get('/productos-servicios/', { params })).data;
};

export const searchProductosServicios = async (empresaId: string, query: string) =>
  (await api.get(
    `/productos-servicios/busqueda?empresa_id=${encodeURIComponent(empresaId)}&q=${encodeURIComponent(query)}`
  )).data;

export const createProductoServicio = async (payload: any) =>
  (await api.post('/productos-servicios/', payload)).data;

// ---------------------- Catálogos ----------------------
export const getMetodosPago         = async () => (await api.get('/catalogos/cfdi/metodos-pago')).data;
export const getFormasPago          = async () => (await api.get('/catalogos/cfdi/formas-pago')).data;
export const getUsosCfdi            = async () => (await api.get('/catalogos/cfdi/usos-cfdi')).data;
export const getRegimenesFiscales   = async () => (await api.get('/catalogos/regimen-fiscal')).data;
export const getTiposRelacion       = async () => (await api.get('/catalogos/cfdi/tipos-relacion')).data;
export const getMotivosCancelacion  = async () => (await api.get('/catalogos/cfdi/motivos-cancelacion')).data;

// SAT search (con query)
export const searchSatProductos = async (q: string) =>
  (await api.get(`/catalogos/busqueda/productos?q=${encodeURIComponent(q)}&limit=20`)).data;

export const searchSatUnidades = async (q: string) =>
  (await api.get(`/catalogos/busqueda/unidades?q=${encodeURIComponent(q)}&limit=20`)).data;


// ── Tipos exportados ─────────────────────────────────────────
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
  cliente?: { id: string; nombre_comercial: string };
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
  fecha_desde?: string; // YYYY-MM-DD
  fecha_hasta?: string; // YYYY-MM-DD
}

// Detalle de factura usado en varios formularios
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
  conceptos?: any[];
}
