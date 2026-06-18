// frontend-erp/src/services/empresaService.ts
import api from '../lib/axios';

interface EmpresaSchema {
  properties: Record<string, any>;
  required?: string[];
}

export interface EmpresaOut {
  id: string;
  nombre: string;
  nombre_comercial: string;
  rfc: string;
  ruc: string;
  direccion?: string;
  telefono?: string;
  email?: string;
  regimen_fiscal: string;
  codigo_postal: string;
  archivo_cer?: string;
  archivo_key?: string;
  logo?: string;
  color_empresa?: string;

  // Datos Bancarios
  nombre_banco?: string;
  numero_cuenta?: string;
  clabe?: string;
  beneficiario?: string;
  creado_en: string;
  actualizado_en: string;
  clientes?: Array<{ id: string; nombre_comercial: string }>;
  contrasena?: string; // Solo para el output, no se envía en create/update
  tiene_config_email?: boolean;
}

export interface CertInfoOut {
  nombre_cn?: string;
  rfc?: string;
  curp?: string;
  numero_serie?: string;
  valido_desde?: string;
  valido_hasta?: string;
  issuer_cn?: string;
  key_usage?: string[];
  extended_key_usage?: string[];
  tipo_cert?: string;
}

export interface EmpresaPageOut {
  items: EmpresaOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface RfcGroupEmpresa {
  id: string;
  nombre_comercial: string;
  nombre: string;
}

export interface RfcGroup {
  rfc: string;
  empresas: RfcGroupEmpresa[];
}

export const empresaService = {
  getEmpresaSchema: async (): Promise<EmpresaSchema> => {
    const response = await api.get<EmpresaSchema>('/empresas/form-schema');
    return response.data;
  },

  descargarLogo: (empresaId: string): string => {
    return `${api.defaults.baseURL}/empresas/logos/${empresaId}.png`;
  },

  descargarCertificado: (filename: string): string => {
    return `${api.defaults.baseURL}/empresas/certificados/${filename}`;
  },

  getCertInfo: async (id: string): Promise<CertInfoOut> => {
    const response = await api.get<CertInfoOut>(`/empresas/${id}/cert-info`);
    return response.data;
  },

  getEmpresas: async (): Promise<EmpresaOut[]> => {
    // Temporary fix: fetch a large number of items for dropdowns.
    // A searchable endpoint would be a better long-term solution.
    const response = await api.get<EmpresaPageOut>("/empresas", {
      params: { limit: 1000, offset: 0 },
    });
    return response.data.items;
  },

  getEmpresa: async (id: string): Promise<EmpresaOut> => {
    const response = await api.get<EmpresaOut>(`/empresas/${id}`);
    return response.data;
  },

  createEmpresa: async (data: FormData): Promise<EmpresaOut> => {
    // FormData se envía directamente, axios se encarga de los headers
    const response = await api.post<EmpresaOut>('/empresas', data);
    return response.data;
  },

  updateEmpresa: async (id: string, data: FormData): Promise<EmpresaOut> => {
    const response = await api.put<EmpresaOut>(`/empresas/${id}`, data);
    return response.data;
  },

  deleteEmpresa: async (id: string): Promise<void> => {
    await api.delete(`/empresas/${id}`);
  },

  // ── Plantilla de contrato por empresa ──────────────────────────────────────
  uploadPlantillaContrato: async (id: string, file: File): Promise<EmpresaOut> => {
    const fd = new FormData();
    fd.append('file', file);
    const response = await api.post<EmpresaOut>(`/empresas/${id}/plantilla-contrato`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  downloadPlantillaContrato: async (id: string): Promise<Blob> => {
    const response = await api.get(`/empresas/${id}/plantilla-contrato`, { responseType: 'blob' });
    return response.data;
  },

  deletePlantillaContrato: async (id: string): Promise<void> => {
    await api.delete(`/empresas/${id}/plantilla-contrato`);
  },

  getRfcGroups: async (): Promise<RfcGroup[]> => {
    const response = await api.get<RfcGroup[]>('/empresas/rfc-groups');
    return response.data;
  },

  /** Returns the empresa logo as an authenticated Blob */
  getLogoBlob: async (id: string): Promise<Blob> => {
    const response = await api.get(`/empresas/logos/${id}.png`, { responseType: 'blob' });
    return response.data;
  },

  /** Returns a certificate file as a Blob (used to verify presence on server) */
  getCertificadoBlob: async (filename: string): Promise<Blob> => {
    const response = await api.get(`/empresas/certificados/${filename}`, { responseType: 'blob' });
    return response.data;
  },

  /** Returns the email SMTP configuration for an empresa */
  getEmailConfig: async (id: string): Promise<any> => {
    const response = await api.get(`/empresas/${id}/email-config`);
    return response.data;
  },

  /** Parses a Constancia de Situación Fiscal PDF and returns extracted fields */
  parseCSF: async (file: File): Promise<{ rfc?: string; razon_social?: string; codigo_postal?: string; direccion?: string; regimen_fiscal?: string }> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/utils/parse-csf', formData);
    return response.data;
  },
};
