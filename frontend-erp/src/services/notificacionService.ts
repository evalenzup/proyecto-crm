import api from '@/lib/axios';

export type TipoNotificacion = 'EXITO' | 'INFO' | 'ADVERTENCIA' | 'ERROR';

export interface NotificacionOut {
  id: string;
  empresa_id: string;
  usuario_id: string | null;
  tipo: TipoNotificacion;
  titulo: string;
  mensaje: string;
  leida: boolean;
  metadata?: Record<string, unknown>;
  creada_en: string;
}

export interface NotificacionListResponse {
  items: NotificacionOut[];
  total: number;
  no_leidas: number;
}

export const notificacionService = {
  getNotificaciones: async (params?: {
    solo_no_leidas?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<NotificacionListResponse> => {
    const response = await api.get<NotificacionListResponse>('/notificaciones/', { params });
    return response.data;
  },

  marcarLeida: async (id: string): Promise<NotificacionOut> => {
    const response = await api.patch<NotificacionOut>(`/notificaciones/${id}/leer`);
    return response.data;
  },

  marcarTodasLeidas: async (): Promise<{ message: string }> => {
    const response = await api.patch<{ message: string }>('/notificaciones/leer-todas');
    return response.data;
  },
};
