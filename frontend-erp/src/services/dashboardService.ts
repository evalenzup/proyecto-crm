// frontend-erp/src/services/dashboardService.ts
import api from '../lib/axios';

export interface SerieMensual {
  period: string; // YYYY-MM
  ingresos: number;
  egresos: number;
  por_cobrar?: number;
  por_pagar?: number;
}

export interface IngresosEgresosOut {
  mtd: { ingresos: number; egresos: number; por_cobrar?: number; por_pagar?: number; total_facturado?: number };
  ytd: { ingresos: number; egresos: number; por_cobrar?: number; por_pagar?: number; total_facturado?: number };
  series: SerieMensual[];
  currency: string; // e.g., MXN
}

export interface PresupuestosMetricsOut {
  conversion_rate: number;
  pipeline_amount: number;
  lost_sales_amount: number;
  avg_ticket: number;
  currency: string;
}

export const dashboardService = {
  async getIngresosEgresos(params?: { empresaId?: string; rfc?: string; months?: number; year?: number; month?: number }): Promise<IngresosEgresosOut> {
    const response = await api.get<IngresosEgresosOut>('/dashboard/ingresos-egresos', {
      params: {
        empresa_id: params?.rfc ? undefined : params?.empresaId,
        rfc: params?.rfc,
        months: params?.months ?? 12,
        year: params?.year,
        month: params?.month,
      },
    });
    return response.data;
  },

  async getPresupuestosMetrics(params?: { empresaId?: string; rfc?: string }): Promise<PresupuestosMetricsOut> {
    const response = await api.get<PresupuestosMetricsOut>('/dashboard/presupuestos', {
      params: {
        empresa_id: params?.rfc ? undefined : params?.empresaId,
        rfc: params?.rfc,
      },
    });
    return response.data;
  },

  async getEgresosPorCategoria(params?: { empresaId?: string; rfc?: string; year?: number; month?: number }): Promise<EgresoCategoriaMetric[]> {
    const response = await api.get<EgresoCategoriaMetric[]>('/dashboard/egresos-categoria', {
      params: {
        empresa_id: params?.rfc ? undefined : params?.empresaId,
        rfc: params?.rfc,
        year: params?.year,
        month: params?.month,
      },
    });
    return response.data;
  },

  async getAlertas(params?: { empresaId?: string; rfc?: string }): Promise<AlertasMetrics> {
    const response = await api.get<AlertasMetrics>('/dashboard/alertas', {
      params: {
        empresa_id: params?.rfc ? undefined : params?.empresaId,
        rfc: params?.rfc,
      },
    });
    return response.data;
  },

  async getReportes(params?: { empresaId?: string; rfc?: string }): Promise<ReportesMetrics> {
    const response = await api.get<ReportesMetrics>('/dashboard/reportes', {
      params: {
        empresa_id: params?.rfc ? undefined : params?.empresaId,
        rfc: params?.rfc,
      },
    });
    return response.data;
  },
};

export interface EgresoCategoriaMetric {
  name: string;
  value: number;
}

export interface AlertasMetrics {
  borradores_sin_timbrar: number;
  proximas_a_vencer_7_dias: number;
  facturas_timbradas_hoy: number;
  tasa_cancelacion_mes: number;
}

export interface ReportesMetrics {
  ticket_promedio_mes: number;
  margen_bruto_pct: number;
  dias_promedio_cobro: number;
  clientes_sin_actividad: number;
  concentracion_cartera_pct: number;
  concentracion_cartera_cliente: string;
  concentracion_cartera_cliente_comercial: string;
  ingresos_mtd: number;
  egresos_mtd: number;
}


