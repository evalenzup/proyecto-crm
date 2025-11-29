// frontend-erp/src/services/clienteService.ts
import api from '../lib/axios';

// Definir interfaces para los esquemas de datos (pueden ser más detalladas si se importan de un generador)
interface ClienteSchema {
  properties: Record<string, any>;
  required?: string[];
}

export interface ClienteOut {
  id: string;
  nombre_comercial: string;
  nombre_razon_social: string;
  rfc: string;
  regimen_fiscal: string;
  codigo_postal: string;
  telefono?: string[];
  email?: string[];
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

  buscarClientes: async (q: string, empresaId?: string, limit: number = 10): Promise<ClienteOut[]> => {
    const params: any = { q, limit };
    if (empresaId) {
      params.empresa_id = empresaId;
    }
    const response = await api.get<ClienteOut[]>(`/clientes/busqueda`, { params });
    return response.data;
  },

  getClientes: async (params: {
    limit: number;
    offset: number;
    empresa_id?: string | null;
    rfc?: string | null;
    nombre_comercial?: string | null;
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

  deleteCliente: async (id: string): Promise<void> => {
    await api.delete(`/clientes/${id}`);
  },
};
