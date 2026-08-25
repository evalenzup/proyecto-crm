// src/services/conciliacionService.ts
import api from '@/lib/axios';

export interface ComplementoPago {
  id: string;
  folio: string;              // "P-857"
  fecha_pago?: string | null;
  imp_pagado: number;
}

export interface FacturaEnlazada {
  id: string;
  folio: string;              // "A-1585"
  total: number;
  fecha_emision?: string | null;
  cliente_nombre?: string | null;
  empresa_nombre?: string | null;
  estatus: string;
  metodo_pago?: string | null;          // PUE | PPD
  /** En una PPD el complemento es el documento que cuenta; una PUE no lo tiene. */
  complementos?: ComplementoPago[];
}

export interface EgresoEnlazado {
  id: string;
  proveedor?: string | null;
  descripcion?: string | null;
  monto: number;
  fecha_egreso?: string | null;
  categoria?: string | null;
  empresa_nombre?: string | null;
  /** Ruta del comprobante dentro de data/egresos, si lo tiene. */
  archivo_pdf?: string | null;
}

/** Candidata que propone el sistema. Trae su origen y su confianza porque no
 *  es lo mismo un folio escrito por el cliente que una coincidencia de monto. */
export interface Sugerencia {
  tipo: 'factura' | 'egreso';
  id: string;
  folio: string;
  total: number;
  fecha?: string | null;
  descripcion?: string | null;
  empresa?: string | null;
  origen: string;
  confianza: 'alta' | 'media' | 'baja';
  archivo_pdf?: string | null;
  metodo_pago?: string | null;
  complementos?: ComplementoPago[];
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
  egresos: EgresoEnlazado[];
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

  /** Candidatas por movimiento: { movimiento_id: [sugerencia, ...] } */
  sugerencias: async (id: string, empresa_id?: string): Promise<Record<string, Sugerencia[]>> => {
    const { data } = await api.get(`/conciliacion/${id}/sugerencias`, { params: { empresa_id } });
    return data;
  },

  enlazarEgresos: async (id: string, egreso_ids: string[]): Promise<MovimientoBancario> => {
    const { data } = await api.put(`/conciliacion/movimientos/${id}/egresos`, { egreso_ids });
    return data;
  },

  buscarEgresos: async (q: string, empresa_id?: string): Promise<EgresoEnlazado[]> => {
    const { data } = await api.get('/conciliacion/egresos/busqueda', { params: { q, empresa_id } });
    return data;
  },

  buscarFacturas: async (q: string, empresa_id?: string): Promise<FacturaEnlazada[]> => {
    const { data } = await api.get('/conciliacion/facturas/busqueda', {
      params: { q, empresa_id },
    });
    return data;
  },

  /** Deshace la conciliación: quita enlaces, comentario y área. */
  limpiarMovimiento: async (id: string): Promise<MovimientoBancario> => {
    const { data } = await api.delete(`/conciliacion/movimientos/${id}/enlaces`);
    return data;
  },

  areas: async (): Promise<Area[]> => {
    const { data } = await api.get('/conciliacion/areas');
    return data;
  },

  urlPdf: (id: string) => `/conciliacion/${id}/pdf`,

  /** Documento de respaldo de una candidata, para revisarla antes de aceptar.
   *  La factura arma su PDF con el id; el egreso se sirve por su ruta. */
  urlDocumento: (tipo: 'factura' | 'egreso' | 'pago', id: string, archivo?: string | null) => {
    if (tipo === 'factura') return `/facturas/${id}/pdf`;
    if (tipo === 'pago') return `/pagos/${id}/pdf`;
    return archivo ? `/egresos/archivo?ruta=${encodeURIComponent(archivo)}` : null;
  },

  urlExcel: (id: string) => `/conciliacion/${id}/export-excel`,
};

export default conciliacionService;
