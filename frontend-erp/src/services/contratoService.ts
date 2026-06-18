// frontend-erp/src/services/contratoService.ts
import api from '../lib/axios';

export interface Contrato {
  id: string;
  empresa_id: string;
  cliente_id: string;
  presupuesto_id?: string | null;
  numero_contrato?: string | null;
  fecha_contrato?: string | null;
  vigencia_desde?: string | null;
  vigencia_hasta?: string | null;
  certificado_folio?: string | null;
  datos?: Record<string, any> | null;
  personal_asignado?: string[] | null;
  exclusiones?: string | null;
  notas?: string | null;
  estado: string;
  archivo_docx?: string | null;
  archivo_pdf?: string | null;
  creado_en: string;
  actualizado_en: string;
}

export interface CampoPlantilla {
  name: string;
  label: string;
  tipo: 'numero' | 'texto';
}

export interface ContratoPrecarga {
  empresa_id: string | null;
  tiene_plantilla: boolean;
  campos: CampoPlantilla[];
  presupuesto_total: number | null;
  tecnicos_disponibles: { id: string; nombre: string; puesto?: string | null }[];
}

export const contratoService = {
  list: async (clienteId: string): Promise<Contrato[]> => {
    const { data } = await api.get<Contrato[]>('/contratos', { params: { cliente_id: clienteId } });
    return data;
  },

  precarga: async (clienteId: string, presupuestoId?: string): Promise<ContratoPrecarga> => {
    const params: Record<string, string> = { cliente_id: clienteId };
    if (presupuestoId) params.presupuesto_id = presupuestoId;
    const { data } = await api.get<ContratoPrecarga>('/contratos/precarga', { params });
    return data;
  },

  create: async (payload: Partial<Contrato>): Promise<Contrato> => {
    const { data } = await api.post<Contrato>('/contratos', payload);
    return data;
  },

  update: async (id: string, payload: Partial<Contrato>): Promise<Contrato> => {
    const { data } = await api.put<Contrato>(`/contratos/${id}`, payload);
    return data;
  },

  remove: async (id: string): Promise<void> => {
    await api.delete(`/contratos/${id}`);
  },

  generar: async (id: string): Promise<Contrato> => {
    const { data } = await api.post<Contrato>(`/contratos/${id}/generar`);
    return data;
  },

  descargar: async (id: string, fmt: 'pdf' | 'docx'): Promise<Blob> => {
    const { data } = await api.get(`/contratos/${id}/documento`, {
      params: { fmt },
      responseType: 'blob',
    });
    return data;
  },
};
