// src/services/pagoService.ts

import api from '@/lib/axios';
import type { FacturaOut } from './facturaService'; // Assuming types can be shared

// Helper
const getData = <T = any>(p: Promise<any>): Promise<T> => p.then((r) => r.data);
const getBlob = (p: Promise<any>): Promise<Blob> => p.then((r) => r.data as Blob);

// ---------------------- Pagos ----------------------

export const getPagos = (params: any) =>
  getData<PagoListResponse>(api.get('/pagos/', { params }));

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

// This is the key function for the form
export const getFacturasPendientes = (clienteId: string) =>
  getData<FacturaPendiente[]>(api.get(`/pagos/clientes/${clienteId}/facturas-pendientes`));

export const getPagoPdf = (id: string) =>
  getBlob(api.get(`/pagos/${id}/pdf`, { responseType: 'blob' }));

export const downloadPagoXml = (id: string) =>
  getBlob(api.get(`/pagos/${id}/xml`, { responseType: 'blob' }));


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
  cliente?: { id: string; nombre_comercial: string };
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
    // The backend doesn't calculate this yet, the UI will have to assume
    // for a NO_PAGADA invoice, saldo_pendiente is the total.
    saldo_pendiente?: number;
}
