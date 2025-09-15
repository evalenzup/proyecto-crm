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

interface ClienteCreate {
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

interface ClienteUpdate {
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


export const clienteService = {
  getClienteSchema: async (): Promise<ClienteSchema> => {
    const response = await api.get<ClienteSchema>('/clientes/schema');
    return response.data;
  },

  buscarClientes: async (q: string, limit: number = 10): Promise<ClienteOut[]> => {
    const response = await api.get<ClienteOut[]>(`/clientes/busqueda`, { params: { q, limit } });
    return response.data;
  },

  getClientes: async (): Promise<ClienteOut[]> => {
    const response = await api.get<ClienteOut[]>('/clientes');
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
