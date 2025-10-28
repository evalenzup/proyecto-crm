import api from '@/lib/axios';

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

export interface EmailConfigTest {
  smtp_server: string;
  smtp_port: number;
  smtp_user: string;
  smtp_password?: string;
  use_tls: boolean;
}

const getEmailConfig = async (empresaId: string): Promise<EmailConfig> => {
  const response = await api.get<EmailConfig>('/email-config/', { params: { empresa_id: empresaId } });
  return response.data;
};

const createEmailConfig = async (empresaId: string, data: EmailConfigCreate): Promise<EmailConfig> => {
  const response = await api.post<EmailConfig>('/email-config/', data, { params: { empresa_id: empresaId } });
  return response.data;
};

const updateEmailConfig = async (empresaId: string, data: EmailConfigUpdate): Promise<EmailConfig> => {
  const response = await api.put<EmailConfig>('/email-config/', data, { params: { empresa_id: empresaId } });
  return response.data;
};

const deleteEmailConfig = async (empresaId: string): Promise<void> => {
  await api.delete('/email-config/', { params: { empresa_id: empresaId } });
};

const testEmailConnection = async (empresaId: string, data: EmailConfigTest): Promise<{ message: string }> => {
  const response = await api.post<{ message: string }>('/email-config/test-connection', data, { params: { empresa_id: empresaId } });
  return response.data;
};

export const emailConfigService = {
  get: getEmailConfig,
  create: createEmailConfig,
  update: updateEmailConfig,
  delete: deleteEmailConfig,
  testConnection: testEmailConnection,
};
