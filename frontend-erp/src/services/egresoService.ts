// src/services/egresoService.ts

import api from '@/lib/axios';

const getData = <T = any>(p: Promise<any>): Promise<T> => p.then((r) => r.data);

// ---------------------- Egresos ----------------------

export const getEgresoEnums = () =>
  getData<{ categorias: string[], estatus: string[] }>(api.get('/egresos/enums'));

export const getEgresos = (params: {
  skip: number;
  limit: number;
  empresa_id?: string | null;
  proveedor?: string | null;
  categoria?: string | null;
  estatus?: string | null;
  fecha_desde?: string | null;
  fecha_hasta?: string | null;
}) =>
  getData<EgresoPageOut>(api.get('/egresos/', { params }));

export const getEgresoById = (id: string) =>
  getData<Egreso>(api.get(`/egresos/${id}`));

export const createEgreso = (payload: any) =>
  getData<Egreso>(api.post('/egresos/', payload));

export const updateEgreso = (id: string, payload: any) =>
  getData<Egreso>(api.put(`/egresos/${id}`, payload));

export const deleteEgreso = (id: string) =>
  getData(api.delete(`/egresos/${id}`));

export interface Egreso {
  id: string;
  empresa_id: string;
  descripcion: string;
  monto: number;
  moneda: string;
  fecha_egreso: string; // date
  categoria: string;
  estatus: string;
  proveedor?: string;
  path_documento?: string;
  metodo_pago?: string;
}

export interface EgresoPageOut {
  items: Egreso[];
  total: number;
  limit: number;
  offset: number;
}


