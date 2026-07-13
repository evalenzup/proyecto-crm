// src/services/certificadoService.ts
import api from '@/lib/axios';

export type TipoCertificado = 'PLAGUICIDAS' | 'SANITIZACION';

export interface CertificadoServicio {
  id: string;
  empresa_id: string;
  cliente_id?: string | null;
  tipo: TipoCertificado;
  folio: number;
  fecha: string;
  nombre_razon_social: string;
  domicilio?: string | null;
  telefono?: string | null;
  actividad?: string | null;
  areas?: Record<string, string> | null;
  plagas?: Record<string, string> | null;
  aplicaciones?: Record<string, string> | null;
  observaciones?: string | null;
  gerente_nombre?: string | null;
  creado_en: string;
}

export interface CertificadoPageOut {
  items: CertificadoServicio[];
  total: number;
  limit: number;
  offset: number;
}

export type CertificadoCreate = Omit<CertificadoServicio, 'id' | 'folio' | 'creado_en'> & {
  folio?: number | null;
};
export type CertificadoUpdate = Partial<Omit<CertificadoCreate, 'empresa_id' | 'tipo'>>;

export const certificadoService = {
  list: async (params: {
    empresa_id?: string;
    tipo?: string;
    q?: string;
    limit?: number;
    offset?: number;
    order_by?: string;
    order_dir?: 'asc' | 'desc';
  }): Promise<CertificadoPageOut> => {
    const { data } = await api.get<CertificadoPageOut>('/certificados', { params });
    return data;
  },

  siguienteFolio: async (empresaId: string, tipo: TipoCertificado = 'PLAGUICIDAS'): Promise<number> => {
    const { data } = await api.get<{ folio: number }>('/certificados/siguiente-folio', {
      params: { empresa_id: empresaId, tipo },
    });
    return data.folio;
  },

  create: async (payload: CertificadoCreate): Promise<CertificadoServicio> => {
    const { data } = await api.post<CertificadoServicio>('/certificados', payload);
    return data;
  },

  update: async (id: string, payload: CertificadoUpdate): Promise<CertificadoServicio> => {
    const { data } = await api.put<CertificadoServicio>(`/certificados/${id}`, payload);
    return data;
  },

  remove: async (id: string): Promise<void> => {
    await api.delete(`/certificados/${id}`);
  },

  pdf: async (id: string): Promise<Blob> => {
    const { data } = await api.get(`/certificados/${id}/pdf`, { responseType: 'blob' });
    return data;
  },
};

export default certificadoService;
