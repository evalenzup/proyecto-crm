import { apiClient } from '@/lib/apiClient';

// Tipos de datos basados en los schemas de Pydantic
export interface EmailConfig {
  smtp_server: string;
  smtp_port: number;
  smtp_user: string;
  from_address: string;
  from_name?: string;
  use_tls: boolean;
  id: number;
  empresa_id: string;
}

export interface EmailConfigCreate {
  smtp_server: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password: string;
  from_address: string;
  from_name?: string;
  use_tls: boolean;
}

export interface EmailConfigUpdate {
  smtp_server?: string;
  smtp_port?: number;
  smtp_user?: string;
  smtp_password?: string;
  from_address?: string;
  from_name?: string;
  use_tls?: boolean;
}

const getEmailConfig = async (empresaId: string): Promise<EmailConfig> => {
  const response = await apiClient.get<EmailConfig>(`/empresas/${empresaId}/email-config/`);
  return response.data;
};

const createEmailConfig = async (empresaId: string, data: EmailConfigCreate): Promise<EmailConfig> => {
  const response = await apiClient.post<EmailConfig>(`/empresas/${empresaId}/email-config/`, data);
  return response.data;
};

const updateEmailConfig = async (empresaId: string, data: EmailConfigUpdate): Promise<EmailConfig> => {
  const response = await apiClient.put<EmailConfig>(`/empresas/${empresaId}/email-config/`, data);
  return response.data;
};

const deleteEmailConfig = async (empresaId: string): Promise<void> => {
  await apiClient.delete(`/empresas/${empresaId}/email-config/`);
};

export const emailConfigService = {
  get: getEmailConfig,
  create: createEmailConfig,
  update: updateEmailConfig,
  delete: deleteEmailConfig,
};
