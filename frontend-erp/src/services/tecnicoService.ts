// src/services/tecnicoService.ts
import api from '../lib/axios';
import { ServicioOperativoSimpleOut } from './servicioOperativoService';

export type TipoPersonal = 'TECNICO' | 'ADMINISTRATIVO' | 'OPERATIVO' | 'SUPERVISOR' | 'OTRO';
export type Sexo = 'HOMBRE' | 'MUJER' | 'OTRO';
export type TipoSangre = 'A+' | 'A-' | 'B+' | 'B-' | 'AB+' | 'AB-' | 'O+' | 'O-';
export type NivelEstudios = 'PRIMARIA' | 'SECUNDARIA' | 'PREPARATORIA' | 'TECNICO_MEDIO' | 'LICENCIATURA' | 'INGENIERIA' | 'POSGRADO' | 'OTRO';
export type LicenciaTipo = 'A' | 'B' | 'C' | 'D' | 'E';

export interface TecnicoOut {
  id: string;
  empresa_id: string;

  // Nombre
  nombre?: string | null;
  primer_apellido?: string | null;
  segundo_apellido?: string | null;
  nombre_completo: string;

  // Identificación
  curp?: string | null;
  rfc?: string | null;
  nss?: string | null;
  sexo?: Sexo | null;
  tipo_sangre?: TipoSangre | null;

  // Datos laborales
  numero_trabajador?: string | null;
  tipo_personal: TipoPersonal;
  area?: string | null;
  puesto?: string | null;
  nivel_estudios?: NivelEstudios | null;
  salario_base_cotizable?: number | null;

  // Contacto
  telefono?: string | null;
  celular?: string | null;
  email?: string | null;
  direccion?: string | null;

  // Licencia
  licencia_numero?: string | null;
  licencia_tipo?: LicenciaTipo | null;
  licencia_vencimiento?: string | null;

  // Foto
  foto?: string | null;

  // Operativo
  max_servicios_dia?: number | null;
  activo: boolean;
  notas?: string | null;

  creado_en: string;
  actualizado_en: string;
  especialidades: ServicioOperativoSimpleOut[];
}

export interface TecnicoCreate {
  empresa_id: string;

  nombre: string;
  primer_apellido: string;
  segundo_apellido?: string | null;

  curp?: string | null;
  rfc?: string | null;
  nss?: string | null;
  sexo?: Sexo | null;
  tipo_sangre?: TipoSangre | null;

  numero_trabajador?: string | null;
  tipo_personal?: TipoPersonal;
  area?: string | null;
  puesto?: string | null;
  nivel_estudios?: NivelEstudios | null;
  salario_base_cotizable?: number | null;

  telefono?: string | null;
  celular?: string | null;
  email?: string | null;
  direccion?: string | null;

  licencia_numero?: string | null;
  licencia_tipo?: LicenciaTipo | null;
  licencia_vencimiento?: string | null;

  max_servicios_dia?: number | null;
  activo?: boolean;
  notas?: string | null;
  especialidades_ids?: string[];
}

export type TecnicoUpdate = Partial<Omit<TecnicoCreate, 'empresa_id'>>;

export interface TecnicoPageOut {
  items: TecnicoOut[];
  total: number;
  limit: number;
  offset: number;
}

export const tecnicoService = {
  getTecnicos: async (params: {
    empresa_id?: string | null;
    q?: string;
    activo?: boolean;
    tipo_personal?: TipoPersonal;
    limit?: number;
    offset?: number;
    order_by?: string;
    order_dir?: 'asc' | 'desc';
  }): Promise<TecnicoPageOut> => {
    const response = await api.get<TecnicoPageOut>('/tecnicos', { params });
    return response.data;
  },

  getTecnico: async (id: string): Promise<TecnicoOut> => {
    const response = await api.get<TecnicoOut>(`/tecnicos/${id}`);
    return response.data;
  },

  createTecnico: async (data: TecnicoCreate): Promise<TecnicoOut> => {
    const response = await api.post<TecnicoOut>('/tecnicos', data);
    return response.data;
  },

  updateTecnico: async (id: string, data: TecnicoUpdate): Promise<TecnicoOut> => {
    const response = await api.put<TecnicoOut>(`/tecnicos/${id}`, data);
    return response.data;
  },

  deleteTecnico: async (id: string): Promise<void> => {
    await api.delete(`/tecnicos/${id}`);
  },

  subirFoto: async (id: string, file: File): Promise<TecnicoOut> => {
    const form = new FormData();
    form.append('file', file);
    const response = await api.post<TecnicoOut>(
      `/tecnicos/${id}/foto`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
  },

  eliminarFoto: async (id: string): Promise<void> => {
    await api.delete(`/tecnicos/${id}/foto`);
  },

  getFotoBlob: async (id: string): Promise<string> => {
    const response = await api.get(`/tecnicos/${id}/foto`, { responseType: 'blob' });
    return URL.createObjectURL(response.data);
  },

  descargarCredencial: async (id: string, nombreArchivo: string): Promise<void> => {
    const response = await api.get(`/tecnicos/${id}/credencial`, { responseType: 'blob' });
    const url = URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = nombreArchivo;
    a.click();
    URL.revokeObjectURL(url);
  },
};
