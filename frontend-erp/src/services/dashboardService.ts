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
  mtd: { ingresos: number; egresos: number; por_cobrar?: number; por_pagar?: number };
  ytd: { ingresos: number; egresos: number; por_cobrar?: number; por_pagar?: number };
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
  async getIngresosEgresos(params?: { empresaId?: string; months?: number; year?: number; month?: number }): Promise<IngresosEgresosOut> {
    const response = await api.get<IngresosEgresosOut>('/dashboard/ingresos-egresos', {
      params: {
        empresa_id: params?.empresaId,
        months: params?.months ?? 12,
        year: params?.year,
        month: params?.month,
      },
    });
    return response.data;
  },

  async getPresupuestosMetrics(params?: { empresaId?: string }): Promise<PresupuestosMetricsOut> {
    const response = await api.get<PresupuestosMetricsOut>('/dashboard/presupuestos', {
      params: {
        empresa_id: params?.empresaId,
      },
    });
    return response.data;
  },

  async getEgresosPorCategoria(params?: { empresaId?: string; year?: number; month?: number }): Promise<EgresoCategoriaMetric[]> {
    const response = await api.get<EgresoCategoriaMetric[]>('/dashboard/egresos-categoria', {
      params: {
        empresa_id: params?.empresaId,
        year: params?.year,
        month: params?.month,
      },
    });
    return response.data;
  },
};

export interface EgresoCategoriaMetric {
  name: string; // Category name
  value: number; // Total amount
}
