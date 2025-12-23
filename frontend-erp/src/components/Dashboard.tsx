// src/components/Dashboard.tsx
import React, { useEffect, useMemo, useState } from 'react';
import { Row, Col, Card, Statistic, Table, Typography, Tooltip, Space, Select, Skeleton } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { dashboardService, IngresosEgresosOut, PresupuestosMetricsOut } from '@/services/dashboardService';
import { empresaService, EmpresaOut } from '@/services/empresaService';
import { useAuth } from '@/context/AuthContext';
import dynamic from 'next/dynamic';

const ReactECharts = dynamic(() => import('echarts-for-react'), {
  ssr: false,
  loading: () => <Skeleton active paragraph={{ rows: 8 }} style={{ height: 360, padding: 20 }} />,
});

const currency = (n: number, ccy: string) =>
  new Intl.NumberFormat('es-MX', { style: 'currency', currency: ccy || 'MXN', maximumFractionDigits: 2 }).format(
    Number.isFinite(n) ? n : 0
  );

export const Dashboard: React.FC = () => {
  const [data, setData] = useState<IngresosEgresosOut | null>(null);
  // const [presupuestosData, setPresupuestosData] = useState<PresupuestosMetricsOut | null>(null); // Disabled
  const [loadingFinance, setLoadingFinance] = useState(false);
  // const [loadingBudget, setLoadingBudget] = useState(false); // Disabled

  const [empresaId, setEmpresaId] = useState<string | undefined>(undefined);
  const [empresas, setEmpresas] = useState<EmpresaOut[]>([]);

  // Cargar lista de empresas
  useEffect(() => {
    empresaService.getEmpresas().then(data => {
      setEmpresas(data);
      if (data.length > 0 && !empresaId) {
        setEmpresaId(data[0].id);
      }
    });
  }, []);

  useEffect(() => {
    if (!empresaId) return;

    let mounted = true;

    // 2. Fetch Finance Metrics (Only)
    setLoadingFinance(true);
    dashboardService.getIngresosEgresos({ months: 12, empresaId })
      .then((res) => {
        if (mounted) setData(res);
      })
      .finally(() => {
        if (mounted) setLoadingFinance(false);
      });

    return () => {
      mounted = false;
    };
  }, [empresaId]);

  const ccy = data?.currency || 'MXN';

  const chartSeries = useMemo(() => {
    return (data?.series || []).map((s) => ({
      period: s.period,
      ingresos: s.ingresos || 0,
      egresos: s.egresos || 0,
      diff: (s.ingresos || 0) - (s.egresos || 0),
    }));
  }, [data]);

  const chartOption = useMemo(() => {
    const categories = chartSeries.map((s) => s.period);
    const ingresos = chartSeries.map((s) => s.ingresos);
    const egresos = chartSeries.map((s) => s.egresos);
    const porCobrar = (data?.series || []).map((s) => (s.por_cobrar ?? 0));
    const porPagar = (data?.series || []).map((s) => (s.por_pagar ?? 0));
    const diff = chartSeries.map((s) => s.diff);
    return {
      animation: true,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        valueFormatter: (v: any) => currency(Number(v), ccy),
      },
      legend: {
        data: ['Ingresos', 'Egresos', 'Por cobrar', 'Por pagar', 'Diferencia'],
      },
      grid: { left: 16, right: 16, top: 40, bottom: 40, containLabel: true },
      xAxis: {
        type: 'category',
        data: categories,
        axisLabel: { interval: 0, rotate: categories.length > 10 ? 45 : 0 },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (val: number) => currencyFormatter(val, ccy),
        },
        splitLine: { lineStyle: { color: '#f0f0f0' } },
      },
      series: [
        {
          name: 'Ingresos',
          type: 'bar',
          data: ingresos,
          itemStyle: { color: '#52c41a' },
          barGap: '10%',
          barCategoryGap: '30%'
        },
        {
          name: 'Egresos',
          type: 'bar',
          data: egresos,
          itemStyle: { color: '#f5222d' },
        },
        {
          name: 'Por cobrar',
          type: 'bar',
          data: porCobrar,
          itemStyle: { color: '#faad14' },
        },
        {
          name: 'Por pagar',
          type: 'bar',
          data: porPagar,
          itemStyle: { color: '#722ed1' },
        },
        {
          name: 'Diferencia',
          type: 'line',
          smooth: true,
          data: diff,
          itemStyle: { color: '#1677ff' },
          markLine: {
            symbol: 'none',
            label: { show: true, formatter: '0' },
            data: [{ yAxis: 0 }],
            lineStyle: { color: '#999', type: 'dashed' },
          },
        },
      ],
      dataZoom: [
        { type: 'inside' },
        { type: 'slider', height: 16, bottom: 6 },
      ],
    } as const;
  }, [chartSeries, ccy, data?.series]);

  // auth hook
  const { user } = useAuth();

  return (
    <Row gutter={[16, 16]}>
      {/* Filtro de Empresa (Solo Admin) */}
      {user?.rol === 'admin' && (
        <Col span={24} style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <Select
            placeholder="Filtrar por Empresa"
            style={{ width: 250 }}
            allowClear
            value={empresaId}
            onChange={setEmpresaId}
            options={empresas.map(e => ({ label: e.nombre_comercial, value: e.id }))}
          />
        </Col>
      )}

      {/* Sección de Ventas y Presupuestos - COMENTADA POR SOLICITUD
      <Col span={24}>
        <Typography.Title level={4}>Ventas y Presupuestos</Typography.Title>
      </Col>

      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Tasa de Conversión
                <Tooltip title="Porcentaje de presupuestos que han sido Aceptados o Facturados del total creado.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={presupuestosData?.conversion_rate ?? 0}
            suffix="%"
            precision={1}
            valueStyle={{ color: '#1890ff' }}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Pipeline (Por cerrar)
                <Tooltip title="Suma total de los presupuestos que están en estado Borrador o Enviado.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={presupuestosData?.pipeline_amount ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#faad14' }}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Ventas Perdidas
                <Tooltip title="Suma total de los presupuestos que fueron Rechazados o Caducaron.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={presupuestosData?.lost_sales_amount ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#ff4d4f' }}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Ticket Promedio
                <Tooltip title="Valor promedio de venta de los presupuestos Aceptados o Facturados.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={presupuestosData?.avg_ticket ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#52c41a' }}
          />
        </Card>
      </Col>
      */}

      <Col span={24}>
        <Typography.Title level={4} style={{ marginTop: 16 }}>Finanzas</Typography.Title>
      </Col>

      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Ingresos (MTD)
                <Tooltip title="Total de facturas cobradas en el mes actual.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={data?.mtd?.ingresos ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#3f8600' }}
            prefix={<ArrowUpOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Egresos (MTD)
                <Tooltip title="Total de gastos pagados en el mes actual.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={data?.mtd?.egresos ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#cf1322' }}
            prefix={<ArrowDownOutlined />}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Por cobrar (MTD)
                <Tooltip title="Monto pendiente de cobro de facturas emitidas en el mes actual.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={data?.mtd?.por_cobrar ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#faad14' }}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Por pagar (MTD)
                <Tooltip title="Monto pendiente de pago de gastos registrados en el mes actual.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={data?.mtd?.por_pagar ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
            valueStyle={{ color: '#722ed1' }}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Ingresos (YTD)
                <Tooltip title="Acumulado de ingresos en lo que va del año.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={data?.ytd?.ingresos ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Egresos (YTD)
                <Tooltip title="Acumulado de egresos en lo que va del año.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={data?.ytd?.egresos ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Por cobrar (YTD)
                <Tooltip title="Total acumulado pendiente de cobro del año.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={data?.ytd?.por_cobrar ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
          />
        </Card>
      </Col>
      <Col xs={24} md={12} lg={6}>
        <Card loading={loadingFinance}>
          <Statistic
            title={
              <Space>
                Por pagar (YTD)
                <Tooltip title="Total acumulado pendiente de pago del año.">
                  <InfoCircleOutlined style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }} />
                </Tooltip>
              </Space>
            }
            value={data?.ytd?.por_pagar ?? 0}
            formatter={(v) => currency(Number(v), ccy)}
          />
        </Card>
      </Col>

      <Col span={24}>
        <Card loading={loadingFinance}>
          <Typography.Title level={5} style={{ marginBottom: 16 }}>
            Tendencia últimos 12 meses (MXN)
          </Typography.Title>
          {chartSeries.length ? (
            <ReactECharts option={chartOption as any} style={{ width: '100%', height: 360 }} notMerge lazyUpdate />
          ) : (
            <Typography.Text type="secondary">Sin datos para graficar</Typography.Text>
          )}
        </Card>
      </Col>

      <Col span={24}>
        <Card loading={loadingFinance}>
          <Typography.Title level={5} style={{ marginBottom: 16 }}>
            Detalle mensual (MXN)
          </Typography.Title>
          <Table
            size="small"
            pagination={false}
            dataSource={(data?.series || []).map((r) => ({ key: r.period, ...r }))}
            columns={[
              { title: 'Periodo', dataIndex: 'period', key: 'period' },
              {
                title: 'Ingresos',
                dataIndex: 'ingresos',
                key: 'ingresos',
                align: 'right' as const,
                render: (v: number) => currency(v, ccy),
              },
              {
                title: 'Egresos',
                dataIndex: 'egresos',
                key: 'egresos',
                align: 'right' as const,
                render: (v: number) => currency(v, ccy),
              },
              {
                title: 'Por cobrar',
                dataIndex: 'por_cobrar',
                key: 'por_cobrar',
                align: 'right' as const,
                render: (v: number) => currency(v || 0, ccy),
              },
              {
                title: 'Por pagar',
                dataIndex: 'por_pagar',
                key: 'por_pagar',
                align: 'right' as const,
                render: (v: number) => currency(v || 0, ccy),
              },
              {
                title: 'Resultado',
                key: 'resultado',
                align: 'right' as const,
                render: (_: any, r: any) => currency((r.ingresos || 0) - (r.egresos || 0), ccy),
              },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
};

// helpers
const currencyFormatter = (n: number, ccy: string) =>
  new Intl.NumberFormat('es-MX', { style: 'currency', currency: ccy || 'MXN', maximumFractionDigits: 0 }).format(
    Number.isFinite(n) ? n : 0
  );

