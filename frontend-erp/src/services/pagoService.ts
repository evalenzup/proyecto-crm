// src/services/pagoService.ts

import api from '@/lib/axios';
import type { FacturaOut } from './facturaService'; // Assuming types can be shared

// Helper
const getData = <T = any>(p: Promise<any>): Promise<T> => p.then((r) => r.data);
const getBlob = (p: Promise<any>): Promise<Blob> => p.then((r) => r.data as Blob);

// ---------------------- Pagos ----------------------

export const getPagos = (params: any) =>
  getData<PagoListResponse>(api.get('/pagos/', { params }));

export const exportPagosExcel = (params: any) =>
  getBlob(api.get('/pagos/export-excel', { params, responseType: 'blob' }));

export const getSiguienteFolioPago = (empresaId: string, serie: string) =>
  getData<number>(api.get('/pagos/siguiente-folio', { params: { empresa_id: empresaId, serie } }));

export const getPagoById = (id: string) =>
  getData<Pago>(api.get(`/pagos/${id}`));

export const createPago = (payload: any) => // Define a proper type for payload later
  getData<Pago>(api.post('/pagos/', payload));

export const updatePago = (id: string, payload: any) =>
  getData<Pago>(api.put(`/pagos/${id}`, payload));

export const timbrarPago = (id: string) =>
  getData(api.post(`/pagos/${id}/timbrar`));

export const cancelarPagoSat = (id: string, motivo: string, folioSustituto?: string) =>
  getData(api.post(`/pagos/${id}/cancelar-sat`, { motivo, folio_sustituto: folioSustituto }));

// This is the key function for the form
export const getFacturasPendientes = (clienteId: string, empresaId?: string) =>
  getData<FacturaPendiente[]>(api.get(`/pagos/clientes/${clienteId}/facturas-pendientes`, { params: { empresa_id: empresaId } }));

export const getPagoPdf = (id: string) =>
  getBlob(api.get(`/pagos/${id}/pdf`, { responseType: 'blob' }));

export const downloadPagoXml = (id: string) =>
  getBlob(api.get(`/pagos/${id}/xml`, { responseType: 'blob' }));

export const enviarPagoEmail = (id: string, recipients: string[], subject?: string, body?: string) =>
  getData(api.post(`/pagos/${id}/enviar-email`, { recipients, subject, body }));


// ── Tipos exportados ─────────────────────────────────────────

export type EstatusPagoCfdi = 'BORRADOR' | 'TIMBRADO' | 'CANCELADO';

// Represents a single row in the payments list
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

// The response from the list endpoint
export interface PagoListResponse {
  items: PagoRow[];
  total: number;
  limit: number;
  offset: number;
}

// Represents a full Pago object, as returned by getById or create
export interface Pago {
  id: string;
  // Add all fields from the backend Pago schema
  [key: string]: any;
  motivo_cancelacion?: string;
  folio_fiscal_sustituto?: string;
  no_certificado?: string;
  no_certificado_sat?: string;
  sello_cfdi?: string;
  sello_sat?: string;
  rfc_proveedor_sat?: string;
}

// Represents a pending invoice for the payment form
// This is based on the FacturaOut schema from the backend
export interface FacturaPendiente extends FacturaOut {
  saldo_pendiente?: number;
  parcialidad_actual?: number;
}
