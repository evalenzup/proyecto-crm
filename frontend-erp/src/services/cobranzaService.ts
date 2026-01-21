import api from '@/lib/axios';
import { AgingReportResponse, CobranzaNota, CobranzaNotaCreate } from '@/types/cobranza';

export const getAgingReport = async (empresaId?: string): Promise<AgingReportResponse> => {
    const params = empresaId ? { empresa_id: empresaId } : {};
    const response = await api.get<AgingReportResponse>('/cobranza/aging', { params });
    return response.data;
};

export const createNota = async (payload: CobranzaNotaCreate, empresaId?: string): Promise<CobranzaNota> => {
    const params = empresaId ? { empresa_id: empresaId } : {};
    const response = await api.post<CobranzaNota>('/cobranza/notas', payload, { params });
    return response.data;
};

export const getNotasByCliente = async (clienteId: string, empresaId?: string): Promise<CobranzaNota[]> => {
    const params = empresaId ? { empresa_id: empresaId } : {};
    const response = await api.get<CobranzaNota[]>(`/cobranza/notas/${clienteId}`, { params });
    return response.data;
};

export const downloadEstadoCuenta = async (clienteId: string, empresaId?: string) => {
    const params = empresaId ? { empresa_id: empresaId } : {};
    const response = await api.get(`/cobranza/estado-cuenta/${clienteId}`, {
        params,
        responseType: 'blob'
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `estado_cuenta_${clienteId}.pdf`); // Backend can override this from header
    document.body.appendChild(link);
    link.click();
    link.remove();
};

export const fetchEstadoCuentaBlob = async (clienteId: string, empresaId?: string): Promise<Blob> => {
    const params = empresaId ? { empresa_id: empresaId } : {};
    const response = await api.get(`/cobranza/estado-cuenta/${clienteId}`, {
        params,
        responseType: 'blob'
    });
    return new Blob([response.data], { type: 'application/pdf' });
};

export const sendEstadoCuentaEmail = async (clienteId: string, recipients: string[], empresaId?: string) => {
    const params = empresaId ? { empresa_id: empresaId } : {};
    await api.post(`/cobranza/enviar-estado-cuenta`,
        { cliente_id: clienteId, recipients },
        { params }
    );
};

export const deleteNota = async (notaId: string): Promise<void> => {
    await api.delete(`/cobranza/notas/${notaId}`);
};
