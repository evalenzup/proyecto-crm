// frontend-erp/src/services/productoServicioService.ts
import api from '../lib/axios';

interface ProductoServicioSchema {
  properties: Record<string, any>;
  required?: string[];
}

export enum TipoProductoServicio {
  PRODUCTO = "PRODUCTO",
  SERVICIO = "SERVICIO",
}

export interface ProductoServicioOut {
  id: string;
  tipo: TipoProductoServicio;
  clave_producto: string;
  clave_unidad: string;
  descripcion: string;
  valor_unitario: number;
  empresa_id: string;
  cantidad?: number;
  stock_actual?: number;
  stock_minimo?: number;
  unidad_inventario?: string;
  ubicacion?: string;
  requiere_lote: boolean;
  creado_en: string;
  actualizado_en: string;
}

export interface ProductoServicioCreate {
  tipo: TipoProductoServicio;
  clave_producto: string;
  clave_unidad: string;
  descripcion: string;
  valor_unitario: number;
  empresa_id: string;
  cantidad?: number;
  stock_actual?: number;
  stock_minimo?: number;
  unidad_inventario?: string;
  ubicacion?: string;
  requiere_lote: boolean;
}

export interface ProductoServicioUpdate {
  tipo?: TipoProductoServicio;
  clave_producto?: string;
  clave_unidad?: string;
  descripcion?: string;
  valor_unitario?: number;
  empresa_id?: string;
  cantidad?: number;
  stock_actual?: number;
  stock_minimo?: number;
  unidad_inventario?: string;
  ubicacion?: string;
  requiere_lote?: boolean;
}

export interface ProductoServicioPageOut {
  items: ProductoServicioOut[];
  total: number;
  limit: number;
  offset: number;
}

export const productoServicioService = {
  getProductoServicioSchema: async (): Promise<ProductoServicioSchema> => {
    const response = await api.get<ProductoServicioSchema>('/productos-servicios/schema');
    return response.data;
  },

  getProductoServicios: async (params: {
    limit: number;
    offset: number;
  }): Promise<ProductoServicioPageOut> => {
    const response = await api.get<ProductoServicioPageOut>("/productos-servicios", {
      params,
    });
    return response.data;
  },

  buscarProductoServicios: async (q: string, empresaId?: string, limit: number = 20): Promise<ProductoServicioOut[]> => {
    const params: { q: string; empresa_id?: string; limit: number } = { q, limit };
    if (empresaId) {
      params.empresa_id = empresaId;
    }
    const response = await api.get<ProductoServicioOut[]>('/productos-servicios/busqueda', { params });
    return response.data;
  },

  getProductoServicio: async (id: string): Promise<ProductoServicioOut> => {
    const response = await api.get<ProductoServicioOut>(`/productos-servicios/${id}`);
    return response.data;
  },

  createProductoServicio: async (data: ProductoServicioCreate): Promise<ProductoServicioOut> => {
    const response = await api.post<ProductoServicioOut>('/productos-servicios', data);
    return response.data;
  },

  updateProductoServicio: async (id: string, data: ProductoServicioUpdate): Promise<ProductoServicioOut> => {
    const response = await api.put<ProductoServicioOut>(`/productos-servicios/${id}`, data);
    return response.data;
  },

  deleteProductoServicio: async (id: string): Promise<void> => {
    await api.delete(`/productos-servicios/${id}`);
  },
};
