// frontend-erp/src/services/clienteService.ts
import api from '../lib/axios';

// Definir interfaces para los esquemas de datos (pueden ser más detalladas si se importan de un generador)
interface ClienteSchema {
  properties: Record<string, unknown>;
  required?: string[];
}

export interface ExportClientesParams {
  empresa_id?: string | null;
  rfc?: string | null;
  nombre_comercial?: string | null;
}

export interface ClienteOut {
  id: string;
  nombre_comercial: string;
  nombre_razon_social: string;
  rfc: string;
  regimen_fiscal: string;
  // Dirección fiscal
  calle?: string;
  numero_exterior?: string;
  numero_interior?: string;
  colonia?: string;
  ciudad?: string;
  estado?: string;
  codigo_postal: string;
  // Dirección de servicio / operativa
  serv_calle?: string;
  serv_numero_exterior?: string;
  serv_numero_interior?: string;
  serv_colonia?: string;
  serv_ciudad?: string;
  serv_estado?: string;
  serv_codigo_postal?: string;
  serv_referencia?: string;
  // Geolocalización
  latitud?: number | null;
  longitud?: number | null;
  // Contacto
  telefono?: string[];
  email?: string[];
  // Financiero
  dias_credito: number;
  dias_recepcion: number;
  dias_pago: number;
  tamano?: 'CHICO' | 'MEDIANO' | 'GRANDE';
  actividad?: 'RESIDENCIAL' | 'COMERCIAL' | 'INDUSTRIAL';
  creado_en: string;
  actualizado_en: string;
  empresas?: Array<{ id: string; nombre_comercial: string }>;
}

export interface ClienteCreate {
  nombre_comercial: string;
  nombre_razon_social: string;
  rfc: string;
  regimen_fiscal: string;
  codigo_postal: string;
  telefono?: string[];
  email?: string[];
  dias_credito?: number;
  dias_recepcion?: number;
  dias_pago?: number;
  tamano?: 'CHICO' | 'MEDIANO' | 'GRANDE';
  actividad?: 'RESIDENCIAL' | 'COMERCIAL' | 'INDUSTRIAL';
  serv_calle?: string;
  serv_numero_exterior?: string;
  serv_numero_interior?: string;
  serv_colonia?: string;
  serv_codigo_postal?: string;
  serv_referencia?: string;
  empresa_id: string[];
}

export interface ClienteUpdate {
  nombre_comercial?: string;
  nombre_razon_social?: string;
  rfc?: string;
  regimen_fiscal?: string;
  codigo_postal?: string;
  telefono?: string[];
  email?: string[];
  dias_credito?: number;
  dias_recepcion?: number;
  dias_pago?: number;
  tamano?: 'CHICO' | 'MEDIANO' | 'GRANDE';
  actividad?: 'RESIDENCIAL' | 'COMERCIAL' | 'INDUSTRIAL';
  serv_calle?: string;
  serv_numero_exterior?: string;
  serv_numero_interior?: string;
  serv_colonia?: string;
  serv_codigo_postal?: string;
  serv_referencia?: string;
  empresa_id?: string[];
}


export interface ClientePageOut {
  items: ClienteOut[];
  total: number;
  limit: number;
  offset: number;
}


export const clienteService = {
  getClienteSchema: async (): Promise<ClienteSchema> => {
    const response = await api.get<ClienteSchema>('/clientes/schema');
    return response.data;
  },

  buscarClientes: async (q: string, empresaId?: string, searchField: 'comercial' | 'fiscal' | 'both' = 'comercial', limit: number = 10): Promise<ClienteOut[]> => {
    const params: { q: string; limit: number; search_field: string; empresa_id?: string } = { q, limit, search_field: searchField };
    if (empresaId) {
      params.empresa_id = empresaId;
    }
    const response = await api.get<ClienteOut[]>(`/clientes/busqueda`, { params });
    return response.data;
  },

  checkRfcExistence: async (rfc: string, excludeId?: string): Promise<string[]> => {
    const params: { rfc: string; exclude_id?: string } = { rfc };
    if (excludeId) params.exclude_id = excludeId;
    // Retorna lista de nombres de empresas
    const response = await api.get<string[]>('/clientes/validar-rfc', { params });
    return response.data;
  },

  checkExistingClient: async (rfc: string, nombre_comercial: string): Promise<ClienteOut | null> => {
    const params = { rfc, nombre_comercial };
    const response = await api.get<ClienteOut | null>('/clientes/buscar-existente', { params });
    return response.data;
  },

  exportClientesExcel: async (params: ExportClientesParams): Promise<Blob> => {
    const response = await api.get('/clientes/export-excel', { params, responseType: 'blob' });
    return response.data;
  },

  getClientes: async (params: {
    limit: number;
    offset: number;
    empresa_id?: string | null; // Ahora lo pasaremos explícitamente
    rfc?: string | null;
    nombre_comercial?: string | null;
    nombre_razon_social?: string | null;
    order_by?: string;
    order_dir?: 'asc' | 'desc';
  }): Promise<ClientePageOut> => {
    const response = await api.get<ClientePageOut>("/clientes", { params });
    return response.data;
  },

  getCliente: async (id: string): Promise<ClienteOut> => {
    const response = await api.get<ClienteOut>(`/clientes/${id}`);
    return response.data;
  },

  createCliente: async (data: ClienteCreate): Promise<ClienteOut> => {
    const response = await api.post<ClienteOut>('/clientes', data);
    return response.data;
  },

  updateCliente: async (id: string, data: ClienteUpdate): Promise<ClienteOut> => {
    const response = await api.put<ClienteOut>(`/clientes/${id}`, data);
    return response.data;
  },

  linkCliente: async (id: string, empresa_ids: string[]): Promise<void> => {
    await api.post(`/clientes/${id}/vincular`, { empresa_ids });
  },

  deleteCliente: async (id: string): Promise<void> => {
    await api.delete(`/clientes/${id}`);
  },

  // ── Documentos del cliente (contrato firmado, adjuntos) ──────────────────────
  listDocumentos: async (id: string): Promise<ClienteDocumento[]> => {
    const response = await api.get<ClienteDocumento[]>(`/clientes/${id}/documentos`);
    return response.data;
  },

  uploadDocumento: async (
    id: string,
    file: File,
    meta: {
      tipo: string;
      nombre?: string;
      numero?: string;
      vigencia_desde?: string;
      vigencia_hasta?: string;
      notas?: string;
    },
  ): Promise<ClienteDocumento> => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('tipo', meta.tipo);
    if (meta.nombre) fd.append('nombre', meta.nombre);
    if (meta.numero) fd.append('numero', meta.numero);
    if (meta.vigencia_desde) fd.append('vigencia_desde', meta.vigencia_desde);
    if (meta.vigencia_hasta) fd.append('vigencia_hasta', meta.vigencia_hasta);
    if (meta.notas) fd.append('notas', meta.notas);
    const response = await api.post<ClienteDocumento>(`/clientes/${id}/documentos`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  downloadDocumento: async (id: string, docId: string): Promise<Blob> => {
    const response = await api.get(`/clientes/${id}/documentos/${docId}/archivo`, {
      responseType: 'blob',
    });
    return response.data;
  },

  deleteDocumento: async (id: string, docId: string): Promise<void> => {
    await api.delete(`/clientes/${id}/documentos/${docId}`);
  },

  // ── Croquis del cliente (planos, general o por área) ─────────────────────────
  listCroquis: async (id: string, empresaId?: string): Promise<Croquis[]> => {
    const response = await api.get<Croquis[]>(`/clientes/${id}/croquis`, {
      params: { empresa_id: empresaId },
    });
    return response.data;
  },

  uploadCroquis: async (
    id: string,
    file: File,
    meta: { empresa_id: string; titulo?: string; area?: string; descripcion?: string },
  ): Promise<Croquis> => {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('empresa_id', meta.empresa_id);
    if (meta.titulo) fd.append('titulo', meta.titulo);
    if (meta.area) fd.append('area', meta.area);
    if (meta.descripcion) fd.append('descripcion', meta.descripcion);
    const response = await api.post<Croquis>(`/clientes/${id}/croquis`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  downloadCroquis: async (id: string, croquisId: string): Promise<Blob> => {
    const response = await api.get(`/clientes/${id}/croquis/${croquisId}/archivo`, {
      responseType: 'blob',
    });
    return response.data;
  },

  deleteCroquis: async (id: string, croquisId: string): Promise<void> => {
    await api.delete(`/clientes/${id}/croquis/${croquisId}`);
  },
};

export interface ClienteDocumento {
  id: string;
  tipo: string;
  nombre: string;
  archivo: string;
  numero?: string | null;
  vigencia_desde?: string | null;
  vigencia_hasta?: string | null;
  notas?: string | null;
  creado_en: string;
}

export interface Croquis {
  id: string;
  empresa_id: string;
  cliente_id: string;
  titulo: string;
  area?: string | null;
  descripcion?: string | null;
  archivo: string;
  creado_en: string;
}
