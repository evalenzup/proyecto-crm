// frontend-erp/src/services/presupuestoService.ts
import api from '../lib/axios';
import { Presupuesto } from '@/models/presupuesto';

interface ClienteSimple {
  id: string;
  nombre_comercial: string;
}

// Interfaces basadas en los schemas de Pydantic
export interface PresupuestoSimpleOut {
  id: string;
  folio: string;
  version: number;
  estado: string;
  fecha_emision: string; // Las fechas llegan como strings
  total: number;
  cliente: ClienteSimple;
}

export interface PresupuestoPageOut {
  items: PresupuestoSimpleOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface PresupuestoDetalleCreate {
  producto_servicio_id?: string;
  descripcion: string;
  cantidad: number;
  unidad?: string;
  precio_unitario: number;
  tasa_impuesto: number;
  costo_estimado?: number;
}

export interface PresupuestoCreate {
  cliente_id: string;
  empresa_id: string;
  responsable_id?: string;
  fecha_emision: string;
  fecha_vencimiento?: string;
  moneda: 'MXN' | 'USD';
  tipo_cambio?: number;
  condiciones_comerciales?: string;
  notas_internas?: string;
  detalles: PresupuestoDetalleCreate[];
}

export interface PresupuestoUpdate {
  // Define los campos que se pueden actualizar
  estado?: 'BORRADOR' | 'ENVIADO' | 'ACEPTADO' | 'RECHAZADO' | 'CADUCADO' | 'FACTURADO';
  // ... otros campos según PresupuestoUpdate en el backend
}

export const presupuestoService = {
  getPresupuestos: async (params: {
    limit: number;
    offset: number;
    empresa_id?: string;
    cliente_id?: string;
    estado?: string;
    fecha_inicio?: string;
    fecha_fin?: string;
  }): Promise<PresupuestoPageOut> => {
    const response = await api.get<PresupuestoPageOut>("/presupuestos", { params });
    return response.data;
  },

  getSiguienteFolio: async (empresaId: string): Promise<{ folio: string }> => {
    const response = await api.get(`/presupuestos/siguiente-folio`, { params: { empresa_id: empresaId } });
    return response.data;
  },

  getPresupuesto: async (id: string): Promise<Presupuesto> => {
    const response = await api.get<Presupuesto>(`/presupuestos/${id}`);
    return response.data;
  },

  createPresupuesto: async (data: PresupuestoCreate): Promise<Presupuesto> => {
    const response = await api.post<Presupuesto>('/presupuestos', data);
    return response.data;
  },

  updatePresupuesto: async (id: string, data: PresupuestoUpdate): Promise<Presupuesto> => {
    const response = await api.put<Presupuesto>(`/presupuestos/${id}`, data);
    return response.data;
  },

  deletePresupuesto: async (id: string): Promise<void> => {
    await api.delete(`/presupuestos/${id}`);
  },

  getPresupuestoPdf: async (id: string): Promise<Blob> => {
    const response = await api.get(`/presupuestos/${id}/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  },

  sendPresupuesto: async (id: string, recipient_email: string): Promise<{ message: string }> => {
    const response = await api.post(`/presupuestos/${id}/enviar`, { recipient_email });
    return response.data;
  },

  getPresupuestoHistory: async (folio: string, empresaId: string): Promise<Presupuesto[]> => {
    const response = await api.get<Presupuesto[]>(`/presupuestos/historial/${folio}`, {
      params: { empresa_id: empresaId },
    });
    return response.data;
  },

  updatePresupuestoStatus: async (id: string, estado: string): Promise<Presupuesto> => {
    const response = await api.patch<Presupuesto>(`/presupuestos/${id}/estado`, { estado });
    return response.data;
  },

  uploadEvidencia: async (id: string, file: File): Promise<Presupuesto> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<Presupuesto>(`/presupuestos/${id}/evidencia`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  convertirAFactura: async (id: string): Promise<{ id: string }> => { // Assuming it returns the new factura's ID
    const response = await api.post(`/presupuestos/${id}/convertir-a-factura`);
    return response.data;
  },
};
