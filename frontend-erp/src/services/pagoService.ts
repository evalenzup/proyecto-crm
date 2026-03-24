// src/services/pagoService.ts

import api from '@/lib/axios';
import type { FacturaOut } from './facturaService';

// Helper
const getData = <T>(p: Promise<{ data: T }>): Promise<T> => p.then((r) => r.data);
const getBlob = (p: Promise<{ data: Blob }>): Promise<Blob> => p.then((r) => r.data);

// ── Tipos ────────────────────────────────────────────────────
export type EstatusPagoCfdi = 'BORRADOR' | 'TIMBRADO' | 'CANCELADO';

export interface PagoListParams {
  limit?: number;
  offset?: number;
  empresa_id?: string;
  cliente_id?: string;
  estatus?: EstatusPagoCfdi;
  fecha_desde?: string;
  fecha_hasta?: string;
  order_by?: string;
  order_dir?: 'asc' | 'desc';
}

export interface FacturaRelacionadaPago {
  factura_id: string;
  importe_pagado: number;
  parcialidad: number;
  saldo_anterior: number;
  saldo_insoluto: number;
}

export interface PagoCreate {
  empresa_id: string;
  cliente_id: string;
  serie?: string;
  fecha_pago: string;
  monto: number;
  moneda?: string;
  tipo_cambio?: number | null;
  forma_pago?: string | null;
  facturas_relacionadas?: FacturaRelacionadaPago[];
}

export type PagoUpdate = Partial<PagoCreate>;

export interface PagoRow {
  id: string;
  empresa_id: string;
  cliente_id: string;
  serie: string;
  folio: string;
  fecha_pago: string;
  monto: number;
  estatus: EstatusPagoCfdi;
  cliente?: { id: string; nombre_comercial: string; email?: string };
}

export interface PagoListResponse {
  items: PagoRow[];
  total: number;
  limit: number;
  offset: number;
}

export interface DocumentoRelacionado {
  factura_id: string;
  uuid_cfdi?: string | null;
  serie?: string | null;
  folio?: string | null;
  moneda?: string | null;
  tipo_cambio?: number | null;
  metodo_pago?: string | null;
  num_parcialidad?: number | null;
  imp_saldo_ant?: number | null;
  imp_pagado?: number | null;
  imp_saldo_insoluto?: number | null;
}

export interface Pago {
  id: string;
  empresa_id: string;
  cliente_id: string;
  serie: string;
  folio: string;
  fecha_pago: string;
  fecha_emision?: string | null;
  fecha_timbrado?: string | null;
  monto: number;
  moneda?: string | null;
  tipo_cambio?: number | null;
  forma_pago?: string | null;
  forma_pago_p?: string | null;
  estatus: EstatusPagoCfdi;
  uuid?: string | null;
  folio_fiscal?: string | null;
  no_certificado?: string | null;
  no_certificado_sat?: string | null;
  sello_cfdi?: string | null;
  sello_sat?: string | null;
  rfc_proveedor_sat?: string | null;
  motivo_cancelacion?: string | null;
  folio_fiscal_sustituto?: string | null;
  cliente?: { id: string; nombre_comercial: string; email?: string };
  facturas_relacionadas?: FacturaRelacionadaPago[];
  documentos_relacionados?: DocumentoRelacionado[];
  message?: string;
}

export interface FacturaPendiente extends FacturaOut {
  saldo_pendiente?: number;
  parcialidad_actual?: number;
}

export interface ExportPagosParams {
  empresa_id?: string;
  estatus?: EstatusPagoCfdi;
  fecha_desde?: string;
  fecha_hasta?: string;
  cliente_id?: string;
}

// ── Pagos ────────────────────────────────────────────────────
export const getPagos = (params: PagoListParams) =>
  getData<PagoListResponse>(api.get('/pagos/', { params }));

export const exportPagosExcel = (params: ExportPagosParams) =>
  getBlob(api.get('/pagos/export-excel', { params, responseType: 'blob' }));

export const getSiguienteFolioPago = (empresaId: string, serie: string) =>
  getData<number>(api.get('/pagos/siguiente-folio', { params: { empresa_id: empresaId, serie } }));

export const getPagoById = (id: string) =>
  getData<Pago>(api.get(`/pagos/${id}`));

export const createPago = (payload: PagoCreate) =>
  getData<Pago>(api.post('/pagos/', payload));

export const updatePago = (id: string, payload: PagoUpdate) =>
  getData<Pago>(api.put(`/pagos/${id}`, payload));

export const timbrarPago = (id: string) =>
  getData<Pago>(api.post(`/pagos/${id}/timbrar`));

export const cancelarPagoSat = (id: string, motivo: string, folioSustituto?: string) =>
  getData<Pago>(api.post(`/pagos/${id}/cancelar-sat`, { motivo, folio_sustituto: folioSustituto }));

export const getFacturasPendientes = (clienteId: string, empresaId?: string, matchRfc = false) =>
  getData<FacturaPendiente[]>(api.get(`/pagos/clientes/${clienteId}/facturas-pendientes`, {
    params: { empresa_id: empresaId, match_rfc: matchRfc },
  }));

export const getPagoPdf = (id: string) =>
  getBlob(api.get(`/pagos/${id}/pdf`, { responseType: 'blob' }));

export const downloadPagoXml = (id: string) =>
  getBlob(api.get(`/pagos/${id}/xml`, { responseType: 'blob' }));

export const enviarPagoEmail = (id: string, recipients: string[], subject?: string, body?: string) =>
  getData<{ message: string }>(api.post(`/pagos/${id}/enviar-email`, { recipients, subject, body }));
