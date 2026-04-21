import api from '@/lib/axios';

export interface FinancieroMes {
  periodo: string; // "YYYY-MM"
  facturado: number;
  cobrado: number;
  por_cobrar: number;
  egresos: number;
  utilidad: number;
  margen_pct: number;
}

export interface FinancieroKpis {
  total_facturado: number;
  cobrado: number;
  por_cobrar: number;
  egresos: number;
  utilidad: number;
  margen_pct: number;
}

export interface FinancieroOut {
  kpis: FinancieroKpis;
  meses: FinancieroMes[];
}

export interface EgresoCatItem {
  name: string;
  value: number;
  pct: number;
}

export interface VentasKpis {
  total_presupuestos: number;
  tasa_conversion_pct: number;
  pipeline_abierto: number;
  ticket_promedio: number;
}

export interface EmbudoItem {
  etapa: string;
  cantidad: number;
  monto: number;
}

export interface VentasMes {
  periodo: string;
  cerrados: number;
  monto_cerrado: number;
  enviados: number;
  monto_pipeline: number;
}

export interface VentasOut {
  kpis: VentasKpis;
  embudo: EmbudoItem[];
  meses: VentasMes[];
}

export interface ClientesKpis {
  total_activos: number;
  nuevos: number;
  en_riesgo: number;
}

export interface TopCliente {
  rfc: string;
  nombre_comercial: string;
  nombre_razon_social: string;
  monto: number;
  facturas: number;
  ticket_promedio: number;
  ultima_factura: string | null;
}

export interface ClientesMes {
  periodo: string;
  nuevos: number;
  recurrentes: number;
}

export interface ClientesOut {
  kpis: ClientesKpis;
  top_clientes: TopCliente[];
  meses: ClientesMes[];
}

export interface EmpresaFinancieroMes {
  periodo: string;
  cobrado: number;
  por_cobrar: number;
  facturado: number;
  egresos: number;
}

export interface EmpresaFinanciero {
  empresa_id: string;
  nombre_comercial: string;
  facturado: number;
  cobrado: number;
  por_cobrar: number;
  egresos: number;
  utilidad: number;
  margen_pct: number;
  meses: EmpresaFinancieroMes[];
}

interface BaseParams {
  fechaInicio: string; // "YYYY-MM"
  fechaFin: string;    // "YYYY-MM"
  empresaId?: string;
  rfc?: string;
}

export const reportesService = {
  async getFinanciero(p: BaseParams): Promise<FinancieroOut> {
    const { data } = await api.get('/reportes/financiero', {
      params: {
        fecha_inicio: p.fechaInicio,
        fecha_fin: p.fechaFin,
        empresa_id: p.rfc ? undefined : p.empresaId,
        rfc: p.rfc,
      },
    });
    return data;
  },

  async getEgresosCategorias(p: BaseParams): Promise<EgresoCatItem[]> {
    const { data } = await api.get('/reportes/egresos-categoria', {
      params: {
        fecha_inicio: p.fechaInicio,
        fecha_fin: p.fechaFin,
        empresa_id: p.rfc ? undefined : p.empresaId,
        rfc: p.rfc,
      },
    });
    return data;
  },

  async getVentas(p: BaseParams): Promise<VentasOut> {
    const { data } = await api.get('/reportes/ventas', {
      params: {
        fecha_inicio: p.fechaInicio,
        fecha_fin: p.fechaFin,
        empresa_id: p.rfc ? undefined : p.empresaId,
        rfc: p.rfc,
      },
    });
    return data;
  },

  async getClientes(p: BaseParams): Promise<ClientesOut> {
    const { data } = await api.get('/reportes/clientes', {
      params: {
        fecha_inicio: p.fechaInicio,
        fecha_fin: p.fechaFin,
        empresa_id: p.rfc ? undefined : p.empresaId,
        rfc: p.rfc,
      },
    });
    return data;
  },

  async getFinancieroPorEmpresa(p: BaseParams): Promise<EmpresaFinanciero[]> {
    const { data } = await api.get('/reportes/financiero-por-empresa', {
      params: {
        fecha_inicio: p.fechaInicio,
        fecha_fin: p.fechaFin,
        empresa_id: p.rfc ? undefined : p.empresaId,
        rfc: p.rfc,
      },
    });
    return data;
  },
};
