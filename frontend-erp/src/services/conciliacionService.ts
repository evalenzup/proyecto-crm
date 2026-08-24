// src/services/conciliacionService.ts
import api from '@/lib/axios';

export interface FacturaEnlazada {
  id: string;
  folio: string;              // "A-1585"
  total: number;
  fecha_emision?: string | null;
  cliente_nombre?: string | null;
  empresa_nombre?: string | null;
  estatus: string;
}

export interface MovimientoBancario {
  id: string;
  orden: number;
  fecha: string;
  concepto: string;
  deposito?: number | null;
  retiro?: number | null;
  comentario?: string | null;
  area?: string | null;
  conciliado: boolean;
  facturas: FacturaEnlazada[];
  /** Suma de las facturas enlazadas; se compara contra el importe. */
  suma_facturas: number;
}

export interface ConciliacionResumen {
  id: string;
  periodo_inicio: string;
  periodo_fin: string;
  banco: string;
  cuenta?: string | null;
  estado: string;
  saldo_inicial: number;
  saldo_final: number;
  total_depositos: number;
  total_retiros: number;
  n_depositos: number;
  n_retiros: number;
  total_movimientos: number;
  conciliados: number;
  tiene_archivo: boolean;
  creado_en: string;
}

export interface ConciliacionDetalle extends ConciliacionResumen {
  movimientos: MovimientoBancario[];
}

export interface Area {
  clave: string;
  nombre: string;
}

const conciliacionService = {
  listar: async (empresa_id?: string): Promise<ConciliacionResumen[]> => {
    const { data } = await api.get('/conciliacion', { params: { empresa_id } });
    return data;
  },

  obtener: async (id: string): Promise<ConciliacionDetalle> => {
    const { data } = await api.get(`/conciliacion/${id}`);
    return data;
  },

  /** Sube el estado de cuenta en PDF. El backend lo rechaza si no cuadra. */
  importar: async (archivo: File, empresa_id?: string): Promise<ConciliacionDetalle> => {
    const form = new FormData();
    form.append('archivo', archivo);
    const { data } = await api.post('/conciliacion', form, {
      params: { empresa_id },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  eliminar: async (id: string): Promise<void> => {
    await api.delete(`/conciliacion/${id}`);
  },

  actualizarMovimiento: async (
    id: string,
    cambios: { comentario?: string | null; area?: string | null; conciliado?: boolean },
  ): Promise<MovimientoBancario> => {
    const { data } = await api.put(`/conciliacion/movimientos/${id}`, cambios);
    return data;
  },

  /** Reemplaza las facturas del movimiento y rearma el comentario con los folios. */
  enlazarFacturas: async (id: string, factura_ids: string[]): Promise<MovimientoBancario> => {
    const { data } = await api.put(`/conciliacion/movimientos/${id}/facturas`, { factura_ids });
    return data;
  },

  buscarFacturas: async (q: string, empresa_id?: string): Promise<FacturaEnlazada[]> => {
    const { data } = await api.get('/conciliacion/facturas/busqueda', {
      params: { q, empresa_id },
    });
    return data;
  },

  areas: async (): Promise<Area[]> => {
    const { data } = await api.get('/conciliacion/areas');
    return data;
  },

  urlPdf: (id: string) => `/conciliacion/${id}/pdf`,
  urlExcel: (id: string) => `/conciliacion/${id}/export-excel`,
};

export default conciliacionService;
